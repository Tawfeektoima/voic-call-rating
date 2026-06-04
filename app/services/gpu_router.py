import redis
import os
from typing import List
from app.config import get_settings

# Setup Redis client for router (Shared with ASR heartbeat)
settings = get_settings()
redis_router = redis.from_url(settings.REDIS_URL, decode_responses=True)

async def get_best_gpu() -> int:
    """
    Implements Critical Fix C-5: Dynamic GPU Session Routing & Failover.
    Finds the healthy GPU (with active heartbeat) that has the lowest load.
    
    Returns:
        int: GPU ID
    """
    # Detect actual hardware capability (I-10)
    try:
        import torch
        num_gpus = torch.cuda.device_count() if torch.cuda.is_available() else 0
        if num_gpus == 0:
            return 0 # CPU or no CUDA
        AVAILABLE_GPUS = list(range(num_gpus))
    except ImportError:
        AVAILABLE_GPUS = [0] # Fallback to single GPU 0

    gpu_stats = []
    for gpu_id in AVAILABLE_GPUS:
        heartbeat = redis_router.get(f"gpu:{gpu_id}:heartbeat")
        if heartbeat == "active":
            # GPU is healthy, fetch current load
            load_str = redis_router.get(f"gpu:{gpu_id}:load")
            load = int(load_str) if load_str else 0
            gpu_stats.append({"id": gpu_id, "load": load})
        else:
            print(f"[Router] GPU {gpu_id} heartbeat missing. Excluding from routing.")

    if not gpu_stats:
        # Fallback if no heartbeats are found (system-wide startup or failure)
        print("[Router] WARNING: No active GPUs found. Falling back to GPU 0.")
        return 0

    # Sort by load (ascending) and return the ID of the least loaded GPU
    gpu_stats.sort(key=lambda x: x["load"])
    best_gpu = gpu_stats[0]["id"]
    
    print(f"[Router] Routing new session to GPU {best_gpu} (Load: {gpu_stats[0]['load']})")
    return best_gpu
