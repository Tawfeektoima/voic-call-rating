import os
import gc
import torch
import redis
import json
import psutil
from celery import Celery
from datetime import datetime, timezone
from app.database import SessionLocal
from app.models import Call, Campaign, CallStatus, SystemLog, CallOutcome, Employee, CallQAPair, GoldenPairCandidate, CandidateStatus
from app.services.transcription import transcriber
import logging

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
from app.services.analysis import evaluate_transcript, assign_speakers, CAMPAIGN_EXTRACTION_RULES
from app.services.acoustic import AcousticAnalyzer
from app.config import get_settings

settings = get_settings()
acoustic_analyzer = AcousticAnalyzer()
redis_client = redis.from_url(settings.CELERY_BROKER_URL)

def force_cuda_cleanup():
    """Explicitly collect garbage and clear PyTorch's CUDA cache."""
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()
    print("[*] CUDA memory cache cleared.")

def filter_hallucinated_segments(segments: list[dict]) -> list[dict]:
    """
    Filter segments based on Whisper confidence scores (Task-BE05).
    """
    cleaned = []
    for seg in segments:
        avg_logprob = seg.get("avg_logprob", 0)
        no_speech_prob = seg.get("no_speech_prob", 0)

        # 1. Hard Removal: no speech detected
        if no_speech_prob > 0.6:
            continue

        # 2. Flagging: low confidence
        if avg_logprob < -1.0:
            seg["needs_review"] = True
        else:
            seg["needs_review"] = False

        cleaned.append(seg)
    return cleaned

def format_transcript_for_llm(segments):
    """
    Prepares transcript for LLM with low-confidence markers (Task-BE05).
    """
    lines = []
    for seg in segments:
        prefix = "[NEEDS_REVIEW] " if seg.get("needs_review") else ""
        lines.append(
            f"{prefix}{seg['speaker']} ({seg['start']:.0f}s): {seg['text']}"
        )
    return "\n".join(lines)

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
    broker_connection_retry_on_startup=True, # Address Celery 6.0 deprecation
    task_ignore_result=True,         # Results are saved to DB, no need for Redis storage
)

def check_redis_health():
    """Checks if Redis is accessible and writable (Task 62-G)."""
    try:
        r = redis.from_url(settings.CELERY_BROKER_URL)
        r.ping()
        # Test write to ensure not in ReadOnly mode (MISCONF)
        r.set("health_check_probe", "ok", ex=10)
        return True, ""
    except redis.exceptions.ResponseError as e:
        if "MISCONF" in str(e):
            return False, "CRITICAL: Redis is in ReadOnly mode due to MISCONF. Fix: run 'redis-cli config set stop-writes-on-bgsave-error no'"
        return False, f"Redis Response Error: {str(e)}"
    except Exception as e:
        return False, f"Broker Connection Error: {str(e)}"

def print_worker_vram(stage: str):
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
    
    # Hard Cutoff for Legacy Calls (TASK-V07 Protection)
    if call_id <= 65:
        print(f"[*] Skipping legacy Call ID {call_id} (ID <= 65)")
        return
    
    # 0. Redis Health Check (Task 62-G)
    is_healthy, redis_error = check_redis_health()
    if not is_healthy:
        print(f"[!] {redis_error}")
        return

    # 0b. Disk Space Check (Task 67)
    # Check D: drive where project/database resides
    try:
        disk_usage = psutil.disk_usage('D:').percent
        if disk_usage > 95:
            print(f"[!] CRITICAL: Disk space on D: is {disk_usage}%. Worker aborted to prevent Redis MISCONF.")
            return
    except:
        pass

    db = SessionLocal()
    current_stage = "INITIALIZATION"
    import traceback
    try:
        current_stage = "DB_FETCH"
        call = db.query(Call).filter(Call.id == call_id).first()
        if not call:
            print(f"[!] Background Task: Call ID {call_id} not found.")
            return

        # Fetch Employee for dynamic speaker mapping (Task 62-F)
        employee = db.query(Employee).filter(Employee.id == call.employee_id).first()
        agent_name = employee.name if employee else None

        # 0. File Integrity Check (Task 62-E)
        if not os.path.exists(call.audio_file_path) or os.path.getsize(call.audio_file_path) == 0:
            print(f"[!] Call {call_id}: Corrupt upload or missing file.")
            call.status = CallStatus.FAILED
            call.error_message = "Corrupt Upload: Audio file is empty or missing."
            db.commit()
            redis_client.publish("call_updates", json.dumps({"call_id": call_id, "status": CallStatus.FAILED.value}))
            return

        # 1. Idempotency Check & Start Processing
        # FIX: Allow TRANSCRIBED calls to proceed to EVALUATION. Only skip if already EVALUATED or currently PROCESSING.
        if call.status == CallStatus.EVALUATED:
            print(f"[*] Call {call_id} is already EVALUATED. Skipping duplicate task.")
            return

        call.status = CallStatus.PROCESSING
        db.commit()
        redis_client.publish("call_updates", json.dumps({"call_id": call_id, "status": CallStatus.PROCESSING.value}))

        # 2. Transcribe & Diarize
        try:
            current_stage = "TRANSCRIPTION"
            raw_segments, duration = transcriber.process_audio(call.audio_file_path)
            raw_segments = filter_hallucinated_segments(raw_segments)
            call.audio_duration = duration
            force_cuda_cleanup() # After Transcription (Task 62-E)
            
            # 2b. Acoustic Emotion Analysis
            current_stage = "ACOUSTIC_ANALYSIS"
            print(f"[*] Starting acoustic emotion analysis for Call {call_id}...")
            force_cuda_cleanup() # Before Acoustic (Task 62-E)
            emotion_timeline = acoustic_analyzer.analyze_segments(call.audio_file_path, raw_segments)
            call.emotion_timeline = emotion_timeline
            force_cuda_cleanup() # After Acoustic (Task 62-E)
            
            # 2c. Semantic Speaker Assignment
            current_stage = "SPEAKER_ASSIGNMENT"
            print(f"[*] Assigning roles for Call {call_id} (Agent: {agent_name})...")
            speaker_map = assign_speakers(raw_segments, agent_name=agent_name)
            call.speaker_map = speaker_map
            
            # Correct speakers in emotion_timeline for UI coloring
            for point in emotion_timeline:
                original_spk = point.get("speaker", "UNKNOWN")
                point["speaker"] = speaker_map.get(original_spk, "Customer").lower()
            call.emotion_timeline = emotion_timeline
            
            # 2d. Transcript Schema Mapping (Action Item 2)
            structured_segments = []
            agent_time = 0.0
            customer_time = 0.0
            
            for i, seg in enumerate(raw_segments):
                # Safely extract emotion from timeline if available
                emotion = "neutral"
                if emotion_timeline and i < len(emotion_timeline):
                    emotion = emotion_timeline[i].get("emotion", "neutral")
                
                # Map speaker via speaker_map with "Customer" fallback
                # CRITICAL: This is the only place role is assigned
                role = speaker_map.get(seg.get("speaker"), "Customer")
                
                # Build structured segment according to target schema
                segment_obj = {
                    "id": str(i),
                    "start": float(seg.get("start", 0.0)),
                    "end": float(seg.get("end", 0.0)),
                    "speaker": role,
                    "text": str(seg.get("text", "")).strip(),
                    "emotion": emotion,
                    "needs_review": seg.get("needs_review", False)
                }
                structured_segments.append(segment_obj)
                
                # Calculate talk durations
                seg_dur = max(0, segment_obj["end"] - segment_obj["start"])
                if role == "Agent":
                    agent_time += seg_dur
                else:
                    customer_time += seg_dur
            
            call.transcript = structured_segments
            call.needs_review = any(s.get("needs_review") for s in structured_segments)
            call.agent_talk_time = round(agent_time, 2)
            call.customer_talk_time = round(customer_time, 2)
            
            # --- 2e. Advanced Feature Engineering (Task 65) ---
            current_stage = "FEATURE_ENGINEERING"
            print(f"[*] Extracting advanced features for Call {call_id}...")
            
            # Temporal Features
            call.call_datetime = call.created_at
            if call.call_datetime:
                call.call_hour = call.call_datetime.hour
                call.call_day_of_week = call.call_datetime.strftime('%A')
            
            # Tenure (Task-C03: Handle naive/aware mixing)
            if employee and employee.created_at:
                now_utc = datetime.now(timezone.utc)
                created = employee.created_at
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                delta_tenure = now_utc - created
                employee.agent_tenure_days = delta_tenure.days
            
            # Calls Before This (Today) (Task-C03: Handle naive/aware mixing)
            if call.call_datetime:
                start_of_day = datetime.combine(call.call_datetime.date(), datetime.min.time())
                # Ensure start_of_day matches the timezone-awareness of call_datetime
                if call.call_datetime.tzinfo is not None:
                    start_of_day = start_of_day.replace(tzinfo=timezone.utc)
                
                calls_today_count = db.query(Call).filter(
                    Call.employee_id == call.employee_id,
                    Call.created_at >= start_of_day,
                    Call.created_at < call.created_at
                ).count()
                call.calls_before_this = calls_today_count
            
            # NLP Metrics (Fillers, Interruptions, Response Time)
            fillers = ["okay", "yeah", "uh", "um", "ok", "right"]
            filler_count = 0
            interruptions = 0
            response_times = []
            
            for i in range(len(structured_segments)):
                seg = structured_segments[i]
                # Fillers (Agent only)
                if seg["speaker"] == "Agent":
                    text_lower = seg["text"].lower()
                    for f in fillers:
                        filler_count += text_lower.count(f)
                
                # Response Time & Interruptions
                if i > 0:
                    prev_seg = structured_segments[i-1]
                    gap = seg["start"] - prev_seg["end"]
                    
                    if seg["speaker"] != prev_seg["speaker"]:
                        if gap > 0:
                            response_times.append(gap)
                        elif gap < -0.2: # Overlap detection
                            interruptions += 1
            
            call.filler_words_count = filler_count
            call.interruptions_count = interruptions
            if response_times:
                call.avg_response_time_sec = round(sum(response_times) / len(response_times), 2)

            # --- Acoustic Delta (Task 67) ---
            if emotion_timeline:
                from collections import Counter
                first_30s = [p.get("emotion", "neutral") for p in emotion_timeline if p.get("start", 0) <= 30]
                last_30s = [p.get("emotion", "neutral") for p in emotion_timeline if p.get("end", 0) >= (call.audio_duration - 30)]
                
                emo_start = Counter(first_30s).most_common(1)[0][0] if first_30s else "neutral"
                emo_end = Counter(last_30s).most_common(1)[0][0] if last_30s else "neutral"
                
                negative = ["stress", "agitation", "angry", "sad"]
                positive = ["calm", "happy", "neutral"]
                if emo_start.lower() in negative and emo_end.lower() in positive:
                    call.de_escalation_success = True
                else:
                    call.de_escalation_success = False

            call.status = CallStatus.TRANSCRIBED
            db.commit()
            redis_client.publish("call_updates", json.dumps({"call_id": call_id, "status": CallStatus.TRANSCRIBED.value}))
            print(f"[*] Transcription and Emotion synchronization complete for Call {call_id}")
            
            # --- VRAM Offloading (Task 66) ---
            force_cuda_cleanup()
            
            print_worker_vram(f"POST-TRANSCRIPTION & EMOTION - Call ID {call_id}")
        except Exception as e:
            logger.error(f"[!] Transcription Error for Call {call_id}: {str(e)}", exc_info=True)
            call.status = CallStatus.FAILED
            call.error_message = f"Transcription Error: {str(e)}"
            
            error_type = "CUDA_OOM" if "CUDA out of memory" in str(e) else "TRANSCRIPTION_ERROR"
            sys_log = SystemLog(call_id=call_id, error_type=error_type, error_message=str(e))
            db.add(sys_log)
            
            db.commit()
            redis_client.publish("call_updates", json.dumps({"call_id": call_id, "status": CallStatus.FAILED.value}))
            return

        # 3. Evaluate with Groq
        try:
            current_stage = "LLM_EVALUATION"
            # Fetch Campaign for prompt
            campaign = db.query(Campaign).filter(Campaign.id == call.campaign_id).first()
            if not campaign:
                raise ValueError("Campaign not found for evaluation.")

            campaign_type_value = campaign.type.value if hasattr(campaign.type, 'value') else str(campaign.type)

            SYSTEM_ANNOUNCEMENT_PATTERNS = [
                "this call is being recorded",
                "this call may be recorded",
                "this call is recorded",
                "your call may be monitored",
                "calls may be recorded",
                "this call is monitored",
                "please hold",
                "thank you for calling",
            ]

            def is_system_announcement(seg) -> bool:
                text_lower = seg["text"].strip().lower()
                if seg["start"] >= 5.0:
                    return False
                return any(pattern in text_lower for pattern in SYSTEM_ANNOUNCEMENT_PATTERNS)

            filtered_transcript = [s for s in call.transcript if not is_system_announcement(s)]

            llm_transcript = format_transcript_for_llm(filtered_transcript)

            TRANSFER_PHRASES = [
                "put you through",
                "transfer you",
                "connect you",
                "put her through",
                "put him through",
                "transferring you",
                "let me connect",
                "i'll connect",
                "i will connect",
            ]

            transfer_detected = any(
                any(phrase in seg["text"].lower() for phrase in TRANSFER_PHRASES)
                for seg in call.transcript
                if seg["speaker"] == "Agent"
            )

            transfer_point_sec = None
            if transfer_detected:
                for seg in call.transcript:
                    if seg["speaker"] == "Agent" and any(
                        phrase in seg["text"].lower() for phrase in TRANSFER_PHRASES
                    ):
                        transfer_point_sec = seg["end"]
                        break

            # Pass campaign_type for dynamic prompt injection (Task 59)
            eval_result = evaluate_transcript(
                transcript=llm_transcript,
                campaign_prompt=campaign.evaluation_prompt,
                campaign_type=campaign_type_value,
                agent_name=agent_name,
                transfer_detected=transfer_detected,
                transfer_point_sec=transfer_point_sec,
            )
            
            call.reasoning = eval_result.reasoning
            call.call_summary = eval_result.summary
            call.evaluation_score = eval_result.score
            call.strengths = [s.model_dump() if hasattr(s, "model_dump") else s for s in eval_result.strengths]
            call.weaknesses = [w.model_dump() for w in eval_result.weaknesses]
            
            # Compliance Flags (Task 66)
            call.opening_ok = eval_result.opening_ok
            call.closing_ok = eval_result.closing_ok
            call.dob_verified = eval_result.dob_verified

            # Sales Data & Violations (Task 5)
            if campaign_type_value == "sales" and eval_result.raw_sales_data:
                call.sales_eval_data = eval_result.raw_sales_data

                # Auto-flag HR violations
                violations = eval_result.raw_sales_data.get("violations", [])
                if violations:
                    flagged_violations = []
                    if isinstance(violations, dict):
                        flagged_violations = [
                            k for k, v in violations.items()
                            if isinstance(v, dict) and v.get("flagged")
                        ]
                    elif isinstance(violations, list):
                        flagged_violations = [
                            v.get("violation_id", str(v))
                            for v in violations
                            if isinstance(v, dict)
                        ]
                    if flagged_violations:
                        print(f"⚠️ HR ALERT — Call {call_id} | Agent {call.employee_id} "
                              f"| Violations: {flagged_violations}")

                # Auto-set lead status from offer funnel
                offers = eval_result.raw_sales_data.get("offers_presented", [])
                call.lead_status = (
                    "hot" if len(offers) >= 3 else
                    "warm" if len(offers) >= 1 else
                    "cold"
                )

            call.status = CallStatus.EVALUATED
            call.processed_at = datetime.now(timezone.utc)

            # --- Save RAG QA Pairs (Task 65) ---
            if eval_result.qa_pairs:
                for pair in eval_result.qa_pairs:
                    qa_pair = CallQAPair(
                        call_id=call.id,
                        objection=pair.objection,
                        response=pair.response,
                        customer_emotion_at=pair.customer_emotion_at,
                        customer_emotion_after=pair.customer_emotion_after,
                        is_golden_response=pair.is_golden
                    )
                    db.add(qa_pair)

            # --- Programmatic KPI Calculation (Task 59) ---
            agent_time = call.agent_talk_time or 0.0
            customer_time = call.customer_talk_time or 0.0
            total_time = agent_time + customer_time
            talk_ratio = round(agent_time / total_time, 4) if total_time > 0 else 0.0

            # --- Backend "Sanity Check" for AI JSON Parsing (Task 61) ---
            specific_data = eval_result.campaign_specific_data or {}
            
            expected_rules = CAMPAIGN_EXTRACTION_RULES.get(campaign_type_value, {})
            if expected_rules:
                for field_name, field_desc in expected_rules.get("fields", {}).items():
                    if field_name not in specific_data or specific_data[field_name] is None:
                        default_val = 0 if "integer" in field_desc or "float" in field_desc else (False if "boolean" in field_desc else "")
                        specific_data[field_name] = default_val

            if campaign_type_value == "sales" and specific_data.get("sale_closed") is True:
                if not eval_result.outcome_value or eval_result.outcome_value <= 0:
                    print(f"[WARNING] Call {call_id}: AI marked sale_closed=True but outcome_value is 0.")
                    db.add(SystemLog(call_id=call_id, error_type="DATA_WARNING", error_message="Sale closed but outcome_value is 0"))

            eval_result.campaign_specific_data = specific_data

            # --- Persist CallOutcome (Task 59) ---
            outcome = CallOutcome(
                call_id=call.id,
                campaign_type=campaign_type_value,
                primary_outcome=eval_result.primary_outcome,
                outcome_value=eval_result.outcome_value,
                follow_up_required=eval_result.follow_up_required,
                follow_up_date=None,  # Parsed separately if needed
                agent_talk_time=agent_time,
                customer_talk_time=customer_time,
                talk_ratio=talk_ratio,
                campaign_specific_data=eval_result.campaign_specific_data,
            )
            db.add(outcome)

            # --- Phase 7: Self-Improvement Loop (HITL) ---
            # Nominate candidates for human review if they are high quality
            if call.evaluation_score >= 85:
                if eval_result.qa_pairs:
                    for pair in eval_result.qa_pairs:
                        # Improvement: Only nominate substantial responses (Word count > 15)
                        word_count = len(pair.response.split())
                        if pair.is_golden and word_count > 15:
                            candidate = GoldenPairCandidate(
                                call_id=call.id,
                                campaign_id=call.campaign_id,
                                question=pair.objection,
                                answer=pair.response,
                                score=call.evaluation_score
                            )
                            db.add(candidate)
                            print(f"[HITL] Nominated Golden Pair candidate from Call {call_id}")

            db.commit()
            redis_client.publish("call_updates", json.dumps({"call_id": call_id, "status": CallStatus.EVALUATED.value}))
            # Action Item 1: Radar Chart Data Synchronization
            from app.services.aggregation import update_agent_mastery_stats
            update_agent_mastery_stats(db, call.employee_id)
            print(f"[*] Evaluation complete for Call {call_id}. Score: {eval_result.score}")
            print(f"[*] CallOutcome saved: {outcome.primary_outcome} | Talk Ratio: {talk_ratio}")
            
            
        except Exception as e:
            logger.error(f"[!] Evaluation Error for Call {call_id}: {str(e)}", exc_info=True)
            call.status = CallStatus.FAILED
            call.error_message = f"Evaluation Error: {str(e)}"
            
            sys_log = SystemLog(call_id=call_id, error_type="EVALUATION_ERROR", error_message=str(e))
            db.add(sys_log)
            
            db.commit()
            redis_client.publish("call_updates", json.dumps({"call_id": call_id, "status": CallStatus.FAILED.value}))
            return

    except Exception as e:
        full_error = traceback.format_exc()
        print(f"[!] Unhandled background task error at stage {current_stage}: {full_error}")
        try:
            if call:
                call.status = CallStatus.FAILED
                call.error_message = f"Critical Error in {current_stage}: {str(e)}"
                db.add(SystemLog(call_id=call_id, error_type="CRITICAL_FAILURE", error_message=f"Stage: {current_stage} | Error: {str(e)}"))
                db.commit()
                redis_client.publish("call_updates", json.dumps({"call_id": call_id, "status": CallStatus.FAILED.value}))
        except:
            pass
    finally:
        print_worker_vram(f"END-TASK - Call ID {call_id}")
        db.close()
        # Explicitly clear VRAM and collect garbage before process exit
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()


@celery_app.task(name="evaluate_live_call")
def evaluate_live_call_task(call_id: int):
    """
    Evaluates a live call that already has its transcript assembled.
    Skips transcription and acoustic analysis to minimize latency.
    """
    db = SessionLocal()
    try:
        call = db.query(Call).filter(Call.id == call_id).first()
        if not call:
            print(f"[!] Live Eval: Call {call_id} not found.")
            return

        # 1. Start Processing
        call.status = CallStatus.PROCESSING
        db.commit()
        redis_client.publish("call_updates", json.dumps({"call_id": call_id, "status": CallStatus.PROCESSING.value}))

        # 2. Fetch Context
        campaign = db.query(Campaign).filter(Campaign.id == call.campaign_id).first()
        employee = db.query(Employee).filter(Employee.id == call.employee_id).first()
        agent_name = employee.name if employee else "Agent"
        campaign_type = campaign.type.value if hasattr(campaign.type, 'value') else str(campaign.type)

        # 3. Assemble LLM Transcript from structured JSON
        # Live calls come with a pre-assembled structured transcript list
        llm_transcript = "\n".join([
            f"[{s['start']:05.2f} - {s['end']:05.2f}] {s['speaker']}: {s['text']}"
            for s in call.transcript
        ])

        # 4. Evaluate (Reuse existing logic exactly)
        eval_result = evaluate_transcript(
            transcript=llm_transcript,
            campaign_prompt=campaign.evaluation_prompt,
            campaign_type=campaign_type,
            agent_name=agent_name,
            transfer_detected=False,
            transfer_point_sec=None,
        )

        # 5. Save results
        call.reasoning = eval_result.reasoning
        call.call_summary = eval_result.summary
        call.evaluation_score = eval_result.score
        call.strengths = [s.model_dump() if hasattr(s, "model_dump") else s for s in eval_result.strengths]
        call.weaknesses = [w.model_dump() for w in eval_result.weaknesses]
        call.opening_ok = eval_result.opening_ok
        call.closing_ok = eval_result.closing_ok
        call.dob_verified = eval_result.dob_verified

        # Save Outcomes
        outcome = CallOutcome(
            call_id=call.id,
            campaign_type=campaign_type,
            primary_outcome=eval_result.primary_outcome,
            outcome_value=eval_result.outcome_value,
            follow_up_required=eval_result.follow_up_required,
            agent_talk_time=call.agent_talk_time or 0.0,
            customer_talk_time=call.customer_talk_time or 0.0,
            talk_ratio=0.5, # Placeholder
            campaign_specific_data=eval_result.campaign_specific_data,
        )
        db.add(outcome)

        # --- Phase 7: Self-Improvement Loop (HITL) ---
        if call.evaluation_score >= 85:
            if eval_result.qa_pairs:
                for pair in eval_result.qa_pairs:
                    word_count = len(pair.response.split())
                    if pair.is_golden and word_count > 15:
                        candidate = GoldenPairCandidate(
                            call_id=call.id,
                            campaign_id=call.campaign_id,
                            question=pair.objection,
                            answer=pair.response,
                            score=call.evaluation_score
                        )
                        db.add(candidate)
                        print(f"[HITL] Nominated Golden Pair candidate from Live Call {call_id}")

        call.status = CallStatus.EVALUATED
        call.processed_at = datetime.now(timezone.utc)
        db.commit()
        redis_client.publish("call_updates", json.dumps({"call_id": call_id, "status": CallStatus.EVALUATED.value}))
        
        # Trigger stats aggregation
        from app.services.aggregation import update_agent_mastery_stats
        update_agent_mastery_stats(db, call.employee_id)
        
        print(f"[*] Live Evaluation complete for Call {call_id}.")

    except Exception as e:
        logger.error(f"[!] Live Evaluation Error for Call {call_id}: {str(e)}", exc_info=True)
        if call:
            call.status = CallStatus.FAILED
            call.error_message = f"Live Eval Error: {str(e)}"
            db.commit()
    finally:
        db.close()
