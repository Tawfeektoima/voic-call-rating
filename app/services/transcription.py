import os
import gc
import subprocess
import warnings

warnings.filterwarnings("ignore", message="torchcodec is not installed correctly")
warnings.filterwarnings("ignore", module="torchcodec")
warnings.filterwarnings("ignore", category=UserWarning, module=r"pyannote\.audio\.core\.io")
try:
    import torch
    import whisperx
    from whisperx.diarize import DiarizationPipeline
    WHISPER_AVAILABLE = True
except Exception as e:
    print(f"[!] Warning: WhisperX/Torch failed to load: {e}")
    WHISPER_AVAILABLE = False
from typing import List, Dict, Any

from app.config import get_settings

settings = get_settings()

class CallTranscriber:
    """
    Handles local Speech-to-Text (ASR) and Speaker Diarization using WhisperX.
    Ensures VRAM availability before loading models.
    """

    def __init__(self, device: str = None):
        self.hf_token = settings.HF_TOKEN
        self.model_size = "small" # Using small as requested
        
        if not self.hf_token:
            print("[!] Warning: HF_TOKEN is missing. Diarization may fail.")
            
        # Auto-detect device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
            
        self.compute_type = "float16" if self.device == "cuda" else "int8"
        
        # Check for FFmpeg accessibility (Task 62-C)
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            print("[*] FFmpeg is accessible in the system PATH.")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("[!] CRITICAL WARNING: FFmpeg not found in PATH. Audio decoding via torchcodec/whisperx will be slow or fail.")

    def _print_vram_usage(self, step_name: str):
        if not WHISPER_AVAILABLE or self.device != "cuda":
            return
        if self.device == "cuda":
            import torch
            allocated = torch.cuda.memory_allocated() / (1024**3)
            reserved = torch.cuda.memory_reserved() / (1024**3)
            free_mem, total_mem = torch.cuda.mem_get_info()
            total_gb = total_mem / (1024**3)
            free_gb = free_mem / (1024**3)
            used_gb = total_gb - free_gb

            print(f"\n📊 --- [VRAM Monitor: {step_name}] ---")
            print(f"   ➤ PyTorch Allocated: {allocated:.2f} GB")
            print(f"   ➤ PyTorch Reserved : {reserved:.2f} GB")
            print(f"   ➤ Total GPU Used   : {used_gb:.2f} GB / {total_gb:.2f} GB")
            print(f"   ➤ Available VRAM   : {free_gb:.2f} GB")
            print("-" * 40)

    def _get_safe_batch_size(self) -> int:
        if self.device != "cuda":
            return 4
        try:
            free_mem, _ = torch.cuda.mem_get_info()
            free_gb = free_mem / (1024**3)
            if free_gb > 8.0:
                return 16
            elif free_gb > 5.0:
                return 8
            else:
                return 4
        except Exception as e:
            print(f"[!] Error getting VRAM info: {e}. Defaulting to batch_size 4.")
            return 4

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
        
        try:
            actual_batch_size = batch_size if batch_size is not None else self._get_safe_batch_size()
            print(f"[*] Processing audio: {audio_path} (Batch Size: {actual_batch_size})")
            
            # 1. Load Audio
            audio = whisperx.load_audio(audio_path)
            duration = len(audio) / 16000.0  # WhisperX default sample rate is 16kHz
            
            # 2. Transcribe (Whisper)
            print(f"[*] Loading Whisper '{self.model_size}' on {self.device}...")
            model = whisperx.load_model(self.model_size, self.device, compute_type=self.compute_type)
            
            # Repetition fix and VAD settings as requested
            result = model.transcribe(
                audio,
                batch_size=actual_batch_size,
                language="en",
                print_progress=True,
            )
            result["segments"] = self.filter_hallucinations(result.get("segments", []))
            
            # Unload Whisper immediately
            del model
            gc.collect()
            if self.device == "cuda":
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
            self._print_vram_usage("AFTER WHISPER UNLOAD")

            # 3. Align
            print(f"[*] Loading Alignment Model...")
            model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=self.device)
            result = whisperx.align(
                result["segments"],
                model_a,
                metadata,
                audio,
                self.device,
                return_char_alignments=False,  # أسرع
            )
            
            # Unload alignment model immediately
            del model_a
            gc.collect()
            if self.device == "cuda":
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
            self._print_vram_usage("AFTER ALIGN UNLOAD")

            # 4. Diarize
            if self.hf_token:
                print(f"[*] Loading Diarization Pipeline...")
                diarize_model = DiarizationPipeline(token=self.hf_token, device=self.device)
                diarize_segments = diarize_model(audio)
                
                # 5. Assign speakers
                result = whisperx.assign_word_speakers(diarize_segments, result)
                
                # Unload Diarization immediately
                del diarize_model
                gc.collect()
                if self.device == "cuda":
                    torch.cuda.empty_cache()
                self._print_vram_usage("AFTER DIARIZATION UNLOAD")
            
            # 6. Return raw segments for enrichment
            return result.get("segments", []), duration
            
        finally:
            self._print_vram_usage("END")

    def filter_hallucinations(self, segments: list) -> list:
        """
        Enhanced hallucination filter for whisper-small:
        1. Remove repeated consecutive segments (existing)
        2. Remove very short segments < 0.3s (existing)
        3. Remove known hallucination phrases specific to silence/hold music
        4. Flag segments with suspiciously low word count vs duration
        """
        if not segments:
            return segments

        # Known whisper-small hallucination phrases during silence
        HALLUCINATION_PHRASES = {
            "thank you for watching",
            "thank you for listening",
            "please subscribe",
            "thanks for watching",
            "www.",
            "subtitles by",
            "transcribed by",
            "i'm going to",          # very common false positive in silence
            "uh huh uh huh uh huh",
        }

        filtered = []
        repeat_count = 0
        last_text = ""

        for seg in segments:
            current_text = seg.get("text", "").strip()
            seg_duration = seg.get("end", 0) - seg.get("start", 0)
            text_lower = current_text.lower()

            # 1. Skip very short noise artifacts
            if seg_duration < 0.3:
                continue

            # 2. Skip known hallucination phrases
            if any(phrase in text_lower for phrase in HALLUCINATION_PHRASES):
                print(f"[Hallucination Filter] Removed known phrase: '{current_text}'")
                continue

            # 3. Skip repeated consecutive segments (max 1 repetition allowed)
            if current_text.lower() == last_text:
                repeat_count += 1
                if repeat_count >= 2:
                    continue
            else:
                repeat_count = 0
                last_text = current_text.lower()

            # 4. Flag suspiciously sparse segments
            # (very long duration but very few words = likely silence hallucination)
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
            output.append({
                "id": str(i),
                "start": segment.get("start", 0.0),
                "end": segment.get("end", 0.0),
                "speaker": segment.get("speaker", "UNKNOWN"),
                "text": segment.get("text", "").strip(),
                "emotion": "calm"
            })
        return output

# Singleton instance for the app to reuse
transcriber = CallTranscriber()
