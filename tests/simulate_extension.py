"""
VoiceQA Extension Simulator
============================
Simulates a WebSocket client's audio streaming behaviour using pure Python.
Connects via WebSocket, streams 16kHz 16-bit Mono PCM in 500ms chunks,
captures RAG suggestions, and uploads a dummy agent microphone file.

Usage:
    python tests/simulate_extension.py [--session_id <id>] [--token <tok>]
    
Requirements: websockets, httpx, numpy
"""

import asyncio
import time
import struct
import logging
import argparse
import numpy as np

try:
    import websockets
except ImportError:
    raise ImportError("Install websockets: pip install websockets")

try:
    import httpx
except ImportError:
    raise ImportError("Install httpx: pip install httpx")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_URL = "http://localhost:8000"
WS_BASE  = "ws://localhost:8000"

# PCM format matching the expected client protocol
SAMPLE_RATE    = 16000           # 16kHz
BYTES_PER_SAMPLE = 2             # 16-bit = 2 bytes
CHANNELS       = 1               # Mono
CHUNK_DURATION_SEC = 0.5         # 500ms chunks
SAMPLES_PER_CHUNK  = int(SAMPLE_RATE * CHUNK_DURATION_SEC)  # 8000 samples
BYTES_PER_CHUNK    = SAMPLES_PER_CHUNK * BYTES_PER_SAMPLE   # 16000 bytes

# Total duration to simulate (seconds)
STREAM_DURATION_SEC = 10

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-5s | %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("Simulator")


# ---------------------------------------------------------------------------
# Audio Generation
# ---------------------------------------------------------------------------

def generate_sine_pcm(frequency: float = 440.0, duration_sec: float = STREAM_DURATION_SEC) -> bytes:
    """
    Generates a synthetic sine wave encoded as 16-bit signed PCM (Little-Endian).
    This matches the exact binary format a WebSocket client sends.
    """
    num_samples = int(SAMPLE_RATE * duration_sec)
    t = np.linspace(0, duration_sec, num_samples, endpoint=False)
    # Generate sine wave in float [-1.0, 1.0]
    wave = np.sin(2 * np.pi * frequency * t)
    # Convert to 16-bit signed PCM [-32768, 32767]
    # PCM encoding: s < 0 ? s * 0x8000 : s * 0x7FFF
    pcm_int16 = np.where(
        wave < 0,
        (wave * 0x8000).astype(np.int16),
        (wave * 0x7FFF).astype(np.int16)
    )
    return pcm_int16.tobytes()


# ---------------------------------------------------------------------------
# WebSocket Streaming
# ---------------------------------------------------------------------------

async def stream_audio(session_id: str, token: str):
    """
    Connects to the backend WebSocket and streams PCM audio in real-time.
    Logs every chunk sent and every suggestion received.
    """
    ws_url = f"{WS_BASE}/api/live/ws/live/{session_id}?token={token}"
    log.info(f"Connecting to WebSocket: {ws_url}")

    suggestion_latencies = []

    async with websockets.connect(ws_url) as ws:
        # --- Wait for handshake ---
        handshake = await ws.recv()
        log.info(f"Handshake received: {handshake}")

        # --- Generate full audio ---
        full_pcm = generate_sine_pcm()
        total_chunks = len(full_pcm) // BYTES_PER_CHUNK
        log.info(f"Streaming {STREAM_DURATION_SEC}s of audio ({total_chunks} chunks, {BYTES_PER_CHUNK} bytes each)")

        # --- Streaming loop ---
        chunk_idx = 0
        for offset in range(0, len(full_pcm), BYTES_PER_CHUNK):
            chunk = full_pcm[offset : offset + BYTES_PER_CHUNK]
            if len(chunk) < BYTES_PER_CHUNK:
                # Pad the last chunk if needed (matches extension behaviour)
                chunk += b'\x00' * (BYTES_PER_CHUNK - len(chunk))

            send_time = time.perf_counter()
            await ws.send(chunk)
            chunk_idx += 1
            log.info(f"[TX] Chunk {chunk_idx}/{total_chunks} sent ({len(chunk)} bytes)")

            # Non-blocking check for incoming suggestions
            try:
                suggestion = await asyncio.wait_for(ws.recv(), timeout=0.05)
                latency_ms = (time.perf_counter() - send_time) * 1000
                suggestion_latencies.append(latency_ms)
                log.info(f"[RX] Suggestion received ({latency_ms:.1f}ms): {suggestion}")
            except asyncio.TimeoutError:
                pass  # No suggestion for this chunk — expected

            # Pace to real-time (500ms per chunk)
            await asyncio.sleep(CHUNK_DURATION_SEC)

        log.info(f"Streaming complete. Total chunks sent: {chunk_idx}")

    # --- Report latency stats ---
    if suggestion_latencies:
        avg = sum(suggestion_latencies) / len(suggestion_latencies)
        p95 = sorted(suggestion_latencies)[int(len(suggestion_latencies) * 0.95)]
        log.info(f"Suggestion Latency — Avg: {avg:.1f}ms | p95: {p95:.1f}ms | Count: {len(suggestion_latencies)}")
    else:
        log.info("No RAG suggestions received during the session.")

    return suggestion_latencies


# ---------------------------------------------------------------------------
# Agent Microphone Upload
# ---------------------------------------------------------------------------

async def upload_agent_audio(session_id: str):
    """
    Simulates a client's post-session microphone upload.
    Sends a small dummy WebM file to the backend.
    """
    # Create a minimal dummy WebM-like payload (just enough to test the endpoint)
    dummy_audio = b'\x1a\x45\xdf\xa3' + b'\x00' * 4096  # Minimal EBML header + padding

    log.info(f"Uploading dummy agent audio for session {session_id}...")

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        response = await client.post(
            f"/api/live/session/{session_id}/upload_agent_audio",
            files={"file": ("agent_mic.webm", dummy_audio, "audio/webm")}
        )

    if response.status_code == 200:
        log.info(f"Agent audio upload successful: {response.json()}")
    else:
        log.error(f"Agent audio upload FAILED ({response.status_code}): {response.text}")

    return response.status_code


# ---------------------------------------------------------------------------
# Full Simulation Flow
# ---------------------------------------------------------------------------

async def run_simulation(session_id: str, token: str):
    """
    Full end-to-end simulation:
    1. Stream tab audio via WebSocket
    2. Upload agent microphone recording
    """
    log.info("=" * 60)
    log.info(f"  VoiceQA Extension Simulator — Session: {session_id[:16]}...")
    log.info("=" * 60)

    # Step 1: Stream audio
    latencies = await stream_audio(session_id, token)

    # Step 2: Upload agent mic
    await upload_agent_audio(session_id)

    log.info("=" * 60)
    log.info("  Simulation Complete")
    log.info("=" * 60)

    return latencies


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VoiceQA Extension Simulator")
    parser.add_argument("--session_id", type=str, required=True, help="Live session ID")
    parser.add_argument("--token", type=str, required=True, help="Reconnect token")
    parser.add_argument("--duration", type=int, default=10, help="Stream duration in seconds")
    args = parser.parse_args()

    STREAM_DURATION_SEC = args.duration

    asyncio.run(run_simulation(args.session_id, args.token))
