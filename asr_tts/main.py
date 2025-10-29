# main.py
from asr_module import ASRModel
from tts_module import TTSModel
import json, time, os

LOG_PATH = "logs/interactions.jsonl"
os.makedirs("logs", exist_ok=True)

def query_llm(prompt):
    """Stub for your GenAI model (replace later with MedGemma/Qwen)."""
    if "appointment" in prompt.lower():
        reply = "Your next appointment is scheduled for tomorrow at 10 AM."
    elif "update" in prompt.lower():
        reply = "Record updated successfully in the database."
    else:
        reply = "I'm here to help! Please provide more details."
    print("💬 LLM reply:", reply)
    return reply

def log_interaction(audio_in, transcript, llm_out, audio_out):
    log_entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "audio_input": audio_in,
        "transcript": transcript,
        "llm_output": llm_out,
        "tts_output": audio_out,
    }
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    print(f"🪵 Logged interaction to {LOG_PATH}")

def main():
    print("=== ASR → LLM → TTS Local Pipeline ===")
    asr = ASRModel()
    tts = TTSModel()

    # Step 1. Record & transcribe
    audio_path = asr.record_audio(duration=5)
    user_text = asr.transcribe(audio_path)

    # Step 2. Get LLM response
    llm_reply = query_llm(user_text)

    # Step 3. Convert reply to speech
    tts_path = tts.synthesize(llm_reply)

    # Step 4. Log
    log_interaction(audio_path, user_text, llm_reply, tts_path)
    print("Pipeline complete.")

if __name__ == "__main__":
    main()


