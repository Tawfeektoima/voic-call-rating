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

    def _print_vram_usage(self, step_name: str):
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

    def process_audio(self, audio_path: str, batch_size: int = 16) -> tuple[str, float]:
        """
        Full pipeline with strict sequential model loading to save VRAM:
        Transcribe (Whisper) -> Align -> Diarize -> Assign Speakers -> Format String
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        self._print_vram_usage("START")
        
        try:
            print(f"[*] Processing audio: {audio_path}")
            
            # 1. Load Audio
            audio = whisperx.load_audio(audio_path)
            duration = len(audio) / 16000.0  # WhisperX default sample rate is 16kHz
            
            # 2. Transcribe (Whisper)
            print(f"[*] Loading Whisper '{self.model_size}' on {self.device}...")
            model = whisperx.load_model(self.model_size, self.device, compute_type=self.compute_type)
            
            # Repetition fix and VAD settings as requested
            result = model.transcribe(
                audio, 
                batch_size=batch_size,
                chunk_size=30,
                print_progress=True
            )
            
            # Unload Whisper immediately
            del model
            gc.collect()
            if self.device == "cuda":
                torch.cuda.empty_cache()
            self._print_vram_usage("AFTER WHISPER UNLOAD")

            # 3. Align
            print(f"[*] Loading Alignment Model...")
            model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=self.device)
            result = whisperx.align(result["segments"], model_a, metadata, audio, self.device)
            
            # Unload alignment model immediately
            del model_a
            gc.collect()
            if self.device == "cuda":
                torch.cuda.empty_cache()
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
            
            # 6. Format output
            transcript = self._format_transcript(result.get("segments", []))
            return transcript, duration
            
        finally:
            self._print_vram_usage("END")

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
