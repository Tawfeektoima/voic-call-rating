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
from app.services.export import ExportService

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
        "qa_score", "lead_status", "is_golden_moment", "tags",
        "primary_outcome", "outcome_value", "talk_ratio", "follow_up_required",
        "campaign_specific_data"
    ])

    for call in calls:
        outcome = call.outcome
        writer.writerow([
            call.id,
            call.created_at.isoformat(),
            call.employee_id,
            call.campaign_id,
            call.audio_duration,
            call.overridden_score or call.evaluation_score,
            call.lead_status.value if hasattr(call.lead_status, 'value') else (call.lead_status or "N/A"),
            call.is_golden_moment,
            json.dumps(call.tags) if call.tags else "[]",
            outcome.primary_outcome if outcome else "N/A",
            outcome.outcome_value if outcome else 0.0,
            outcome.talk_ratio if outcome else 0.0,
            outcome.follow_up_required if outcome else False,
            json.dumps(outcome.campaign_specific_data) if outcome and outcome.campaign_specific_data else "{}"
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=voiceqa_export_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"}
    )


@router.get("/xlsx")
def export_dataset_xlsx(
    campaign_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """
    Export a Data-Science-Ready .xlsx dataset with ~50 columns.
    Includes multi-table joins, JSON flattening, acoustic emotion %,
    temporal features, and formatted headers (Task 64).
    """
    df_master, df_qa, df_ann = ExportService.build_dataset(db, campaign_id=campaign_id)

    if df_master.empty:
        raise HTTPException(status_code=404, detail="No evaluated calls found for export.")

    buffer = ExportService.to_styled_xlsx(df_master, df_qa, df_ann)

    filename = f"voiceqa_dataset_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
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
