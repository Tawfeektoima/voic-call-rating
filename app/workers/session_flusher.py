from sqlalchemy.orm import Session
from app.models import LiveSession, LiveTranscriptSegment, Call, LiveSessionStatus, CallStatus
from app.worker import evaluate_live_call_task
from app.services.transcription import transcriber
import asyncio

async def flush_live_session(session_id: str, db: Session):
    """
    Assembles real-time transcript segments into a standard Call record.
    Triggers the existing QA evaluation pipeline asynchronously.
    """
    try:
        # 1. Atomic Transaction Start & State Progression
        session = db.query(LiveSession).filter(LiveSession.id == session_id).first()
        if not session or session.status != LiveSessionStatus.ACTIVE:
            print(f"[Flush {session_id}] Session not found or already processed.")
            return
            
        session.status = LiveSessionStatus.FLUSHING
        db.commit()

        # 2. Wait for Agent Microphone Upload (Timeout: 2 minutes)
        # Improvement: Handle disconnections by waiting for the extension to upload the mic recording
        wait_time = 0
        while not session.agent_audio_path and wait_time < 120:
            await asyncio.sleep(5)
            wait_time += 5
            db.refresh(session)
            if session.agent_audio_path:
                print(f"[Flush {session_id}] Agent audio detected after {wait_time}s.")
                break

        # 3. Transcribe Agent Voice (Post-Call to save GPU)
        agent_segments = []
        if session.agent_audio_path:
            print(f"[Flush {session_id}] Transcribing agent-side recording...")
            try:
                # Reuse the standard transcriber (WhisperX)
                raw_agent, _ = transcriber.process_audio(session.agent_audio_path)
                for i, seg in enumerate(raw_agent):
                    agent_segments.append({
                        "id": f"agent_{i}",
                        "start": float(seg.get("start", 0.0)),
                        "end": float(seg.get("end", 0.0)),
                        "speaker": "Agent",
                        "text": seg.get("text", ""),
                        "emotion": "neutral"
                    })
            except Exception as trans_err:
                print(f"[Flush {session_id}] Agent transcription failed: {str(trans_err)}")

        # 4. Data Assembly (Customer Side)
        customer_segments_raw = db.query(LiveTranscriptSegment)\
                     .filter(LiveTranscriptSegment.session_id == session_id)\
                     .order_by(LiveTranscriptSegment.timestamp.asc())\
                     .all()
        
        customer_segments = []
        for i, seg in enumerate(customer_segments_raw):
            customer_segments.append({
                "id": f"cust_{i}",
                "start": float(seg.timestamp),
                "end": float(seg.timestamp + 1.5), 
                "speaker": "Customer", # Live capture is always customer-side (Tab Audio)
                "text": seg.text,
                "emotion": "neutral"
            })

        # 5. Smart Interleaving (Chronological Merge)
        full_transcript = customer_segments + agent_segments
        full_transcript.sort(key=lambda x: x['start'])

        # 6. Create Call Record (Improvement I-03: source='live')
        new_call = Call(
            employee_id=session.agent_id,
            campaign_id=session.campaign_id,
            transcript=full_transcript,
            audio_file_path=None,
            source="live", # CRITICAL: I-03 Source Flag
            status=CallStatus.PENDING
        )
        db.add(new_call)
        db.flush() # Generate new_call.id for linking

        # 4. Link and Complete Transaction
        session.call_id = new_call.id
        session.status = LiveSessionStatus.COMPLETE
        db.commit()

        # 5. Trigger QA Evaluation
        # We dispatch to Celery to maintain ultra-low latency for the WebSocket closure
        evaluate_live_call_task.delay(new_call.id)
        
        print(f"[Flush {session_id}] Success: Call {new_call.id} created and evaluation triggered.")

    except Exception as e:
        db.rollback()
        print(f"[Flush Error {session_id}] Critical failure during session flush: {str(e)}")
        if session:
            # Revert status to allow retry or manual intervention if needed
            session.status = LiveSessionStatus.ACTIVE
            db.commit()
