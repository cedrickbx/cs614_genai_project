# 🎤 Quick Start Guide - Voice Features

## ✅ Setup Complete!

Voice features are now ready to use. Just follow these steps:

## 🚀 Start the App

### 1. Start Backend (Terminal 1)

```bash
cd "/Users/dauvudangkhoi/Document/GenAI & LLM/cs614_genai_project"
python api_server.py
```

**Wait for:** `✅ Agent initialized successfully!`

### 2. Start Frontend (Terminal 2)

```bash
cd "/Users/dauvudangkhoi/Document/GenAI & LLM/cs614_genai_project/frontend"
npm run dev
```

**Open:** http://localhost:5173

## 🎯 How to Use

### Voice Input (Speech-to-Text)
1. Click the 🎤 **microphone icon**
2. Allow microphone access (first time only)
3. Speak your question clearly
4. Text appears automatically in the input box
5. Click Send or press Enter

### Voice Output (Text-to-Speech)
1. Get a response from the AI
2. Click the 🔊 **"Listen"** button below the response
3. Audio plays automatically

## 🎭 Voice Commands Examples

Try saying:
- "What foods interact with warfarin?"
- "Can I eat grapefruit with statins?"
- "Is coffee safe with antibiotics?"
- "Tell me about vitamin K and blood thinners"

## 🔧 Troubleshooting

### "Failed to generate speech"
→ **Solution:** Restart the backend server (`python api_server.py`)

### "Speech recognition not supported"
→ **Solution:** Use Chrome, Edge, or Safari browser

### "Microphone permission denied"
→ **Solution:** Click the lock icon 🔒 in address bar → Allow microphone

### "No audio playing"
→ **Solution:** 
- Check device volume
- Check browser isn't muted (look for speaker icon on tab)
- Try clicking "Listen" again

## 🌐 Browser Compatibility

| Browser | Status |
|---------|--------|
| Chrome  | ✅ Recommended |
| Edge    | ✅ Perfect |
| Safari  | ✅ Good |
| Firefox | ⚠️ Limited ASR |

## 📝 Notes

- Voice input uses your browser's built-in speech recognition (FREE!)
- Voice output uses Microsoft Edge TTS (FREE, unlimited!)
- No API keys or payment required
- Works offline for voice input (requires internet for TTS)

## 🎉 That's It!

Enjoy your voice-enabled AI assistant!

---

**Having issues?** See [VOICE_SETUP.md](VOICE_SETUP.md) for detailed troubleshooting.

