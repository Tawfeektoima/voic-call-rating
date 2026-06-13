from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.transcription import CallTranscriber


def test_transcriber_uses_batch_one_on_4gb_gpu():
    with patch("app.services.transcription.torch.cuda.is_available", return_value=True), \
        patch("app.services.transcription.torch.cuda.mem_get_info", return_value=(3 * 1024**3, 4 * 1024**3)), \
        patch("app.services.transcription.subprocess.run"):
        transcriber = CallTranscriber(device="cuda")

    assert transcriber._get_safe_batch_size() == 1


def test_transcriber_uses_batch_one_when_free_vram_is_low():
    with patch("app.services.transcription.torch.cuda.is_available", return_value=True), \
        patch("app.services.transcription.torch.cuda.mem_get_info", return_value=(3 * 1024**3, 8 * 1024**3)), \
        patch("app.services.transcription.subprocess.run"):
        transcriber = CallTranscriber(device="cuda")

    assert transcriber._get_safe_batch_size() == 1


def test_transcriber_stays_gpu_only_after_cuda_failure_and_cleans_cache():
    audio_path = Path("test_uploads") / "gpu-only-oom.wav"
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    audio_path.write_bytes(b"fake-audio")

    fake_model_cuda = MagicMock()
    fake_model_cuda.transcribe.side_effect = RuntimeError("CUDA failed with error out of memory")
    load_model_calls = []

    def fake_load_model(model_size, device, compute_type):
        load_model_calls.append((model_size, device, compute_type))
        return fake_model_cuda

    with patch("app.services.transcription.torch.cuda.is_available", return_value=True), \
        patch("app.services.transcription.torch.cuda.mem_get_info", return_value=(3 * 1024**3, 4 * 1024**3)), \
        patch("app.services.transcription.torch.cuda.memory_allocated", return_value=0), \
        patch("app.services.transcription.torch.cuda.memory_reserved", return_value=0), \
        patch("app.services.transcription.subprocess.run"), \
        patch("app.services.transcription.whisperx.load_audio", return_value=[0] * 16000), \
        patch("app.services.transcription.whisperx.load_model", side_effect=fake_load_model), \
        patch("app.services.transcription.gc.collect") as mock_collect, \
        patch("app.services.transcription.torch.cuda.empty_cache") as mock_empty_cache, \
        patch("app.services.transcription.torch.cuda.ipc_collect") as mock_ipc_collect:
        transcriber = CallTranscriber(device="cuda")
        transcriber.hf_token = ""

        with pytest.raises(RuntimeError, match="out of memory"):
            transcriber.process_audio(str(audio_path))

    assert load_model_calls == [("small", "cuda", "float16")]
    assert mock_collect.called
    assert mock_empty_cache.called
    assert mock_ipc_collect.called


def test_transcriber_sets_pyannote_vad_batch_size():
    segmentation = MagicMock()
    segmentation.batch_size = 32
    fake_model = MagicMock()
    fake_model.vad_model.vad_pipeline._segmentation = segmentation

    with patch("app.services.transcription.subprocess.run"):
        transcriber = CallTranscriber(device="cuda")

    transcriber._set_vad_batch_size(fake_model, 1)

    assert segmentation.batch_size == 1
