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

            conn.execute(
                text(
                    "ALTER TABLE employees ADD COLUMN status VARCHAR(50) DEFAULT 'active' NOT NULL"
                )
            )
    except Exception:
        pass
