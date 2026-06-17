from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import InterviewCandidateDocument
from app.services.interview_file_crypto import encrypt_file_in_place, encrypt_text_value, is_text_encrypted


@dataclass
class InterviewSecurityBackfillSummary:
    scanned_documents: int = 0
    encrypted_files: int = 0
    encrypted_text_rows: int = 0
    missing_files: int = 0
    failed_files: int = 0


def backfill_interview_document_security(db: Session) -> InterviewSecurityBackfillSummary:
    summary = InterviewSecurityBackfillSummary()
    documents = db.query(InterviewCandidateDocument).all()

    for document in documents:
        summary.scanned_documents += 1

        if document.storage_path:
            file_path = Path(document.storage_path)
            if not document.is_encrypted:
                if file_path.is_file():
                    try:
                        encrypt_file_in_place(document.storage_path)
                        document.is_encrypted = True
                        summary.encrypted_files += 1
                    except Exception:
                        summary.failed_files += 1
                else:
                    summary.missing_files += 1

        if document.extracted_text and not is_text_encrypted(document.extracted_text):
            document.extracted_text = encrypt_text_value(document.extracted_text)
            summary.encrypted_text_rows += 1

    return summary
