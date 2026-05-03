import torch
import librosa
import numpy as np
from transformers import Wav2Vec2FeatureExtractor, Wav2Vec2ForSequenceClassification
import os

class AcousticAnalyzer:
    """
    Service for analyzing speech emotions from audio segments using Wav2Vec 2.0.
    Maps RAVDESS-style emotions to the platform's 'calm', 'stress', 'agitation' states.
    """
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_name = "ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition"
        
        # We now load these lazily to save VRAM at startup
        self.feature_extractor = None
        self.model = None
        self.id2label = {}

        # Mapping from model's labels to app-specific categories
        self.emotion_map = {
            "neutral": "calm",
            "neu": "calm",
            "calm": "calm",
            "happy": "calm",
            "hap": "calm",
            "sad": "stress",
            "disgust": "stress",
            "angry": "agitation",
            "ang": "agitation",
            "fearful": "agitation",
            "surprised": "agitation"
        }

    def _load_model(self):
        """Internal helper to load model lazily."""
        if self.model is not None:
            return

        # Clear cache before loading to ensure space for the acoustic model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        try:
            print(f"[*] Lazy Loading Acoustic Model '{self.model_name}' on {self.device}...")
            self.feature_extractor = Wav2Vec2FeatureExtractor.from_pretrained(self.model_name)
            self.model = Wav2Vec2ForSequenceClassification.from_pretrained(self.model_name, use_safetensors=True).to(self.device)
            self.model.eval()
            self.id2label = self.model.config.id2label
        except Exception as e:
            print(f"Error loading Wav2Vec model: {e}")
            self.id2label = {}

        # Mapping from model's labels to app-specific categories
        self.emotion_map = {
            "neutral": "calm",
            "neu": "calm",
            "calm": "calm",
            "happy": "calm",
            "hap": "calm",
            "sad": "stress",
            "disgust": "stress",
            "angry": "agitation",
            "ang": "agitation",
            "fearful": "agitation",
            "surprised": "agitation"
        }

    def analyze_segments(self, audio_path: str, segments: list) -> list:
        """
        Processes a list of audio segments and returns an emotion timeline.
        """
        if not os.path.exists(audio_path):
            print(f"Audio file not found: {audio_path}")
            return []
            
        # 1. Load model lazily
        self._load_model()
        if self.model is None:
            return []

        # 2. Load audio at 16kHz
        try:
            audio, sr = librosa.load(audio_path, sr=16000)
        except Exception as e:
            print(f"Error loading audio for analysis: {e}")
            return []
        
        emotion_timeline = []
        
        # 3. Process each segment
        with torch.no_grad():
            for segment in segments:
                start_sec = segment.get("start", 0)
                end_sec = segment.get("end", start_sec + 1)
                
                start_sample = int(start_sec * sr)
                end_sample = int(end_sec * sr)
                
                if end_sample <= start_sample or start_sample >= len(audio):
                    continue
                
                segment_data = audio[start_sample:end_sample]
                if len(segment_data) == 0:
                    continue
                segment_data = (segment_data - np.mean(segment_data)) / (np.std(segment_data) + 1e-5)
                
                inputs = self.feature_extractor(
                    segment_data, 
                    sampling_rate=sr, 
                    return_tensors="pt", 
                    padding=True
                ).to(self.device)
                
                logits = self.model(**inputs).logits
                probs = torch.softmax(logits, dim=-1)
                confidence, predicted_id = torch.max(probs, dim=-1)
                
                raw_label = self.id2label.get(predicted_id.item(), "neutral").lower()
                mapped_emotion = self.emotion_map.get(raw_label, "calm")
                intensity = round(confidence.item() * 100, 2)
                
                emotion_timeline.append({
                    "time": round(start_sec, 2),
                    "emotion": mapped_emotion,
                    "intensity": intensity,
                    "speaker": segment.get("speaker", "UNKNOWN")
                })
        
        # 4. Offload model to free VRAM immediately
        print("[*] Offloading Acoustic Model and clearing cache...")
        if self.model is not None:
            self.model.to("cpu")
            del self.model
            del self.feature_extractor
            self.model = None
            self.feature_extractor = None

        import gc
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            
        return emotion_timeline
