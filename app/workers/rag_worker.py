import os
import json
import asyncio
from typing import Optional, List
from app.database import SessionLocal
from app.models import SystemLog
from app.config import get_settings

try:
    import chromadb
except Exception:  # Optional dependency for lightweight test/CI environments
    chromadb = None

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # Optional dependency for lightweight test/CI environments
    SentenceTransformer = None

try:
    import redis.asyncio as aioredis
except Exception:  # Optional dependency for lightweight test/CI environments
    aioredis = None

# ---------------------------------------------------------------------------
# Local Resource Initialization
# ---------------------------------------------------------------------------

# Local Vector DB: Persistent ChromaDB
db_path = "./local_chroma_db"
os.makedirs(db_path, exist_ok=True)
if chromadb is not None:
    chroma_client = chromadb.PersistentClient(path=db_path)
    collection = chroma_client.get_or_create_collection(name="agent_suggestions")
else:
    chroma_client = None
    collection = None

# Local Embeddings: Lazy-loaded SentenceTransformers (all-MiniLM-L6-v2)
# This model runs locally on CPU/GPU and provides high-quality 384d embeddings
_model = None

def _get_model():
    """Lazy-load the embedding model on first use, not at import time."""
    global _model
    if _model is not None:
        return _model
    if SentenceTransformer is None:
        print("WARNING: sentence-transformers is unavailable. RAG suggestions will be disabled.")
        return None

    print("Loading local embedding model (all-MiniLM-L6-v2)...")
    # Temporarily remove HF_TOKEN if it's expired — this is a PUBLIC model
    # and an expired token causes 401 errors even on public repos
    saved_token = os.environ.pop("HF_TOKEN", None)
    saved_token2 = os.environ.pop("HUGGING_FACE_HUB_TOKEN", None)
    try:
        _model = SentenceTransformer("all-MiniLM-L6-v2", token=False)
        print("Embedding model loaded successfully.")
    except Exception as e:
        print(f"WARNING: Failed to load embedding model: {e}")
        print("RAG suggestions will be disabled.")
        try:
            db_log = SessionLocal()
            log_entry = SystemLog(
                error_type="processing_failure",
                error_message=f"RAG embedding model load failed: {str(e)}",
                severity="warning"
            )
            db_log.add(log_entry)
            db_log.commit()
            db_log.close()
        except Exception as log_err:
            print(f"[RAG Logging Error] Failed to write SystemLog: {log_err}")
    finally:
        # Restore tokens for other services (pyannote, etc.)
        if saved_token:
            os.environ["HF_TOKEN"] = saved_token
        if saved_token2:
            os.environ["HUGGING_FACE_HUB_TOKEN"] = saved_token2
    return _model

# Redis Cache for RAG Suggestions
settings = get_settings()
redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True) if aioredis is not None else None


def get_company_trigger_keywords(company_id: int) -> List[str]:
    """
    Mock function to simulate fetching company-specific trigger keywords.
    Addresses requirement for Arabic keyword support.
    """
    # In production, this would be fetched from a Redis hash or DB config
    return [
        "price", "cost", "discount", "expensive", "billing", 
        "سعر", "تكلفة", "خصم", "غالي", "فاتورة", "اشتراك"
    ]

async def get_agent_suggestion(
    session_id: str, 
    campaign_id: int, 
    company_id: int, 
    transcript_text: str
) -> Optional[str]:
    """
    Pure Retrieval RAG Worker (Ultra-low latency, 100% Local).
    Implements I-01, I-02, and I-05.
    """
    try:
        # 1. Trigger Keyword Detection (Saves compute)
        keywords = get_company_trigger_keywords(company_id)
        text_lower = transcript_text.lower()
        if not any(kw in text_lower for kw in keywords):
            return None

        # 2. Redis Embedding Cache (I-05: 1-hour TTL)
        # We cache the final suggestion for common phrases
        if redis_client is None or collection is None:
            return None
        cache_key = f"rag_cache:{campaign_id}:{text_lower[:50]}"
        cached_suggestion = await redis_client.get(cache_key)
        if cached_suggestion:
            print(f"[RAG {session_id}] Cache Hit for: '{text_lower[:30]}...'")
            return cached_suggestion

        # 3. Local Embedding Generation
        # This is the most compute-intensive part, handled locally
        model = _get_model()
        if model is None:
            return None  # RAG disabled — model failed to load
        loop = asyncio.get_event_loop()
        query_embedding = await loop.run_in_executor(None, model.encode, transcript_text)
        query_embedding = query_embedding.tolist()

        # 4. Mandatory RAG Filtering (I-01)
        # We strictly filter by campaign_id to ensure relevant suggestions
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=1,
            where={"campaign_id": campaign_id}
        )

        if not results or not results['documents'] or not results['documents'][0]:
            return None

        # 5. Confidence Threshold (I-02)
        # ChromaDB returns L2 distance. We convert it to a similarity-like score.
        # Threshold 0.72 ensures high-precision suggestions.
        distance = results['distances'][0][0]
        # Similarity approx: 1 / (1 + distance) or 1 - (distance / 2) depending on scaling
        confidence = 1.0 - (distance / 2.0) 
        
        if confidence > 0.72:
            suggestion = results['documents'][0][0]
            
            # Cache the successful retrieval
            await redis_client.setex(cache_key, 3600, suggestion)
            
            print(f"[RAG {session_id}] Suggestion Found (Confidence: {confidence:.2f})")
            return suggestion

        return None

    except Exception as e:
        print(f"[RAG Error {session_id}] {str(e)}")
        try:
            db_log = SessionLocal()
            log_entry = SystemLog(
                error_type="processing_failure",
                error_message=f"RAG suggestion query failed for session {session_id}: {str(e)}",
                severity="warning"
            )
            db_log.add(log_entry)
            db_log.commit()
            db_log.close()
        except Exception as log_err:
            print(f"[RAG Logging Error] Failed to write SystemLog: {log_err}")
        return None
