"""add interview module core tables

Revision ID: f13d9c4b7a21
Revises: e92c3d4e5f60
Create Date: 2026-06-14 23:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f13d9c4b7a21"
down_revision: Union[str, Sequence[str], None] = "e92c3d4e5f60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


interview_job_status_enum = sa.Enum(
    "draft",
    "open",
    "paused",
    "closed",
    name="interviewjobstatus",
)
interview_candidate_status_enum = sa.Enum(
    "applied",
    "screening",
    "interviewing",
    "evaluated",
    "accepted",
    "rejected",
    "archived",
    name="interviewcandidatestatus",
)
interview_session_status_enum = sa.Enum(
    "invited",
    "in_progress",
    "completed",
    "expired",
    "cancelled",
    name="interviewsessionstatus",
)
interview_question_source_enum = sa.Enum(
    "base",
    "cv_ai",
    "hr_manual",
    name="interviewquestionsource",
)
interview_answer_status_enum = sa.Enum(
    "pending",
    "processing",
    "evaluated",
    "failed",
    name="interviewanswerstatus",
)


def _create_enums(bind) -> None:
    for enum_type in (
        interview_job_status_enum,
        interview_candidate_status_enum,
        interview_session_status_enum,
        interview_question_source_enum,
        interview_answer_status_enum,
    ):
        enum_type.create(bind, checkfirst=True)


def _drop_enums(bind) -> None:
    for enum_type in (
        interview_answer_status_enum,
        interview_question_source_enum,
        interview_session_status_enum,
        interview_candidate_status_enum,
        interview_job_status_enum,
    ):
        enum_type.drop(bind, checkfirst=True)


def upgrade() -> None:
    bind = op.get_bind()
    _create_enums(bind)

    op.create_table(
        "interview_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("department", sa.String(length=255), nullable=True),
        sa.Column("team_id", sa.Integer(), nullable=True),
        sa.Column("campaign_id", sa.Integer(), nullable=True),
        sa.Column("status", interview_job_status_enum, nullable=False, server_default="draft"),
        sa.Column("base_questions", sa.JSON(), nullable=True),
        sa.Column("scoring_weights", sa.JSON(), nullable=True),
        sa.Column("mcq_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("mcq_questions", sa.JSON(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column("updated_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.ForeignKeyConstraint(["updated_by_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_interview_jobs_status", "interview_jobs", ["status"], unique=False)
    op.create_index("ix_interview_jobs_team_id", "interview_jobs", ["team_id"], unique=False)
    op.create_index("ix_interview_jobs_campaign_id", "interview_jobs", ["campaign_id"], unique=False)
    op.create_index("ix_interview_jobs_created_by_id", "interview_jobs", ["created_by_id"], unique=False)
    op.create_index("ix_interview_jobs_title", "interview_jobs", ["title"], unique=False)

    op.create_table(
        "interview_candidates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("contact_email", sa.String(length=255), nullable=False),
        sa.Column("contact_email_normalized", sa.String(length=255), nullable=False),
        sa.Column("phone_number", sa.String(length=50), nullable=True),
        sa.Column("phone_normalized", sa.String(length=50), nullable=True),
        sa.Column("national_id_hash", sa.String(length=128), nullable=True),
        sa.Column("national_id_last4", sa.String(length=4), nullable=True),
        sa.Column("status", interview_candidate_status_enum, nullable=False, server_default="applied"),
        sa.Column("final_score", sa.Float(), nullable=True),
        sa.Column("global_percentile", sa.Float(), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("converted_employee_id", sa.Integer(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["converted_employee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["interview_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "contact_email_normalized", name="uq_interview_candidates_job_email_normalized"),
        sa.UniqueConstraint("converted_employee_id", name="uq_interview_candidates_converted_employee_id"),
    )
    op.create_index("ix_interview_candidates_status", "interview_candidates", ["status"], unique=False)
    op.create_index("ix_interview_candidates_job_status", "interview_candidates", ["job_id", "status"], unique=False)
    op.create_index("ix_interview_candidates_national_id_hash", "interview_candidates", ["national_id_hash"], unique=False)
    op.create_index("ix_interview_candidates_converted_employee_id", "interview_candidates", ["converted_employee_id"], unique=False)
    op.create_index("ix_interview_candidates_contact_email_normalized", "interview_candidates", ["contact_email_normalized"], unique=False)
    op.create_index("ix_interview_candidates_phone_normalized", "interview_candidates", ["phone_normalized"], unique=False)
    op.create_index("ix_interview_candidates_full_name", "interview_candidates", ["full_name"], unique=False)
    op.create_index("ix_interview_candidates_applied_at", "interview_candidates", ["applied_at"], unique=False)

    op.create_table(
        "interview_candidate_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("candidate_id", sa.Integer(), nullable=False),
        sa.Column("document_type", sa.String(length=50), nullable=False, server_default="cv"),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("extraction_status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("extraction_error", sa.Text(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["interview_candidates.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_interview_candidate_documents_candidate_id", "interview_candidate_documents", ["candidate_id"], unique=False)
    op.create_index("ix_interview_candidate_documents_extraction_status", "interview_candidate_documents", ["extraction_status"], unique=False)

    op.create_table(
        "interview_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("candidate_id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("session_token_hash", sa.String(length=128), nullable=False),
        sa.Column("status", interview_session_status_enum, nullable=False, server_default="invited"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("question_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["interview_candidates.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["interview_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_token_hash", name="uq_interview_sessions_session_token_hash"),
    )
    op.create_index("ix_interview_sessions_candidate_id", "interview_sessions", ["candidate_id"], unique=False)
    op.create_index("ix_interview_sessions_job_id", "interview_sessions", ["job_id"], unique=False)
    op.create_index("ix_interview_sessions_status", "interview_sessions", ["status"], unique=False)
    op.create_index("ix_interview_sessions_expires_at", "interview_sessions", ["expires_at"], unique=False)
    op.create_index("ix_interview_sessions_session_token_hash", "interview_sessions", ["session_token_hash"], unique=False)

    op.create_table(
        "interview_questions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=True),
        sa.Column("candidate_id", sa.Integer(), nullable=True),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("expected_skills_tags", sa.JSON(), nullable=True),
        sa.Column("source", interview_question_source_enum, nullable=False, server_default="base"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["interview_candidates.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["interview_jobs.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["interview_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_interview_questions_job_id", "interview_questions", ["job_id"], unique=False)
    op.create_index("ix_interview_questions_session_id", "interview_questions", ["session_id"], unique=False)
    op.create_index("ix_interview_questions_candidate_id", "interview_questions", ["candidate_id"], unique=False)

    op.create_table(
        "interview_answers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("candidate_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("audio_file_path", sa.String(length=500), nullable=True),
        sa.Column("transcribed_text", sa.Text(), nullable=True),
        sa.Column("relevance_score", sa.Float(), nullable=True),
        sa.Column("fluency_score", sa.Float(), nullable=True),
        sa.Column("grammar_score", sa.Float(), nullable=True),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("status", interview_answer_status_enum, nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["candidate_id"], ["interview_candidates.id"]),
        sa.ForeignKeyConstraint(["question_id"], ["interview_questions.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["interview_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "question_id", name="uq_interview_answers_session_question"),
    )
    op.create_index("ix_interview_answers_session_id", "interview_answers", ["session_id"], unique=False)
    op.create_index("ix_interview_answers_candidate_id", "interview_answers", ["candidate_id"], unique=False)
    op.create_index("ix_interview_answers_status", "interview_answers", ["status"], unique=False)
    op.create_index("ix_interview_answers_question_id", "interview_answers", ["question_id"], unique=False)

    op.create_table(
        "interview_workflow_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("candidate_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("from_status", sa.String(length=50), nullable=True),
        sa.Column("to_status", sa.String(length=50), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("event_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["candidate_id"], ["interview_candidates.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_interview_workflow_events_candidate_id", "interview_workflow_events", ["candidate_id"], unique=False)
    op.create_index("ix_interview_workflow_events_actor_id", "interview_workflow_events", ["actor_id"], unique=False)
    op.create_index("ix_interview_workflow_events_event_type", "interview_workflow_events", ["event_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_interview_workflow_events_event_type", table_name="interview_workflow_events")
    op.drop_index("ix_interview_workflow_events_actor_id", table_name="interview_workflow_events")
    op.drop_index("ix_interview_workflow_events_candidate_id", table_name="interview_workflow_events")
    op.drop_table("interview_workflow_events")

    op.drop_index("ix_interview_answers_question_id", table_name="interview_answers")
    op.drop_index("ix_interview_answers_status", table_name="interview_answers")
    op.drop_index("ix_interview_answers_candidate_id", table_name="interview_answers")
    op.drop_index("ix_interview_answers_session_id", table_name="interview_answers")
    op.drop_table("interview_answers")

    op.drop_index("ix_interview_questions_candidate_id", table_name="interview_questions")
    op.drop_index("ix_interview_questions_session_id", table_name="interview_questions")
    op.drop_index("ix_interview_questions_job_id", table_name="interview_questions")
    op.drop_table("interview_questions")

    op.drop_index("ix_interview_sessions_session_token_hash", table_name="interview_sessions")
    op.drop_index("ix_interview_sessions_expires_at", table_name="interview_sessions")
    op.drop_index("ix_interview_sessions_status", table_name="interview_sessions")
    op.drop_index("ix_interview_sessions_job_id", table_name="interview_sessions")
    op.drop_index("ix_interview_sessions_candidate_id", table_name="interview_sessions")
    op.drop_table("interview_sessions")

    op.drop_index("ix_interview_candidate_documents_extraction_status", table_name="interview_candidate_documents")
    op.drop_index("ix_interview_candidate_documents_candidate_id", table_name="interview_candidate_documents")
    op.drop_table("interview_candidate_documents")

    op.drop_index("ix_interview_candidates_applied_at", table_name="interview_candidates")
    op.drop_index("ix_interview_candidates_full_name", table_name="interview_candidates")
    op.drop_index("ix_interview_candidates_phone_normalized", table_name="interview_candidates")
    op.drop_index("ix_interview_candidates_contact_email_normalized", table_name="interview_candidates")
    op.drop_index("ix_interview_candidates_converted_employee_id", table_name="interview_candidates")
    op.drop_index("ix_interview_candidates_national_id_hash", table_name="interview_candidates")
    op.drop_index("ix_interview_candidates_job_status", table_name="interview_candidates")
    op.drop_index("ix_interview_candidates_status", table_name="interview_candidates")
    op.drop_table("interview_candidates")

    op.drop_index("ix_interview_jobs_title", table_name="interview_jobs")
    op.drop_index("ix_interview_jobs_created_by_id", table_name="interview_jobs")
    op.drop_index("ix_interview_jobs_campaign_id", table_name="interview_jobs")
    op.drop_index("ix_interview_jobs_team_id", table_name="interview_jobs")
    op.drop_index("ix_interview_jobs_status", table_name="interview_jobs")
    op.drop_table("interview_jobs")

    bind = op.get_bind()
    _drop_enums(bind)
