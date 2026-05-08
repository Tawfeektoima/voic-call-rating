import os
import json
import asyncio
import chromadb
from sentence_transformers import SentenceTransformer
import redis.asyncio as aioredis
from typing import Optional, List

# ---------------------------------------------------------------------------
# Local Resource Initialization
# ---------------------------------------------------------------------------

# Local Vector DB: Persistent ChromaDB
db_path = "./local_chroma_db"
os.makedirs(db_path, exist_ok=True)
chroma_client = chromadb.PersistentClient(path=db_path)
collection = chroma_client.get_or_create_collection(name="agent_suggestions")

# Local Embeddings: SentenceTransformers (all-MiniLM-L6-v2)
# This model runs locally on CPU/GPU and provides high-quality 384d embeddings
print("Loading local embedding model (all-MiniLM-L6-v2)...")
model = SentenceTransformer('all-MiniLM-L6-v2')

# Redis Cache for RAG Suggestions
redis_client = aioredis.from_url("redis://localhost:6379", decode_responses=True)

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
        cache_key = f"rag_cache:{campaign_id}:{text_lower[:50]}"
        cached_suggestion = await redis_client.get(cache_key)
        if cached_suggestion:
            print(f"[RAG {session_id}] Cache Hit for: '{text_lower[:30]}...'")
            return cached_suggestion

        # 3. Local Embedding Generation
        # This is the most compute-intensive part, handled locally
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
        return None
