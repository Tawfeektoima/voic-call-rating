"""
conftest.py — pytest session-scoped ML dependency stubs and isolated database setup.

1. Heavy ML/native packages (librosa, transformers, torch, chromadb, etc.) are
   not installed in the test environment. We inject lightweight MagicMock stubs
   into sys.modules *before* any test module is imported so that the app import
   chain succeeds.
2. We isolate the test database environment entirely in-memory using an SQLite 
   database with StaticPool. This ensures no test reads/writes to call_rating.db
   and cleanup is deterministic.
3. We redirect audio uploads to a temporary directory 'test_uploads' and clean it.
"""
import os
import sys
import shutil
import pytest
from unittest.mock import MagicMock

# ============================================================================
# 1. External ML/Heavy library stubs
# ============================================================================
_EXTERNAL_STUBS = [
    # Audio / speech
    "librosa", "librosa.feature", "librosa.effects",
    "whisperx", "whisperx.diarize",
    "torchaudio", "torchaudio.transforms",
    # Deep-learning framework
    "torch", "torch.nn", "torch.cuda",
    # NLP / embeddings
    "transformers",
    "sentence_transformers",
    # Vector DB
    "chromadb",
]

for _mod_name in _EXTERNAL_STUBS:
    if _mod_name not in sys.modules:
        _mock = MagicMock()
        _mock.__spec__ = None   # prevent importlib.util.find_spec from choking
        _mock.__path__ = []     # make it look like a package to sub-imports
        sys.modules[_mod_name] = _mock

# torch.cuda.is_available() must return False so transcription.py picks CPU
sys.modules["torch"].cuda.is_available.return_value = False


# ============================================================================
# 2. Database and Upload Folder Isolation Settings
# ============================================================================
# Configure DATABASE_URL and UPLOAD_DIR before any app imports
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["UPLOAD_DIR"] = "test_uploads"

from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

# Create in-memory SQLite engine with StaticPool to share connection across calls
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Overwrite database module engine & SessionLocal before any tests or app imports can use them
import app.database
app.database.engine = test_engine
app.database.SessionLocal = TestSessionLocal

# Create all schema tables in-memory
from app.database import Base
import app.models  # ensure models register on Base
Base.metadata.create_all(bind=test_engine)

# Override get_db FastAPI dependency injection
from app.main import app as fastapi_app
def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()
fastapi_app.dependency_overrides[app.database.get_db] = override_get_db


# ============================================================================
# 3. Pytest Fixtures for Cleanup and Teardown
# ============================================================================
@pytest.fixture(autouse=True)
def clean_db_and_uploads():
    """Autouse function-scoped fixture to delete all rows and files between tests."""
    db = TestSessionLocal()
    try:
        db.execute(text("PRAGMA foreign_keys = OFF;"))
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.execute(text("PRAGMA foreign_keys = ON;"))
        db.commit()
    finally:
        db.close()

    # Clean test uploads folder files
    test_uploads_dir = "test_uploads"
    if os.path.exists(test_uploads_dir):
        for filename in os.listdir(test_uploads_dir):
            file_path = os.path.join(test_uploads_dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception:
                pass

@pytest.fixture(scope="session", autouse=True)
def test_uploads_session_cleanup():
    """Session-scoped teardown to remove the temporary upload directory."""
    yield
    test_uploads_dir = "test_uploads"
    if os.path.exists(test_uploads_dir):
        try:
            shutil.rmtree(test_uploads_dir)
        except Exception:
            pass
