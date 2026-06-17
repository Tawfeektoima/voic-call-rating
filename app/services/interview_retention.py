from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import InterviewCandidate, InterviewCandidateStatus


@dataclass
class InterviewRetentionPurgeSummary:
    archived_candidates_matched: int = 0
    candidates_deleted: int = 0
    document_rows_deleted: int = 0
    answer_audio_files_deleted: int = 0
    document_files_deleted: int = 0
    dry_run: bool = True


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _safe_remove_file(path_value: str | None, uploads_root: str) -> bool:
    if not path_value:
        return False

    try:
        uploads_root_abs = os.path.abspath(uploads_root)
        candidate_path_abs = os.path.abspath(path_value)
        if os.path.commonpath([uploads_root_abs, candidate_path_abs]) != uploads_root_abs:
            return False
        if not os.path.isfile(candidate_path_abs):
            return False
        os.remove(candidate_path_abs)
        return True
    except Exception:
        return False


def purge_archived_interview_candidates(
    db: Session,
    *,
    older_than_days: int,
    dry_run: bool = True,
) -> InterviewRetentionPurgeSummary:
    settings = get_settings()
    cutoff = _utcnow() - timedelta(days=max(1, older_than_days))
    candidates = (
        db.query(InterviewCandidate)
        .filter(
            InterviewCandidate.status == InterviewCandidateStatus.ARCHIVED,
            InterviewCandidate.archived_at.isnot(None),
            InterviewCandidate.archived_at <= cutoff,
        )
        .all()
    )

    summary = InterviewRetentionPurgeSummary(
        archived_candidates_matched=len(candidates),
        dry_run=dry_run,
    )

    for candidate in candidates:
        summary.document_rows_deleted += len(candidate.documents)
        if dry_run:
            summary.document_files_deleted += sum(1 for document in candidate.documents if document.storage_path and os.path.isfile(document.storage_path))
            summary.answer_audio_files_deleted += sum(1 for answer in candidate.answers if answer.audio_file_path and os.path.isfile(answer.audio_file_path))
            continue

        for document in candidate.documents:
            if _safe_remove_file(document.storage_path, settings.UPLOAD_DIR):
                summary.document_files_deleted += 1

        for answer in candidate.answers:
            if _safe_remove_file(answer.audio_file_path, settings.UPLOAD_DIR):
                summary.answer_audio_files_deleted += 1

        db.delete(candidate)
        summary.candidates_deleted += 1

    if not dry_run:
        db.flush()

    return summary
