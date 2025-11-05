# 🎤 Voice Features Setup (FREE!)

## ✨ What You Get

- **ASR (Speech-to-Text)**: Browser's Web Speech API - 100% FREE, no backend needed!
- **TTS (Text-to-Speech)**: Microsoft Edge TTS - 100% FREE, unlimited usage, high quality!

## 🚀 Quick Setup

### 1. Install TTS Dependency

```bash
pip install edge-tts
```

That's it! No API keys, no signup, completely free!

### 2. Start Backend

```bash
python api_server.py
```

### 3. Start Frontend

```bash
cd frontend
npm run dev
```

### 4. Use Voice Features

Open http://localhost:5173

- **🎤 Voice Input**: Click microphone button → Speak → Text appears automatically
- **🔊 Voice Output**: Click "Listen" button on any response → Hear it spoken

## 🎯 How It Works

### ASR (Voice Input)
- Uses browser's built-in Web Speech API
- **FREE** - No backend processing
- **Fast** - Instant transcription
- Works in Chrome, Edge, Safari

### TTS (Voice Output)
- Uses Microsoft Edge TTS API
- **FREE** - No API key needed
- **Unlimited** - No rate limits
- **High Quality** - Natural voices
- Multiple voices available

## 🎭 Available Voices

```python
voices = {
    'female': 'en-US-AriaNeural',      # US Female (default)
    'male': 'en-US-GuyNeural',         # US Male
    'female_uk': 'en-GB-SoniaNeural',  # UK Female
    'male_uk': 'en-GB-RyanNeural',     # UK Male
    'female_au': 'en-AU-NatashaNeural',# Australian Female
}
```

## 📋 Requirements

**Backend:**
- `edge-tts` - Free Microsoft TTS

**Frontend:**
- Modern browser (Chrome, Edge, Safari, Firefox)
- Microphone access permission

## 🌐 Browser Compatibility

| Browser | Voice Input (ASR) | Voice Output (TTS) |
|---------|-------------------|-------------------|
| Chrome  | ✅ Perfect | ✅ Perfect |
| Edge    | ✅ Perfect | ✅ Perfect |
| Safari  | ✅ Good | ✅ Perfect |
| Firefox | ⚠️ Limited | ✅ Perfect |

## 🎬 Usage

### Voice Input
1. Click 🎤 microphone icon
2. Allow microphone access (first time only)
3. Speak your question
4. Text appears automatically
5. Press Enter or Send

### Voice Output
1. Get AI response
2. Click "Listen" button
3. Audio plays automatically

## 🔧 Troubleshooting

### "Microphone not working"
→ Check browser permissions (click lock icon in address bar)

### "Speech recognition not supported"
→ Use Chrome, Edge, or Safari

### "No audio playing"
→ Check device volume and browser isn't muted

### "TTS not working"
→ Make sure edge-tts is installed: `pip install edge-tts`

## 🆓 Why Free?

- **ASR**: Browser's Web Speech API is built into modern browsers
- **TTS**: Microsoft Edge TTS is publicly available without API keys

## 🎉 That's It!

No complex setup, no API keys, no payment required. Just install one package and you're ready to go!

---

**Enjoy your voice-enabled Food-Drug chatbot!** 🚀

