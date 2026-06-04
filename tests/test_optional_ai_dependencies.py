import builtins
import importlib
from unittest.mock import patch


def _blocked_import(names):
    real_import = builtins.__import__

    def _import(name, globals=None, locals=None, fromlist=(), level=0):
        if name.split(".")[0] in names:
            raise ImportError(f"blocked optional dependency: {name}")
        return real_import(name, globals, locals, fromlist, level)

    return _import


def test_acoustic_module_imports_without_optional_dependencies():
    import app.services.acoustic as acoustic_module

    with patch("builtins.__import__", side_effect=_blocked_import({"torch", "librosa", "numpy", "transformers"})):
        reloaded = importlib.reload(acoustic_module)
        analyzer = reloaded.AcousticAnalyzer()
        assert analyzer.analyze_segments("missing.wav", []) == []

    importlib.reload(acoustic_module)


def test_rag_worker_imports_without_optional_dependencies():
    import app.workers.rag_worker as rag_worker_module

    with patch("builtins.__import__", side_effect=_blocked_import({"chromadb", "sentence_transformers", "redis"})):
        reloaded = importlib.reload(rag_worker_module)
        assert reloaded.redis_client is None or reloaded.collection is None

    importlib.reload(rag_worker_module)
