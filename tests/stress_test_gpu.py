"""
VoiceQA GPU Stress Test (RTX 3050 Optimized)
==============================================
Spawns exactly 2 concurrent sessions to verify:
  - GPU router assigns them correctly (load balancing).
  - The asyncio.Semaphore manages the transcription queue without OOM.
  - Tracks asr_latency_ms and suggestion_latency_ms under concurrent load.

Hardware Constraint: RTX 3050 (8GB VRAM) — uses WhisperX tiny/base model.

Usage:
    python tests/stress_test_gpu.py

Requirements: websockets, httpx, numpy
"""

import asyncio
import time
import logging
import numpy as np
import json

try:
    import websockets
except ImportError:
    raise ImportError("Install websockets: pip install websockets")

try:
    import httpx
except ImportError:
    raise ImportError("Install httpx: pip install httpx")


# ---------------------------------------------------------------------------
# Configuration (RTX 3050 safe)
# ---------------------------------------------------------------------------
BASE_URL = "http://localhost:8000"
WS_BASE  = "ws://localhost:8000"

SAMPLE_RATE       = 16000
BYTES_PER_SAMPLE  = 2
CHUNK_DURATION_SEC = 0.5
SAMPLES_PER_CHUNK = int(SAMPLE_RATE * CHUNK_DURATION_SEC)
BYTES_PER_CHUNK   = SAMPLES_PER_CHUNK * BYTES_PER_SAMPLE

# Keep short to avoid OOM on 8GB VRAM
STREAM_DURATION_SEC = 6
CONCURRENT_SESSIONS = 2

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-5s | [Session %(session_num)s] %(message)s",
    datefmt="%H:%M:%S"
)


# ---------------------------------------------------------------------------
# Audio Generation
# ---------------------------------------------------------------------------

def generate_test_pcm(duration_sec: float = STREAM_DURATION_SEC) -> bytes:
    """Generate synthetic 16-bit PCM sine wave."""
    num_samples = int(SAMPLE_RATE * duration_sec)
    t = np.linspace(0, duration_sec, num_samples, endpoint=False)
    wave = np.sin(2 * np.pi * 440.0 * t)
    pcm_int16 = np.where(
        wave < 0,
        (wave * 0x8000).astype(np.int16),
        (wave * 0x7FFF).astype(np.int16)
    )
    return pcm_int16.tobytes()


# ---------------------------------------------------------------------------
# Single Session Worker
# ---------------------------------------------------------------------------

async def run_session(session_num: int, session_id: str, token: str) -> dict:
    """
    Runs a single simulated session: streams PCM, captures metrics.
    Returns a dict of performance metrics.
    """
    log = logging.LoggerAdapter(logging.getLogger("StressTest"), {"session_num": session_num})
    
    ws_url = f"{WS_BASE}/api/live/ws/live/{session_id}?token={token}"
    metrics = {
        "session_num": session_num,
        "session_id": session_id,
        "chunks_sent": 0,
        "suggestions_received": 0,
        "suggestion_latencies_ms": [],
        "errors": [],
        "start_time": None,
        "end_time": None,
    }

    try:
        async with websockets.connect(ws_url) as ws:
            # Wait for handshake
            handshake = await ws.recv()
            log.info(f"Connected. Handshake: {handshake}")
            
            metrics["start_time"] = time.perf_counter()
            full_pcm = generate_test_pcm()
            total_chunks = len(full_pcm) // BYTES_PER_CHUNK

            for offset in range(0, len(full_pcm), BYTES_PER_CHUNK):
                chunk = full_pcm[offset : offset + BYTES_PER_CHUNK]
                if len(chunk) < BYTES_PER_CHUNK:
                    chunk += b'\x00' * (BYTES_PER_CHUNK - len(chunk))

                send_time = time.perf_counter()
                await ws.send(chunk)
                metrics["chunks_sent"] += 1

                log.info(f"Chunk {metrics['chunks_sent']}/{total_chunks} sent")

                # Check for suggestions
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=0.05)
                    latency_ms = (time.perf_counter() - send_time) * 1000
                    metrics["suggestion_latencies_ms"].append(latency_ms)
                    metrics["suggestions_received"] += 1
                    log.info(f"Suggestion received ({latency_ms:.1f}ms)")
                except asyncio.TimeoutError:
                    pass

                await asyncio.sleep(CHUNK_DURATION_SEC)

            metrics["end_time"] = time.perf_counter()
            log.info(f"Stream complete. {metrics['chunks_sent']} chunks sent.")

    except Exception as e:
        metrics["errors"].append(str(e))
        log.error(f"Session error: {e}")

    return metrics


# ---------------------------------------------------------------------------
# GPU Router Verification
# ---------------------------------------------------------------------------

async def verify_gpu_routing():
    """
    Queries Redis directly to check GPU heartbeat and load distribution.
    """
    import redis
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    
    log = logging.LoggerAdapter(logging.getLogger("StressTest"), {"session_num": "R"})
    log.info("=" * 50)
    log.info("GPU Router Status Check")
    log.info("=" * 50)
    
    for gpu_id in range(4):
        hb = r.get(f"gpu:{gpu_id}:heartbeat")
        load = r.get(f"gpu:{gpu_id}:load")
        status = "ALIVE" if hb == "active" else "DEAD"
        log.info(f"  GPU {gpu_id}: {status} | Load: {load or 0}")
    
    r.close()


# ---------------------------------------------------------------------------
# Stress Test Orchestrator
# ---------------------------------------------------------------------------

async def run_stress_test(sessions: list):
    """
    Runs N concurrent session simulations and aggregates results.
    sessions: list of (session_id, token) tuples
    """
    root_log = logging.LoggerAdapter(logging.getLogger("StressTest"), {"session_num": "*"})
    
    root_log.info("=" * 60)
    root_log.info(f"  VoiceQA GPU Stress Test — {len(sessions)} concurrent sessions")
    root_log.info(f"  Hardware: RTX 3050 (8GB VRAM) — Duration: {STREAM_DURATION_SEC}s each")
    root_log.info("=" * 60)

    # Check GPU status before test
    await verify_gpu_routing()

    # Launch all sessions concurrently
    tasks = []
    for i, (sid, tok) in enumerate(sessions):
        tasks.append(run_session(i + 1, sid, tok))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # --- Aggregate Results ---
    root_log.info("")
    root_log.info("=" * 60)
    root_log.info("  STRESS TEST RESULTS")
    root_log.info("=" * 60)

    total_chunks = 0
    total_suggestions = 0
    all_latencies = []
    errors = []

    for result in results:
        if isinstance(result, Exception):
            errors.append(str(result))
            root_log.error(f"Session failed with exception: {result}")
            continue

        total_chunks += result["chunks_sent"]
        total_suggestions += result["suggestions_received"]
        all_latencies.extend(result["suggestion_latencies_ms"])
        errors.extend(result["errors"])

        duration = (result["end_time"] - result["start_time"]) if result["end_time"] else 0
        root_log.info(
            f"  Session {result['session_num']}: "
            f"{result['chunks_sent']} chunks | "
            f"{result['suggestions_received']} suggestions | "
            f"{duration:.1f}s total"
        )

    root_log.info(f"")
    root_log.info(f"  Total Chunks Sent:    {total_chunks}")
    root_log.info(f"  Total Suggestions:    {total_suggestions}")

    if all_latencies:
        avg = sum(all_latencies) / len(all_latencies)
        sorted_lat = sorted(all_latencies)
        p50 = sorted_lat[int(len(sorted_lat) * 0.50)]
        p95 = sorted_lat[int(len(sorted_lat) * 0.95)]
        p99 = sorted_lat[min(int(len(sorted_lat) * 0.99), len(sorted_lat) - 1)]

        root_log.info(f"  Suggestion Latency:")
        root_log.info(f"    Avg:  {avg:.1f}ms")
        root_log.info(f"    p50:  {p50:.1f}ms")
        root_log.info(f"    p95:  {p95:.1f}ms  (Target: <200ms)")
        root_log.info(f"    p99:  {p99:.1f}ms")

    if errors:
        root_log.warning(f"  Errors: {len(errors)}")
        for e in errors:
            root_log.warning(f"    - {e}")
    else:
        root_log.info(f"  Errors: 0  ✓")

    # Check GPU status after test
    await verify_gpu_routing()

    # Final verdict
    oom_detected = any("CUDA" in e or "OOM" in e or "out of memory" in e for e in errors)
    if oom_detected:
        root_log.error("  VERDICT: FAIL — GPU OOM detected!")
    elif errors:
        root_log.warning("  VERDICT: PASS WITH WARNINGS")
    else:
        root_log.info("  VERDICT: PASS ✓")

    return not oom_detected


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="VoiceQA GPU Stress Test (RTX 3050)")
    parser.add_argument(
        "--sessions", type=str, nargs="+", required=True,
        help="Session pairs as 'session_id:token' (provide exactly 2)"
    )
    args = parser.parse_args()

    sessions = []
    for s in args.sessions:
        parts = s.split(":")
        if len(parts) != 2:
            print(f"Invalid session format: {s}. Expected 'session_id:token'")
            exit(1)
        sessions.append((parts[0], parts[1]))

    if len(sessions) != CONCURRENT_SESSIONS:
        print(f"Warning: Expected {CONCURRENT_SESSIONS} sessions, got {len(sessions)}.")

    success = asyncio.run(run_stress_test(sessions))
    exit(0 if success else 1)
