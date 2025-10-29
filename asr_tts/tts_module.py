# tts_module.py
from TTS.api import TTS
import os

AUDIO_OUTPUT_PATH = "outputs/reply.wav"
TTS_MODEL_NAME = "tts_models/en/ljspeech/tacotron2-DDC"

os.makedirs("outputs", exist_ok=True)

class TTSModel:
    def __init__(self, model_name=TTS_MODEL_NAME):
        print(f"Loading TTS model: {model_name}")
        self.tts = TTS(model_name=model_name, progress_bar=False, gpu=False)

    def synthesize(self, text, path=AUDIO_OUTPUT_PATH):
        print("Generating speech...")
        self.tts.tts_to_file(text=text, file_path=path)
        print(f"Audio saved to {path}")
        return path
