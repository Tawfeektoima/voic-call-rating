from __future__ import annotations

import random

from app.models import InterviewQuestionSource
from app.services.interview_documents import generate_cv_questions


def build_hybrid_interview_questions(
    base_questions: list[str] | None,
    cv_text: str = "",
    *,
    manual_questions: list[str] | None = None,
    standard_count: int = 3,
    cv_count: int = 2,
) -> list[tuple[str, InterviewQuestionSource]]:
    source = InterviewQuestionSource.HR_MANUAL if manual_questions is not None else InterviewQuestionSource.BASE
    normalized_base = [
        str(question).strip()
        for question in (manual_questions if manual_questions is not None else base_questions or [])
        if str(question).strip()
    ]

    if manual_questions is not None:
        selected_base = normalized_base
    elif len(normalized_base) <= standard_count:
        selected_base = normalized_base
    else:
        selected_base = random.sample(normalized_base, standard_count)

    combined: list[tuple[str, InterviewQuestionSource]] = [(question, source) for question in selected_base]
    seen = {question.lower() for question in selected_base}

    for question in generate_cv_questions(cv_text or "", max_questions=cv_count):
        normalized = question.strip()
        if normalized and normalized.lower() not in seen:
            combined.append((normalized, InterviewQuestionSource.CV_AI))
            seen.add(normalized.lower())

    return combined
