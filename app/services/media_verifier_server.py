"""Minimal no-network HTTP boundary for resource-bounded media inspection."""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, field_validator

from app.services.recording_ingestion import FfprobeMediaVerifier, RecordingIngestionSecurityError, _resolve_existing_path_within


class VerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    filename: str

    @field_validator("filename")
    @classmethod
    def safe_filename(cls, value: str) -> str:
        if Path(value).name != value or value in {"", ".", ".."}:
            raise ValueError("filename must be a single basename")
        return value


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
_quarantine_dir = Path("/var/lib/call-rating/quarantine")
_verifier = FfprobeMediaVerifier()


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/verify")
def verify(request: VerificationRequest) -> dict[str, object | None]:
    try:
        target = _resolve_existing_path_within(_quarantine_dir, Path(request.filename), field_name="filename")
    except RecordingIngestionSecurityError as exc:
        raise HTTPException(status_code=400, detail=exc.category) from exc

    result = _verifier.verify(target, timeout_seconds=60)
    return {
        "status": result.status.value,
        "duration_seconds": result.duration_seconds,
        "error_category": result.error_category,
        "error_detail": result.error_detail,
    }
