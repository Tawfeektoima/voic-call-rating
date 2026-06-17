from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid
from app.database import get_db
from app.models import GoldenPairCandidate, CandidateStatus, Employee, Call, UserRole
from app.routers.auth import get_current_user
from app.workers.rag_worker import collection, _get_model
from app.permissions import Permission, require_permission
from app.services.team_scope import is_call_in_qa_scope

router = APIRouter(prefix="/api/review", tags=["HITL Review"])

def _require_review_access(current_user: Employee) -> None:
    require_permission(current_user, Permission.REVIEW_CALLS)


@router.get("/queue")
def get_review_queue(db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    """
    Fetches the list of pending Golden Pair candidates for human review.
    Provides call context as requested for informed decision making.
    """
    _require_review_access(current_user)
    candidates = db.query(GoldenPairCandidate)\
                   .filter(GoldenPairCandidate.status == CandidateStatus.PENDING)\
                   .order_by(GoldenPairCandidate.score.desc())\
                   .all()
    if current_user.role == UserRole.QA:
        candidates = [c for c in candidates if is_call_in_qa_scope(db, current_user.id, c.call_id)]
    
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
def approve_candidate(candidate_id: int, db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    """
    Approves a candidate, updates its status, and indexes it into the local RAG database.
    Ensures that the campaign_id filter (I-01) is preserved in the vector store.
    """
    _require_review_access(current_user)
    candidate = db.query(GoldenPairCandidate).filter(GoldenPairCandidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if current_user.role == UserRole.QA and not is_call_in_qa_scope(db, current_user.id, candidate.call_id):
        raise HTTPException(status_code=403, detail="You do not have permission to review this candidate.")
    
    if candidate.status != CandidateStatus.PENDING:
        raise HTTPException(status_code=400, detail="Candidate already processed")

    try:
        # 1. Update Status in MySQL
        candidate.status = CandidateStatus.APPROVED
        
        # 2. Local RAG Indexing (Phase 5 Logic)
        # Generate embedding locally using the shared model instance
        model = _get_model()
        if model is None:
            raise HTTPException(status_code=503, detail="RAG model not available")
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
def reject_candidate(candidate_id: int, db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    """Rejects a candidate and removes it from the review queue."""
    _require_review_access(current_user)
    candidate = db.query(GoldenPairCandidate).filter(GoldenPairCandidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if current_user.role == UserRole.QA and not is_call_in_qa_scope(db, current_user.id, candidate.call_id):
        raise HTTPException(status_code=403, detail="You do not have permission to review this candidate.")
        
    candidate.status = CandidateStatus.REJECTED
    db.commit()
    return {"status": "rejected"}
