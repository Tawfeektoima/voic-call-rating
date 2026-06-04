import asyncio
import time
import numpy as np
import warnings
from typing import Optional
from app.workers.rag_worker import get_agent_suggestion
from app.database import SessionLocal
from app.models import LiveTranscriptSegment, SystemLog
import redis
import os
from app.config import get_settings

# Suppress warnings in the worker process
warnings.filterwarnings("ignore", category=UserWarning)

# ANSI Colors for cleaner logs
CLR_GREEN = "\033[92m"
CLR_RESET = "\033[0m"

# C-6: Concurrency limit for GPU protection
# Caps the number of simultaneous WhisperX tasks to prevent OOM
gpu_semaphore = asyncio.Semaphore(2)  # Max 2 concurrent transcriptions (RTX 3050 safe)

# C-5: Dynamic GPU Session Routing
# Connect to Redis for heartbeats and load tracking
settings = get_settings()
redis_hb = redis.from_url(settings.REDIS_URL, decode_responses=True)
MY_GPU_ID = int(os.getenv("GPU_ID", 0))

async def publish_gpu_heartbeat(active_count: int):
    """
    Publishes GPU health and load status to Redis. 
    Used by gpu_router.py for failover and load balancing.
    """
    try:
        # Mark as active for 15 seconds
        redis_hb.setex(f"gpu:{MY_GPU_ID}:heartbeat", 15, "active")
        # Update current session load
        redis_hb.set(f"gpu:{MY_GPU_ID}:load", active_count)
    except Exception as e:
        print(f"[GPU HB Error] GPU {MY_GPU_ID}: {str(e)}")

async def start_heartbeat_loop(get_active_count_func):
    """
    Background loop to maintain GPU heartbeat.
    """
    while True:
        await publish_gpu_heartbeat(get_active_count_func())
        await asyncio.sleep(5) # 5-second interval

def _is_voice_active(pcm_bytes: bytes, threshold: float = 0.01) -> bool:
    """
    Returns True if the chunk contains actual speech energy.
    Filters out silence/hold music before hitting WhisperX.
    Threshold 0.01 RMS works well for 16-bit PCM in practice.
    """
    samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    rms = np.sqrt(np.mean(samples ** 2))
    return rms > threshold

class SessionASRBuffer:
    """
    Manages a rolling audio buffer for a live session.
    Implements Task 4 requirements for rolling context and overlap.
    """
    def __init__(self, session_id: str, campaign_id: int, company_id: int):
        self.session_id = session_id
        self.campaign_id = campaign_id
        self.company_id = company_id
        self.buffer = bytearray()
        self.queue = asyncio.Queue()
        self.last_text = ""  # For deduplication (I-03)
        
        # Buffer Config (16kHz, 16-bit Mono PCM)
        # 16,000 samples/sec * 2 bytes/sample = 32,000 bytes/sec
        self.trigger_bytes = 48000  # 1.5 seconds of audio
        self.overlap_bytes = 16000  # 0.5 seconds of overlap
        
        self.elapsed_time = 0.0     # Tracks the start time of the next segment
        self.is_running = True
        self.worker_task = asyncio.create_task(self._process_loop())

    async def push(self, chunk: bytes):
        """
        STRICT CONTRACT: Accepts ONLY customer audio — exactly 3200 bytes
        (1600 samples × 2 bytes, 16-bit mono PCM at 16kHz = 100ms).
        Agent audio must NEVER enter this method.
        """
        assert len(chunk) == 3200, (
            f"[ASR GUARD] Wrong chunk size {len(chunk)}. "
            f"Only customer_data[0:3200] is allowed here."
        )

        # Energy-based VAD: skip silent chunks to reduce GPU usage
        if not _is_voice_active(chunk):
            return   # Do not send silence to WhisperX

        await self.queue.put(chunk)

    async def flush(self):
        """Signals end of stream and processes the final chunk."""
        self.is_running = False
        await self.queue.put(None) # Sentinel to end loop
        await self.worker_task

    async def _process_loop(self):
        """Consumer loop that monitors the buffer and triggers transcription."""
        while self.is_running or not self.queue.empty():
            try:
                chunk = await self.queue.get()
                
                if chunk is None:
                    # Flush any remaining audio
                    if len(self.buffer) > 1000:
                        await self._transcribe(bytes(self.buffer), self.elapsed_time)
                    break
                
                self.buffer.extend(chunk)
                
                # C-6: Rolling Buffer Trigger
                if len(self.buffer) >= self.trigger_bytes:
                    # Copy data for transcription
                    to_transcribe = bytes(self.buffer)
                    
                    segment_ts = self.elapsed_time
                    
                    # C-6: Retention/Overlap logic
                    # Retain last 0.5s for overlap context. We "move forward" by 1.0s.
                    self.buffer = self.buffer[-self.overlap_bytes:]
                    self.elapsed_time += 1.0
                    
                    # Offload to transcription
                    asyncio.create_task(self._transcribe(to_transcribe, segment_ts))
            
            except Exception as e:
                print(f"[ASR Error {self.session_id}] In process loop: {str(e)}")

    async def _transcribe(self, pcm_bytes: bytes, timestamp: float):
        """Normalization, Mock Transcription, and Persistence."""
        async with gpu_semaphore:
            try:
                # 1. Convert raw bytes to int16 then normalize to float32
                audio_int16 = np.frombuffer(pcm_bytes, dtype=np.int16)
                # Normalize by dividing by 32768.0 (2^15)
                audio_float32 = audio_int16.astype(np.float32) / 32768.0
                
                # In Phase 5, we will call WhisperX here.
                text = "How much does the subscription cost?" if "cost" not in self.session_id else "I'll take it."
                
                # Deduplication logic (I-03)
                if text == self.last_text:
                    return
                self.last_text = text

                print(f"[ASR {self.session_id}] GPU processing {len(audio_float32)} samples at {timestamp}s...")
                print(f"{CLR_GREEN}-> Detected Speech: {text}{CLR_RESET}")
                
                # Persist segment to Database for QA Integration (Phase 6)
                db = SessionLocal()
                try:
                    new_seg = LiveTranscriptSegment(
                        session_id=self.session_id,
                        timestamp=timestamp,
                        speaker="Agent", # Mock speaker detection
                        text=text
                    )
                    db.add(new_seg)
                    db.commit()
                except Exception as db_err:
                    print(f"[ASR DB Error] {str(db_err)}")
                    try:
                        db_log = SessionLocal()
                        log_entry = SystemLog(
                            error_type="processing_failure",
                            error_message=f"ASR DB persistence failed for session {self.session_id}: {str(db_err)}",
                            severity="warning"
                        )
                        db_log.add(log_entry)
                        db_log.commit()
                        db_log.close()
                    except Exception as log_err:
                        print(f"[ASR Logging Error] Failed to write SystemLog: {log_err}")
                finally:
                    db.close()

                # Simulate processing time
                await asyncio.sleep(0.2)
                
                # 3. Trigger RAG Worker (Phase 5)
                # For this MVP, we use a mock transcript segment
                mock_text = "How much does the subscription cost?" if "cost" not in self.session_id else "No trigger"
                suggestion = await get_agent_suggestion(
                    self.session_id, self.campaign_id, self.company_id, mock_text
                )
                
                if suggestion:
                    # TODO: Push suggestion to WebSocket for agent UI
                    print(f"[RAG {self.session_id}] Suggestion: {suggestion}")
                
            except Exception as e:
                print(f"[ASR Error {self.session_id}] During transcription: {str(e)}")
                try:
                    db_log = SessionLocal()
                    log_entry = SystemLog(
                        error_type="processing_failure",
                        error_message=f"ASR transcription failed for session {self.session_id}: {str(e)}",
                        severity="critical"
                    )
                    db_log.add(log_entry)
                    db_log.commit()
                    db_log.close()
                except Exception as log_err:
                    print(f"[ASR Logging Error] Failed to write SystemLog: {log_err}")
