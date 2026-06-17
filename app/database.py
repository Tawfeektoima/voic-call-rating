"""
SQLAlchemy engine, session factory, and Base class.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import get_settings

settings = get_settings()

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a DB session and ensures it is closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if settings.ENVIRONMENT.lower() != "production":
    # Development-only compatibility shim. Production must rely on Alembic.
    try:
        with engine.begin() as conn:
            from sqlalchemy import text

            def _column_exists(table_name: str, column_name: str) -> bool:
                rows = conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
                return any(row[1] == column_name for row in rows)

            if not _column_exists("employees", "status"):
                conn.execute(
                    text(
                        "ALTER TABLE employees ADD COLUMN status VARCHAR(50) DEFAULT 'active' NOT NULL"
                    )
                )
            if not _column_exists("interview_candidates", "date_of_birth_encrypted"):
                conn.execute(
                    text(
                        "ALTER TABLE interview_candidates ADD COLUMN date_of_birth_encrypted TEXT"
                    )
                )
            if not _column_exists("interview_candidates", "address_encrypted"):
                conn.execute(
                    text(
                        "ALTER TABLE interview_candidates ADD COLUMN address_encrypted TEXT"
                    )
                )
    except Exception:
        pass
