import sounddevice as sd
import soundfile as sf
import whisper
import os

SAMPLE_RATE = 16000
AUDIO_INPUT_PATH = "outputs/input.wav"
WHISPER_MODEL = "base"  # 'tiny' for faster edge inference

os.makedirs("outputs", exist_ok=True)

class ASRModel:
    def __init__(self, model_name=WHISPER_MODEL):
        print(f"Loading Whisper model: {model_name}")
        self.model = whisper.load_model(model_name)

    def record_audio(self, duration=5, path=AUDIO_INPUT_PATH, sr=SAMPLE_RATE):
        print("Recording... Speak now!")
        audio = sd.rec(int(duration * sr), samplerate=sr, channels=1)
        sd.wait()
        sf.write(path, audio, sr)
        print(f"Audio saved to {path}")
        return path

    def transcribe(self, audio_path):
        print("Transcribing audio...")
        result = self.model.transcribe(audio_path, language='en')
        text = result["text"].strip()
        print(f"Transcript: {text}")
        return text
