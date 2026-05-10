import struct
import redis.asyncio as aioredis
from app.config import get_settings

settings = get_settings()

REDIS_STREAM_PREFIX = "agent_audio:"
CHUNK_HEADER_BYTES  = 8   # float64 Unix timestamp

async def archive_agent_chunk(session_id: str, pcm_data: bytes, timestamp: float) -> None:
    """
    Appends a timestamped 3200-byte PCM chunk to a Redis Stream.
    CRITICAL: This function must never interact with WhisperX or any GPU resource.
    """
    assert len(pcm_data) == 3200, f"Expected 3200 bytes, got {len(pcm_data)}"
    header  = struct.pack('<d', timestamp)   # 8-byte little-endian double
    payload = header + pcm_data             # 3208 bytes total per entry

    async with aioredis.from_url(settings.CELERY_BROKER_URL) as r: # Uses the existing Redis URL
        await r.xadd(
            f"{REDIS_STREAM_PREFIX}{session_id}",
            {"chunk": payload},
            maxlen=10000   # safety cap (~16 minutes at 100ms chunks)
        )

async def read_agent_stream(session_id: str) -> list[tuple[float, bytes]]:
    """
    Reads all archived agent chunks for a completed session.
    Returns list of (unix_timestamp, pcm_bytes) tuples, sorted by time.
    """
    async with aioredis.from_url(settings.CELERY_BROKER_URL) as r:
        entries = await r.xrange(f"{REDIS_STREAM_PREFIX}{session_id}")

    result = []
    for _, fields in entries:
        payload   = fields[b"chunk"]
        timestamp = struct.unpack('<d', payload[:CHUNK_HEADER_BYTES])[0]
        pcm_data  = payload[CHUNK_HEADER_BYTES:]
        result.append((timestamp, pcm_data))

    return sorted(result, key=lambda x: x[0])   # sort by timestamp

async def flush_agent_stream(session_id: str) -> None:
    """Deletes the Redis stream after post-call processing is complete."""
    async with aioredis.from_url(settings.CELERY_BROKER_URL) as r:
        await r.delete(f"{REDIS_STREAM_PREFIX}{session_id}")
