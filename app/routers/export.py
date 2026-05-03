import csv
import io
import json
import zipfile
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.models import Call, Campaign, UserRole, Employee
from app.routers.auth import get_current_user

router = APIRouter(prefix="/api/export", tags=["Data Export"])

def redact_text(text: str) -> str:
    """Simple placeholder for PII redaction logic."""
    if not text:
        return ""
    # In a real app, this would use an NER model or regex.
    # For now, we simulate redaction of common patterns if needed.
    return text

@router.get("/csv")
def export_calls_csv(
    campaign_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """
    Export all calls metadata to a streamable CSV.
    """
    query = db.query(Call)
    if campaign_id:
        query = query.filter(Call.campaign_id == campaign_id)
    
    calls = query.all()

    output = io.StringIO()
    writer = csv.writer(output)
    
    # Headers
    writer.writerow([
        "call_id", "date", "agent_id", "campaign_id", "duration", 
        "qa_score", "lead_status", "is_golden_moment", "tags"
    ])

    for call in calls:
        writer.writerow([
            call.id,
            call.created_at.isoformat(),
            call.employee_id,
            call.campaign_id,
            call.audio_duration,
            call.overridden_score or call.evaluation_score,
            call.lead_status.value if call.lead_status else "N/A",
            call.is_golden_moment,
            json.dumps(call.tags) if call.tags else "[]"
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=voiceqa_export_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"}
    )

@router.get("/transcripts")
def export_transcripts_zip(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """
    Zip all transcripts for a specific campaign.
    """
    calls = db.query(Call).filter(Call.campaign_id == campaign_id).all()
    if not calls:
        raise HTTPException(status_code=404, detail="No calls found for this campaign")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for call in calls:
            transcript = call.transcript or "No transcript available"
            # Apply redaction if not admin
            if current_user.role != UserRole.ADMIN:
                transcript = redact_text(transcript)
            
            file_name = f"call_{call.id}_transcript.json"
            data = {
                "call_id": call.id,
                "agent_id": call.employee_id,
                "transcript": transcript,
                "summary": call.call_summary,
                "score": call.overridden_score or call.evaluation_score
            }
            zip_file.writestr(file_name, json.dumps(data, indent=2))

    zip_buffer.seek(0)
    return StreamingResponse(
        iter([zip_buffer.getvalue()]),
        media_type="application/x-zip-compressed",
        headers={"Content-Disposition": f"attachment; filename=campaign_{campaign_id}_transcripts.zip"}
    )
