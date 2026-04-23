import os
import gc
import torch
import whisperx
from whisperx.diarize import DiarizationPipeline
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
        self._check_vram()
        
        self.model = None
        self.diarize_model = None

    def _check_vram(self):
        """Checks if there's enough VRAM before starting."""
        if self.device == "cuda":
            free_mem, total_mem = torch.cuda.mem_get_info()
            free_mem_gb = free_mem / (1024 ** 3)
            print(f"[*] CUDA free VRAM: {free_mem_gb:.2f} GB")
            if free_mem_gb < 2.0:
                print("[!] Warning: Low VRAM detected. Processing might fail.")

    def _load_models(self):
        """Lazy load models to save memory when not actively processing."""
        if self.model is None:
            print(f"[*] Loading Whisper '{self.model_size}' on {self.device}...")
            self.model = whisperx.load_model(self.model_size, self.device, compute_type=self.compute_type)
        
        if self.diarize_model is None and self.hf_token:
            print(f"[*] Loading Diarization Pipeline...")
            self.diarize_model = DiarizationPipeline(token=self.hf_token, device=self.device)

    def _unload_models(self):
        """Unload models to free up VRAM after processing."""
        del self.model
        del self.diarize_model
        self.model = None
        self.diarize_model = None
        gc.collect()
        if self.device == "cuda":
            torch.cuda.empty_cache()
            
    def process_audio(self, audio_path: str, batch_size: int = 16) -> tuple[str, float]:
        """
        Full pipeline: Transcribe -> Align -> Diarize -> Assign Speakers -> Format String
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        try:
            self._load_models()
            print(f"[*] Processing audio: {audio_path}")
            
            # 1. Load Audio
            audio = whisperx.load_audio(audio_path)
            duration = len(audio) / 16000.0  # WhisperX default sample rate is 16kHz
            
            # 2. Transcribe
            result = self.model.transcribe(audio, batch_size=batch_size)
            
            # 3. Align
            model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=self.device)
            result = whisperx.align(result["segments"], model_a, metadata, audio, self.device)
            
            # Cleanup alignment model immediately
            del model_a
            gc.collect()
            if self.device == "cuda":
                torch.cuda.empty_cache()

            # 4. Diarize
            if self.diarize_model:
                diarize_segments = self.diarize_model(audio)
                # 5. Assign speakers
                result = whisperx.assign_word_speakers(diarize_segments, result)
            
            # 6. Format output
            transcript = self._format_transcript(result.get("segments", []))
            return transcript, duration
            
        finally:
            self._unload_models()

    def _format_transcript(self, segments: List[Dict[str, Any]]) -> str:
        output = []
        for segment in segments:
            speaker = segment.get("speaker", "UNKNOWN")
            start = segment.get("start", 0.0)
            end = segment.get("end", 0.0)
            text = segment.get("text", "").strip()
            output.append(f"[{start:05.2f} - {end:05.2f}] {speaker}: {text}")
        return "\n".join(output)

# Singleton instance for the app to reuse
transcriber = CallTranscriber()
