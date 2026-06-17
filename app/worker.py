import os
import gc
import torch
import redis
import json
import psutil
import tempfile
from celery import Celery
from datetime import datetime, timezone
from app.database import SessionLocal
from app.models import (
    AgentViolation,
    Call,
    CallOutcome,
    CallQAPair,
    CallStatus,
    Campaign,
    CandidateStatus,
    Employee,
    GoldenPairCandidate,
    InterviewAnswer,
    InterviewAnswerStatus,
    InterviewCandidateStatus,
    InterviewSessionStatus,
    SystemLog,
)
from app.services.transcription import transcriber
import logging

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
from app.services.analysis import evaluate_transcript, assign_speakers, CAMPAIGN_EXTRACTION_RULES
from app.services.acoustic import AcousticAnalyzer
from app.config import get_settings
from app.services.interview_workflow import create_interview_workflow_event, sync_candidate_interview_state

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

def release_worker_model_resources():
    """
    Free any model state that may still be hanging around after a task.
    This matters on 4GB GPUs where even small leftovers destabilize the next job.
    """
    try:
        transcriber.release_resources()
    except Exception as e:
        print(f"[!] Transcriber cleanup warning: {e}")

    try:
        acoustic_analyzer.release_resources()
    except Exception as e:
        print(f"[!] Acoustic cleanup warning: {e}")

    force_cuda_cleanup()

def filter_hallucinated_segments(segments: list[dict]) -> list[dict]:
    """
    Fixed for WhisperX output — avg_logprob and no_speech_prob
    are NOT available after alignment+diarization.
    Uses word-level confidence instead when available.
    """
    cleaned = []

    for seg in segments:
        # Method 1: word-level confidence (available in WhisperX with word_timestamps=True)
        words = seg.get("words", [])
        if words:
            scores = [w.get("score", 1.0) for w in words if "score" in w]
            if scores:
                avg_score = sum(scores) / len(scores)
                if avg_score < 0.3:   # very low confidence across all words
                    seg["needs_review"] = True
                elif avg_score < 0.55:
                    seg["needs_review"] = True

        # Method 2: fallback to avg_logprob if still present (raw Whisper output)
        avg_logprob = seg.get("avg_logprob")
        no_speech_prob = seg.get("no_speech_prob")

        if no_speech_prob is not None and no_speech_prob > 0.6:
            continue  # Hard remove

        if avg_logprob is not None and avg_logprob < -1.0:
            seg["needs_review"] = True

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
    broker_channel_error_retry=True,  # Retry Redis channel errors like MISCONF instead of crashing
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

def check_disk_capacity():
    """
    AI model loading uses the Windows system drive for paging and the temp
    directory for native library work. If either is full, CUDA/native libraries
    can terminate the worker without raising a Python exception.
    """
    checks = []
    system_root = os.environ.get("SystemDrive", "C:") + "\\"
    temp_root = os.path.abspath(tempfile.gettempdir())
    project_root = os.path.abspath(os.getcwd())

    for label, path, minimum_free_gb in (
        ("system drive/pagefile", system_root, 5.0),
        ("temp drive", temp_root, 2.0),
        ("project drive", project_root, 2.0),
    ):
        try:
            usage = psutil.disk_usage(path)
            free_gb = usage.free / (1024**3)
            if free_gb < minimum_free_gb:
                checks.append(f"{label} at {path} has only {free_gb:.2f} GB free; need at least {minimum_free_gb:.1f} GB")
        except Exception as e:
            checks.append(f"could not check {label} at {path}: {e}")

    if checks:
        return False, "Disk capacity check failed: " + "; ".join(checks)
    return True, ""

def print_worker_vram(stage: str):
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / (1024**3)
        reserved = torch.cuda.memory_reserved() / (1024**3)
        free_mem, total_mem = torch.cuda.mem_get_info()
        print(f"\n⚙️ [Worker VRAM | {stage}]")
        print(f"   ├─ PyTorch Allocated: {allocated:.2f} GB")
        print(f"   ├─ PyTorch Reserved : {reserved:.2f} GB")
        print(f"   └─ System Free VRAM : {free_mem/(1024**3):.2f} / {total_mem/(1024**3):.2f} GB\n")

def _cleanup_partial_evaluation_records(db, call_id: int):
    """Remove partial child records from a failed or interrupted evaluation."""
    db.query(AgentViolation).filter(AgentViolation.call_id == call_id).delete(synchronize_session=False)
    db.query(CallQAPair).filter(CallQAPair.call_id == call_id).delete(synchronize_session=False)
    db.query(GoldenPairCandidate).filter(GoldenPairCandidate.call_id == call_id).delete(synchronize_session=False)


def _has_completed_evaluation(db, call_id: int) -> bool:
    return db.query(CallOutcome.id).filter(CallOutcome.call_id == call_id).first() is not None


def _build_interview_evaluation_prompt(answer: InterviewAnswer) -> str:
    question = answer.question
    candidate = answer.candidate
    job = answer.session.job if answer.session is not None else candidate.job
    expected_skills = question.expected_skills_tags or []
    skills_line = ", ".join(str(item) for item in expected_skills) if isinstance(expected_skills, list) else str(expected_skills or "")
    return (
        "You are evaluating a structured hiring interview answer.\n"
        f"Role Title: {job.title if job is not None else 'Unknown role'}\n"
        f"Department: {job.department if job is not None and job.department else 'Unspecified'}\n"
        f"Interview Question: {question.question_text}\n"
        f"Expected Skills: {skills_line or 'General communication, clarity, and relevance'}\n"
        "Score the candidate answer for relevance, clarity, communication quality, and practical fit for the role. "
        "Treat the candidate as the person being evaluated and do not invent a customer/agent dialogue."
    )


def _build_interview_transcript(answer: InterviewAnswer) -> str:
    response_text = (answer.transcribed_text or "").strip()
    return (
        f"Interviewer: {answer.question.question_text.strip()}\n"
        f"Candidate: {response_text}"
    )


@celery_app.task(bind=True, name="interview.process_answer")
def process_interview_answer_task(self, answer_id: int):
    print_worker_vram(f"PRE-TASK - Interview Answer ID {answer_id}")
    is_healthy, redis_error = check_redis_health()
    if not is_healthy:
        print(f"[!] Interview task proceeding despite Redis health warning: {redis_error}")

    db = SessionLocal()
    try:
        answer = db.query(InterviewAnswer).filter(InterviewAnswer.id == answer_id).first()
        if answer is None:
            print(f"[!] Interview answer {answer_id} not found.")
            return

        if answer.status == InterviewAnswerStatus.EVALUATED and answer.evaluated_at is not None:
            print(f"[*] Interview answer {answer_id} already evaluated. Skipping duplicate task.")
            return

        answer.status = InterviewAnswerStatus.PROCESSING
        answer.error_message = None
        db.flush()
        create_interview_workflow_event(
            db,
            candidate_id=answer.candidate_id,
            event_type="ANSWER_EVALUATION_STARTED",
            note="Interview answer evaluation started",
            event_payload={"answer_id": answer.id, "question_id": answer.question_id},
        )
        db.commit()

        if not answer.transcribed_text:
            if not answer.audio_file_path or not os.path.exists(answer.audio_file_path):
                raise ValueError("Interview answer audio file is missing.")
            raw_segments, _duration = transcriber.process_audio(answer.audio_file_path)
            raw_segments = filter_hallucinated_segments(raw_segments)
            transcript_text = " ".join(
                segment.get("text", "").strip()
                for segment in raw_segments
                if segment.get("text")
            ).strip()
            if not transcript_text:
                raise ValueError("Interview answer transcription returned no usable text.")
            answer.transcribed_text = transcript_text

        interview_prompt = _build_interview_evaluation_prompt(answer)
        eval_result = evaluate_transcript(
            transcript=_build_interview_transcript(answer),
            campaign_prompt=interview_prompt,
            campaign_type="customer_service",
            agent_name=answer.candidate.full_name,
        )

        strengths = ", ".join(
            item.issue if hasattr(item, "issue") else str(item.get("issue", ""))
            for item in eval_result.strengths[:3]
        ).strip(", ")
        weaknesses = ", ".join(
            item.issue if hasattr(item, "issue") else str(item.get("issue", ""))
            for item in eval_result.weaknesses[:3]
        ).strip(", ")
        answer.overall_score = float(eval_result.score)
        answer.ai_summary = eval_result.summary
        if strengths:
            answer.ai_summary += f" Strengths: {strengths}."
        if weaknesses:
            answer.ai_summary += f" Watchouts: {weaknesses}."
        answer.status = InterviewAnswerStatus.EVALUATED
        answer.evaluated_at = datetime.now(timezone.utc)
        before_status, after_status = sync_candidate_interview_state(db, answer.candidate)
        create_interview_workflow_event(
            db,
            candidate_id=answer.candidate_id,
            event_type="ANSWER_EVALUATED",
            from_status=before_status,
            to_status=after_status,
            note="Interview answer evaluated successfully",
            event_payload={"answer_id": answer.id, "question_id": answer.question_id, "overall_score": answer.overall_score},
        )
        if before_status != after_status and after_status == InterviewCandidateStatus.EVALUATED.value:
            create_interview_workflow_event(
                db,
                candidate_id=answer.candidate_id,
                event_type="CANDIDATE_EVALUATED",
                from_status=before_status,
                to_status=after_status,
                note="All interview answers reached terminal evaluation state",
                event_payload={"final_score": answer.candidate.final_score},
            )
        db.commit()
    except Exception as exc:
        db.rollback()
        answer = db.query(InterviewAnswer).filter(InterviewAnswer.id == answer_id).first()
        if answer is not None:
            answer.status = InterviewAnswerStatus.FAILED
            answer.error_message = str(exc)
            before_status, after_status = sync_candidate_interview_state(db, answer.candidate)
            create_interview_workflow_event(
                db,
                candidate_id=answer.candidate_id,
                event_type="ANSWER_EVALUATION_FAILED",
                from_status=before_status,
                to_status=after_status,
                note="Interview answer evaluation failed",
                event_payload={"answer_id": answer.id, "question_id": answer.question_id, "error": str(exc)},
            )
            db.commit()
        print(f"[!] Interview answer {answer_id} evaluation failed: {exc}")
    finally:
        db.close()
        release_worker_model_resources()
        print_worker_vram(f"END-TASK - Interview Answer ID {answer_id}")


@celery_app.task(bind=True, name="process_call_audio")
def process_call_audio_task(self, call_id: int):
    """
    Background task to process audio:
    1. Transcribe (WhisperX + Pyannote)
    2. Evaluate (Groq)
    """
    print_worker_vram(f"PRE-TASK - Call ID {call_id}")

    # 0. Redis Health Check (Task 62-G)
    is_healthy, redis_error = check_redis_health()
    if not is_healthy:
        print(f"[!] {redis_error}")
        return

    db = SessionLocal()
    current_stage = "INITIALIZATION"
    import traceback
    try:
        current_stage = "DB_FETCH"
        call = db.query(Call).filter(Call.id == call_id).first()
        if not call:
            print(f"[!] Background Task: Call ID {call_id} not found.")
            return

        # Disk/Pagefile preflight: fail the call cleanly before native model
        # loading can terminate the process and leave it stuck in PROCESSING.
        has_disk_capacity, disk_error = check_disk_capacity()
        if not has_disk_capacity:
            print(f"[!] Call {call_id}: {disk_error}")
            call.status = CallStatus.FAILED
            call.error_message = disk_error
            db.commit()
            redis_client.publish("call_updates", json.dumps({"call_id": call_id, "status": CallStatus.FAILED.value}))
            return

        # Fetch Employee for dynamic speaker mapping (Task 62-F)
        employee = db.query(Employee).filter(Employee.id == call.employee_id).first()
        agent_name = employee.name if employee else None

        if _has_completed_evaluation(db, call_id):
            print(f"[*] Call {call_id} already has a completed evaluation. Skipping duplicate task run.")
            call.status = CallStatus.EVALUATED
            if call.processed_at is None:
                call.processed_at = datetime.now(timezone.utc)
            db.commit()
            redis_client.publish("call_updates", json.dumps({"call_id": call_id, "status": CallStatus.EVALUATED.value}))
            return

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

        _cleanup_partial_evaluation_records(db, call_id)
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
            # ✅ Guard: if score = 0 and sales breakdown has real scores, use breakdown
            raw_score = eval_result.score

            if raw_score == 0 and eval_result.raw_sales_data:
                breakdown = eval_result.raw_sales_data.get("score_breakdown") or {}
                max_pts = {
                    "opening": 10,
                    "script_compliance": 30,
                    "customer_handling": 20,
                    "conduct": 25,
                    "closing": 15,
                }
                fallback_score = sum(
                    float(breakdown.get(field, 0) or 0)
                    for field in max_pts
                )
                if fallback_score > 0:
                    raw_score = fallback_score
                    print(f"[Score Fix] Call {call_id}: Using breakdown score {fallback_score} instead of 0")

            call.evaluation_score = raw_score
            call.strengths = [s.model_dump() if hasattr(s, "model_dump") else s for s in eval_result.strengths]
            call.weaknesses = [w.model_dump() for w in eval_result.weaknesses]
            
            # Compliance Flags (Task 66)
            call.opening_ok = eval_result.opening_ok
            call.closing_ok = eval_result.closing_ok
            call.dob_verified = eval_result.dob_verified

            # --- Score Breakdown Saver (TASK FIX-SB01) ---
            # Rebuild weaknesses with full score/max structure from breakdown
            if eval_result.raw_sales_data:
                breakdown = eval_result.raw_sales_data.get("score_breakdown") or {}
                max_pts = {
                    "opening": 10,
                    "script_compliance": 30,
                    "customer_handling": 20,
                    "conduct": 25,
                    "closing": 15,
                }
                structured_weaknesses = []
                for field, max_val in max_pts.items():
                    earned = float(breakdown.get(field, 0) or 0)
                    deducted = max_val - earned
                    structured_weaknesses.append({
                        "issue": field.replace("_", " ").title(),
                        "detail": f"Score {earned}/{max_val}",
                        "deduction": deducted,
                        "score": earned,
                        "max": max_val,
                    })
                call.weaknesses = structured_weaknesses

            # --- Violations Registration (TASK FIX-SB01) ---
            if eval_result.raw_violations and call.employee_id:
                from app.violations import apply_violations
                violations_result = apply_violations(
                    base_score=call.evaluation_score or 0.0,
                    raw_violations=eval_result.raw_violations,
                    employee_id=call.employee_id,
                    call_id=call.id,
                    campaign_id=call.campaign_id,
                    db=db,
                )
                # Apply score deduction from violations
                if violations_result.get("final_score") is not None:
                    call.evaluation_score = violations_result["final_score"]
                # Flag call for HR review if any violation triggered HR
                if violations_result.get("hr_flag"):
                    call.needs_review = True

                # Check for abuse detection (manipulative_leading or abusive_language)
                abuse_violations = [
                    v for v in eval_result.raw_violations
                    if isinstance(v, dict) and v.get("violation_id") in ["manipulative_leading", "abusive_language"]
                ]
                if abuse_violations:
                    call.qa_alarm = True
                    call.needs_review = True
                    evidence_list = [
                        f"[{v.get('timestamp') or 'No timestamp'}] {v.get('evidence')}"
                        for v in abuse_violations
                    ]
                    call.qa_alarm_reason = "Abusive agent behavior (manipulative/leading instructions or abusive language) detected."
                    call.qa_alarm_evidence = "; ".join(evidence_list)

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
        release_worker_model_resources()
        print_worker_vram(f"END-TASK - Call ID {call_id}")
        db.close()


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

        if _has_completed_evaluation(db, call_id):
            print(f"[*] Live call {call_id} already has a completed evaluation. Skipping duplicate task run.")
            call.status = CallStatus.EVALUATED
            if call.processed_at is None:
                call.processed_at = datetime.now(timezone.utc)
            db.commit()
            redis_client.publish("call_updates", json.dumps({"call_id": call_id, "status": CallStatus.EVALUATED.value}))
            return

        # 1. Start Processing
        _cleanup_partial_evaluation_records(db, call_id)
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
        # ✅ Guard: if score = 0 and sales breakdown has real scores, use breakdown
        raw_score = eval_result.score

        if raw_score == 0 and eval_result.raw_sales_data:
            breakdown = eval_result.raw_sales_data.get("score_breakdown") or {}
            max_pts = {
                "opening": 10,
                "script_compliance": 30,
                "customer_handling": 20,
                "conduct": 25,
                "closing": 15,
            }
            fallback_score = sum(
                float(breakdown.get(field, 0) or 0)
                for field in max_pts
            )
            if fallback_score > 0:
                raw_score = fallback_score
                print(f"[Score Fix] Live Call {call_id}: Using breakdown score {fallback_score} instead of 0")

        call.evaluation_score = raw_score
        call.strengths = [s.model_dump() if hasattr(s, "model_dump") else s for s in eval_result.strengths]
        call.weaknesses = [w.model_dump() for w in eval_result.weaknesses]
        call.opening_ok = eval_result.opening_ok
        call.closing_ok = eval_result.closing_ok
        call.dob_verified = eval_result.dob_verified

        # --- Score Breakdown Saver (TASK FIX-SB01) ---
        if eval_result.raw_sales_data:
            breakdown = eval_result.raw_sales_data.get("score_breakdown") or {}
            max_pts = {
                "opening": 10,
                "script_compliance": 30,
                "customer_handling": 20,
                "conduct": 25,
                "closing": 15,
            }
            structured_weaknesses = []
            for field, max_val in max_pts.items():
                earned = float(breakdown.get(field, 0) or 0)
                deducted = max_val - earned
                structured_weaknesses.append({
                    "issue": field.replace("_", " ").title(),
                    "detail": f"Score {earned}/{max_val}",
                    "deduction": deducted,
                    "score": earned,
                    "max": max_val,
                })
            call.weaknesses = structured_weaknesses

        # --- Violations Registration (TASK FIX-SB01) ---
        if eval_result.raw_violations and call.employee_id:
            from app.violations import apply_violations
            violations_result = apply_violations(
                base_score=call.evaluation_score or 0.0,
                raw_violations=eval_result.raw_violations,
                employee_id=call.employee_id,
                call_id=call.id,
                campaign_id=call.campaign_id,
                db=db,
            )
            if violations_result.get("final_score") is not None:
                call.evaluation_score = violations_result["final_score"]
            if violations_result.get("hr_flag"):
                call.needs_review = True

            # Check for abuse detection (manipulative_leading or abusive_language)
            abuse_violations = [
                v for v in eval_result.raw_violations
                if isinstance(v, dict) and v.get("violation_id") in ["manipulative_leading", "abusive_language"]
            ]
            if abuse_violations:
                call.qa_alarm = True
                call.needs_review = True
                evidence_list = [
                    f"[{v.get('timestamp') or 'No timestamp'}] {v.get('evidence')}"
                    for v in abuse_violations
                ]
                call.qa_alarm_reason = "Abusive agent behavior (manipulative/leading instructions or abusive language) detected."
                call.qa_alarm_evidence = "; ".join(evidence_list)

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
        release_worker_model_resources()
        db.close()
