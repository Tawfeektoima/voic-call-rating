import gc
import os
import re
import subprocess
import warnings
from typing import Any, Dict, List

warnings.filterwarnings("ignore", message="torchcodec is not installed correctly")
warnings.filterwarnings("ignore", module="torchcodec")
warnings.filterwarnings("ignore", category=UserWarning, module=r"pyannote\.audio\.core\.io")

DIARIZATION_IMPORT_ERROR = None
try:
    import torch
    import whisperx

    WHISPER_AVAILABLE = True
except Exception as e:
    print(f"[!] Warning: WhisperX/Torch failed to load: {e}")
    WHISPER_AVAILABLE = False

if WHISPER_AVAILABLE:
    try:
        from whisperx.diarize import DiarizationPipeline

        DIARIZATION_AVAILABLE = True
    except Exception as e:
        DIARIZATION_IMPORT_ERROR = e
        DIARIZATION_AVAILABLE = False
        print(f"[!] Warning: diarization pipeline unavailable, continuing without speaker diarization: {e}")
else:
    DIARIZATION_AVAILABLE = False

from app.config import get_settings

settings = get_settings()

_CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x1f\x7f]")
_WHITESPACE_PATTERN = re.compile(r"\s+")


def sanitize_untrusted_text(value: Any, fallback: str = "") -> str:
    """
    Normalize transcript and metadata strings so they are treated as inert data.

    This removes control characters and collapses whitespace, but it does not
    attempt semantic interpretation. Downstream code still has to treat the
    returned value as untrusted content.
    """
    if value is None:
        return fallback

    text = str(value).replace("\ufeff", "").replace("\u200b", "")
    text = _CONTROL_CHAR_PATTERN.sub(" ", text)
    text = _WHITESPACE_PATTERN.sub(" ", text).strip()
    return text or fallback


class CallTranscriber:
    """
    Handles local Speech-to-Text (ASR) and Speaker Diarization using WhisperX.
    Ensures VRAM availability before loading models.
    """

    def __init__(self, device: str = None):
        self.hf_token = settings.HF_TOKEN
        self.model_size = "small"

        if not self.hf_token:
            print("[!] Warning: HF_TOKEN is missing. Diarization may fail.")

        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        self.compute_type = "float16" if self.device == "cuda" else "int8"

        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            print("[*] FFmpeg is accessible in the system PATH.")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("[!] CRITICAL WARNING: FFmpeg not found in PATH. Audio decoding via torchcodec/whisperx will be slow or fail.")

    def _print_vram_usage(self, step_name: str):
        if not WHISPER_AVAILABLE or self.device != "cuda":
            return

        allocated = torch.cuda.memory_allocated() / (1024**3)
        reserved = torch.cuda.memory_reserved() / (1024**3)
        free_mem, total_mem = torch.cuda.mem_get_info()
        total_gb = total_mem / (1024**3)
        free_gb = free_mem / (1024**3)
        used_gb = total_gb - free_gb

        print(f"\n[VRAM Monitor: {step_name}]")
        print(f"   PyTorch Allocated: {allocated:.2f} GB")
        print(f"   PyTorch Reserved : {reserved:.2f} GB")
        print(f"   Total GPU Used   : {used_gb:.2f} GB / {total_gb:.2f} GB")
        print(f"   Available VRAM   : {free_gb:.2f} GB")
        print("-" * 40)

    def _get_safe_batch_size(self) -> int:
        if self.device != "cuda":
            return 4
        try:
            free_mem, total_mem = torch.cuda.mem_get_info()
            free_gb = free_mem / (1024**3)
            total_gb = total_mem / (1024**3)
            if total_gb <= 4.5 or free_gb < 3.75:
                return 1
            if free_gb > 8.0:
                return 16
            if free_gb > 5.0:
                return 8
            return 4
        except Exception as e:
            print(f"[!] Error getting VRAM info: {e}. Defaulting to batch_size 1.")
            return 1

    def _clear_device_cache(self):
        gc.collect()
        if WHISPER_AVAILABLE and hasattr(torch, "cuda") and torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()

    def release_resources(self):
        """
        Explicit post-task cleanup hook.
        Whisper models are already short-lived per call, so this mainly forces
        GPU cache release for any leftovers after a task finishes.
        """
        self._clear_device_cache()

    def _set_vad_batch_size(self, model: Any, batch_size: int):
        """
        WhisperX uses a Pyannote VAD model before Whisper inference. Pyannote's
        default inference batch is 32, which is too high for the 4GB local GPU.
        """
        vad_model = getattr(model, "vad_model", None)
        vad_pipeline = getattr(vad_model, "vad_pipeline", None)
        segmentation = getattr(vad_pipeline, "_segmentation", None)

        if segmentation is not None and hasattr(segmentation, "batch_size"):
            current_batch_size = getattr(segmentation, "batch_size", None)
            if current_batch_size != batch_size:
                segmentation.batch_size = batch_size
                print(f"[*] Pyannote VAD batch size set to {batch_size} (was {current_batch_size}).")

    def process_audio(self, audio_path: str, batch_size: int = None) -> tuple[str, float]:
        """
        Full pipeline with strict sequential model loading to save VRAM:
        Transcribe (Whisper) -> Align -> Diarize -> Assign Speakers -> Format String
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        if not WHISPER_AVAILABLE:
            raise RuntimeError("Transcription service is unavailable: WhisperX/Torch not loaded correctly.")

        self._print_vram_usage("START")

        model = None
        model_a = None
        diarize_model = None

        try:
            actual_batch_size = batch_size if batch_size is not None else self._get_safe_batch_size()
            print(f"[*] Processing audio: {audio_path} (Batch Size: {actual_batch_size})")

            audio = whisperx.load_audio(audio_path)
            duration = len(audio) / 16000.0

            print(f"[*] Loading Whisper '{self.model_size}' on {self.device}...")
            model = whisperx.load_model(self.model_size, self.device, compute_type=self.compute_type)
            self._set_vad_batch_size(model, actual_batch_size)
            result = model.transcribe(
                audio,
                batch_size=actual_batch_size,
                language="en",
                print_progress=True,
            )
            result["segments"] = self.filter_hallucinations(result.get("segments", []))

            del model
            model = None
            self._clear_device_cache()
            self._print_vram_usage("AFTER WHISPER UNLOAD")

            print("[*] Loading Alignment Model...")
            model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=self.device)
            result = whisperx.align(
                result["segments"],
                model_a,
                metadata,
                audio,
                self.device,
                return_char_alignments=False,
            )

            del model_a
            model_a = None
            self._clear_device_cache()
            self._print_vram_usage("AFTER ALIGN UNLOAD")

            if self.hf_token and DIARIZATION_AVAILABLE:
                print("[*] Loading Diarization Pipeline...")
                diarize_model = DiarizationPipeline(token=self.hf_token, device=self.device)
                diarize_segments = diarize_model(audio)
                result = whisperx.assign_word_speakers(diarize_segments, result)

                del diarize_model
                diarize_model = None
                self._clear_device_cache()
                self._print_vram_usage("AFTER DIARIZATION UNLOAD")
            elif self.hf_token and not DIARIZATION_AVAILABLE:
                print(f"[!] Skipping diarization because the pipeline is unavailable: {DIARIZATION_IMPORT_ERROR}")

            structured_segments = self._build_structured_transcript(result.get("segments", []))
            return structured_segments, duration
        finally:
            if model is not None:
                del model
            if model_a is not None:
                del model_a
            if diarize_model is not None:
                del diarize_model
            self._clear_device_cache()
            self._print_vram_usage("END")

    def filter_hallucinations(self, segments: list) -> list:
        """
        Enhanced hallucination filter for whisper-small:
        1. Remove repeated consecutive segments.
        2. Remove very short segments < 0.3s.
        3. Remove known hallucination phrases specific to silence/hold music.
        4. Flag segments with suspiciously low word count vs duration.
        """
        if not segments:
            return segments

        hallucination_phrases = {
            "thank you for watching",
            "thank you for listening",
            "please subscribe",
            "thanks for watching",
            "www.",
            "subtitles by",
            "transcribed by",
            "i'm going to",
            "uh huh uh huh uh huh",
        }

        filtered = []
        repeat_count = 0
        last_text = ""

        for seg in segments:
            current_text = sanitize_untrusted_text(seg.get("text", ""))
            seg_duration = seg.get("end", 0) - seg.get("start", 0)
            text_lower = current_text.lower()

            if seg_duration < 0.3:
                continue

            if any(phrase in text_lower for phrase in hallucination_phrases):
                print(f"[Hallucination Filter] Removed known phrase: '{current_text}'")
                continue

            if current_text.lower() == last_text:
                repeat_count += 1
                if repeat_count >= 2:
                    continue
            else:
                repeat_count = 0
                last_text = current_text.lower()

            word_count = len(current_text.split())
            if seg_duration > 5.0 and word_count < 3:
                seg["needs_review"] = True
                seg["hallucination_suspect"] = True

            filtered.append(seg)

        removed = len(segments) - len(filtered)
        if removed > 0:
            print(f"[Hallucination Filter] Removed {removed} repeated/short/known-phrase segments.")
        return filtered

    def _build_structured_transcript(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        output = []
        for i, segment in enumerate(segments):
            output.append(
                {
                    "id": str(i),
                    "start": float(segment.get("start", 0.0) or 0.0),
                    "end": float(segment.get("end", 0.0) or 0.0),
                    "speaker": sanitize_untrusted_text(segment.get("speaker", "UNKNOWN"), fallback="UNKNOWN"),
                    "text": sanitize_untrusted_text(segment.get("text", "")),
                    "emotion": sanitize_untrusted_text(segment.get("emotion", "calm"), fallback="calm"),
                    "needs_review": bool(segment.get("needs_review", False)),
                    "words": segment.get("words", []),
                    "avg_logprob": segment.get("avg_logprob"),
                    "no_speech_prob": segment.get("no_speech_prob"),
                }
            )
        return output


transcriber = CallTranscriber()
