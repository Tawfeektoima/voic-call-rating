import os
import whisperx
from whisperx.diarize import DiarizationPipeline
import torch
import gc
import gradio as gr
from typing import List, Dict, Any

class CallTranscriber:
    """
    A class to handle Speech-to-Text (ASR) and Diarization for voice calls.
    Uses ONLY the local Whisper Small model.
    """
    
    def __init__(self, hf_token: str, device: str = None):
        self.hf_token = hf_token
        self.model_size = "small" # Explicitly set to small
        
        # Auto-detect device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
            
        self.compute_type = "float16" if self.device == "cuda" else "int8"
        
        print(f"[*] Initializing Whisper Small on {self.device}...")
        
        # Load local model
        # WhisperX will find 'small' in C:\Users\Dell\.cache\huggingface\hub\ if it exists
        self.model = whisperx.load_model(self.model_size, self.device, compute_type=self.compute_type)
        
        # Initialize Diarization pipeline
        self.diarize_model = DiarizationPipeline(token=self.hf_token, device=self.device)

    def transcribe_and_diarize(self, audio_path: str, batch_size: int = 16) -> List[Dict[str, Any]]:
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        print(f"[*] Processing audio: {audio_path}")
        audio = whisperx.load_audio(audio_path)
        
        # 1. Transcribe
        result = self.model.transcribe(audio, batch_size=batch_size)
        
        # 2. Align
        model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=self.device)
        result = whisperx.align(result["segments"], model_a, metadata, audio, self.device, return_char_align=False)
        
        # Cleanup
        del model_a
        gc.collect()
        if self.device == "cuda":
            torch.cuda.empty_cache()

        # 3. Diarize
        diarize_segments = self.diarize_model(audio)
        
        # 4. Assign speakers
        result = whisperx.assign_word_speakers(diarize_segments, result)
        
        return result["segments"]

    def format_transcript(self, segments: List[Dict[str, Any]]) -> str:
        output = []
        for segment in segments:
            speaker = segment.get("speaker", "UNKNOWN")
            start = segment["start"]
            end = segment["end"]
            text = segment["text"].strip()
            output.append(f"[{start:05.2f} - {end:05.2f}] {speaker}: {text}")
        return "\n".join(output)

def process_audio(audio_path):
    if not audio_path:
        return "No audio file provided."
    try:
        segments = transcriber.transcribe_and_diarize(audio_path)
        return transcriber.format_transcript(segments)
    except Exception as e:
        return f"Error: {str(e)}"

def launch_ui():
    with gr.Blocks(title="Whisper Small Transcriber") as demo:
        gr.Markdown("# 🎙️ Whisper Small Transcriber (Local)")
        gr.Markdown("Upload audio to get a speaker-labeled transcript using your local **Small** model.")
        
        audio_input = gr.Audio(type="filepath", label="Upload Recording")
        analyze_btn = gr.Button("🚀 Transcribe", variant="primary")
        transcript_output = gr.Textbox(label="Transcript", lines=20)
        
        analyze_btn.click(fn=process_audio, inputs=audio_input, outputs=transcript_output)
        
    demo.launch(share=True)

if __name__ == "__main__":
    HF_TOKEN = "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"
    
    print("[*] Starting UI... please wait.")
    try:
        transcriber = CallTranscriber(hf_token=HF_TOKEN)
        launch_ui()
    except Exception as e:
        print(f"[!] Error: {e}")
