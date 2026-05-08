from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid
from app.database import get_db
from app.models import GoldenPairCandidate, CandidateStatus
from app.workers.rag_worker import collection, model

router = APIRouter(prefix="/api/review", tags=["HITL Review"])

@router.get("/queue")
def get_review_queue(db: Session = Depends(get_db)):
    """
    Fetches the list of pending Golden Pair candidates for human review.
    Provides call context as requested for informed decision making.
    """
    candidates = db.query(GoldenPairCandidate)\
                   .filter(GoldenPairCandidate.status == CandidateStatus.PENDING)\
                   .order_by(GoldenPairCandidate.score.desc())\
                   .all()
    
    return [
        {
            "id": c.id,
            "call_id": c.call_id,
            "campaign_id": c.campaign_id,
            "question": c.question,
            "answer": c.answer,
            "score": c.score,
            "call_link": f"/dashboard/calls/{c.call_id}", # Context for reviewer
            "created_at": c.created_at
        } for c in candidates
    ]

@router.post("/{candidate_id}/approve")
def approve_candidate(candidate_id: int, db: Session = Depends(get_db)):
    """
    Approves a candidate, updates its status, and indexes it into the local RAG database.
    Ensures that the campaign_id filter (I-01) is preserved in the vector store.
    """
    candidate = db.query(GoldenPairCandidate).filter(GoldenPairCandidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    if candidate.status != CandidateStatus.PENDING:
        raise HTTPException(status_code=400, detail="Candidate already processed")

    try:
        # 1. Update Status in MySQL
        candidate.status = CandidateStatus.APPROVED
        
        # 2. Local RAG Indexing (Phase 5 Logic)
        # Generate embedding locally using the shared model instance
        embedding = model.encode(candidate.question).tolist()
        
        # Add to the local ChromaDB collection
        collection.add(
            ids=[str(uuid.uuid4())],
            embeddings=[embedding],
            metadatas=[{"campaign_id": candidate.campaign_id}], # CRITICAL: I-01 Filter
            documents=[candidate.answer]
        )
        
        db.commit()
        print(f"[HITL] Candidate {candidate_id} approved and indexed into RAG DB.")
        return {"status": "approved", "indexed": True}

    except Exception as e:
        db.rollback()
        print(f"[HITL Error] Failed to approve candidate {candidate_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")

@router.post("/{candidate_id}/reject")
def reject_candidate(candidate_id: int, db: Session = Depends(get_db)):
    """Rejects a candidate and removes it from the review queue."""
    candidate = db.query(GoldenPairCandidate).filter(GoldenPairCandidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    candidate.status = CandidateStatus.REJECTED
    db.commit()
    return {"status": "rejected"}
