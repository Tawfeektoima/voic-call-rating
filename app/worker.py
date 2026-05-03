import os
import gc
import torch
from celery import Celery
from datetime import datetime, timezone
from app.database import SessionLocal
from app.models import Call, Campaign, CallStatus, SystemLog
from app.services.transcription import transcriber
from app.services.analysis import evaluate_transcript, assign_speakers
from app.services.acoustic import AcousticAnalyzer
from app.config import get_settings

settings = get_settings()
acoustic_analyzer = AcousticAnalyzer()

# Initialize Celery
celery_app = Celery("call_rating_worker", broker=settings.CELERY_BROKER_URL)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_max_tasks_per_child=1, # CRITICAL: Force worker restart after every task to clear VRAM
    # --- RACE CONDITION PREVENTIONS ---
    broker_transport_options={
        "visibility_timeout": 3600,  # 1 hour (Prevent Redis from re-delivering long tasks)
    },
    task_acks_late=False,            # Acknowledge immediately to remove from queue
    worker_prefetch_multiplier=1,    # Only take one task at a time
)

def print_worker_vram(stage: str):
    import torch
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / (1024**3)
        reserved = torch.cuda.memory_reserved() / (1024**3)
        free_mem, total_mem = torch.cuda.mem_get_info()
        print(f"\n⚙️ [Worker VRAM | {stage}]")
        print(f"   ├─ PyTorch Allocated: {allocated:.2f} GB")
        print(f"   ├─ PyTorch Reserved : {reserved:.2f} GB")
        print(f"   └─ System Free VRAM : {free_mem/(1024**3):.2f} / {total_mem/(1024**3):.2f} GB\n")

@celery_app.task(bind=True, name="process_call_audio")
def process_call_audio_task(self, call_id: int):
    """
    Background task to process audio:
    1. Transcribe (WhisperX + Pyannote)
    2. Evaluate (Groq)
    """
    print_worker_vram(f"PRE-TASK - Call ID {call_id}")
    db = SessionLocal()
    try:
        call = db.query(Call).filter(Call.id == call_id).first()
        if not call:
            print(f"[!] Background Task: Call ID {call_id} not found.")
            return

        # 1. Idempotency Check & Start Processing
        if call.status in [CallStatus.PROCESSING, CallStatus.TRANSCRIBED, CallStatus.EVALUATED]:
            print(f"[*] Call {call_id} is already in state '{call.status.value}'. Skipping duplicate task.")
            return

        call.status = CallStatus.PROCESSING
        db.commit()

        # 2. Transcribe & Diarize
        try:
            raw_segments, duration = transcriber.process_audio(call.audio_file_path)
            call.audio_duration = duration
            
            # 2a. Memory Flush after Diarization (VRAM De-fragmentation)
            print("[*] Diarization complete. Flushing VRAM before Acoustic Analysis...")
            import gc
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            # 2b. Acoustic Emotion Analysis
            print(f"[*] Starting acoustic emotion analysis for Call {call_id}...")
            # analyze_segments takes the raw segments with timestamps
            emotion_timeline = acoustic_analyzer.analyze_segments(call.audio_file_path, raw_segments)
            call.emotion_timeline = emotion_timeline
            
            # 2c. Semantic Speaker Assignment
            print(f"[*] Assigning roles for Call {call_id}...")
            speaker_map = assign_speakers(raw_segments)
            call.speaker_map = speaker_map
            
            # Correct speakers in emotion_timeline for UI coloring
            for point in emotion_timeline:
                original_spk = point.get("speaker", "UNKNOWN")
                point["speaker"] = speaker_map.get(original_spk, "Customer").lower()
            call.emotion_timeline = emotion_timeline
            
            # 2d. Build Enriched Structured Transcript & Calculate Talk Times
            enriched_transcript = []
            agent_time = 0.0
            customer_time = 0.0
            
            for i, seg in enumerate(raw_segments):
                # Match emotion result to this segment
                emotion = "calm"
                if i < len(emotion_timeline):
                    emotion = emotion_timeline[i]["emotion"]
                
                original_speaker = seg.get("speaker", "UNKNOWN")
                role = speaker_map.get(original_speaker, "Customer")
                
                # Create structured segment
                segment_obj = {
                    "id": str(i),
                    "start": round(seg.get("start", 0.0), 2),
                    "end": round(seg.get("end", 0.0), 2),
                    "speaker": role.lower(), # Store as 'agent' or 'customer'
                    "text": seg.get("text", "").strip(),
                    "emotion": emotion
                }
                enriched_transcript.append(segment_obj)
                
                # Calculate talk durations
                seg_dur = segment_obj["end"] - segment_obj["start"]
                if role == "Agent":
                    agent_time += seg_dur
                else:
                    customer_time += seg_dur
            
            call.transcript = enriched_transcript
            call.agent_talk_time = round(agent_time, 2)
            call.customer_talk_time = round(customer_time, 2)
            
            call.status = CallStatus.TRANSCRIBED
            db.commit()
            print(f"[*] Transcription and Emotion synchronization complete for Call {call_id}")
            print_worker_vram(f"POST-TRANSCRIPTION & EMOTION - Call ID {call_id}")
        except Exception as e:
            call.status = CallStatus.FAILED
            call.error_message = f"Transcription Error: {str(e)}"
            
            error_type = "CUDA_OOM" if "CUDA out of memory" in str(e) else "TRANSCRIPTION_ERROR"
            sys_log = SystemLog(call_id=call_id, error_type=error_type, error_message=str(e))
            db.add(sys_log)
            
            db.commit()
            return

        # 3. Evaluate with Groq
        try:
            # Fetch Campaign for prompt
            campaign = db.query(Campaign).filter(Campaign.id == call.campaign_id).first()
            if not campaign:
                raise ValueError("Campaign not found for evaluation.")

            # Convert structured transcript back to string for LLM evaluation
            llm_transcript = "\n".join([
                f"[{s['start']:05.2f} - {s['end']:05.2f}] {s['speaker']}: {s['text']}"
                for s in call.transcript
            ])

            eval_result = evaluate_transcript(llm_transcript, campaign.evaluation_prompt)
            
            call.reasoning = eval_result.reasoning
            call.call_summary = eval_result.summary
            call.evaluation_score = eval_result.score
            call.strengths = eval_result.strengths
            call.weaknesses = [w.model_dump() for w in eval_result.weaknesses]
            call.status = CallStatus.EVALUATED
            call.processed_at = datetime.now(timezone.utc)
            db.commit()
            print(f"[*] Evaluation complete for Call {call_id}. Score: {eval_result.score}")
            
            # --- Cumulative Skill Aggregation (Task 56) ---
            try:
                from app.services.aggregation import update_agent_mastery_stats
                update_agent_mastery_stats(db, call.employee_id)
                print(f"[*] Cumulative skills updated for Agent {call.employee_id}")
            except Exception as agg_err:
                print(f"[!] Error updating cumulative stats: {agg_err}")
            
        except Exception as e:
            call.status = CallStatus.FAILED
            call.error_message = f"Evaluation Error: {str(e)}"
            
            sys_log = SystemLog(call_id=call_id, error_type="EVALUATION_ERROR", error_message=str(e))
            db.add(sys_log)
            
            db.commit()
            return

    except Exception as e:
        print(f"[!] Unhandled background task error: {e}")
        try:
            sys_log = SystemLog(call_id=call_id, error_type="UNHANDLED_ERROR", error_message=str(e))
            db.add(sys_log)
            db.commit()
        except:
            pass
    finally:
        print_worker_vram(f"END-TASK - Call ID {call_id}")
        db.close()
        # Explicitly clear VRAM and collect garbage before process exit
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
