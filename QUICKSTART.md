# 🚀 Quick Start Guide - Food & Drug Chatbot UI

## Prerequisites

✅ Ollama installed and running
✅ Python virtual environment (`genai_project_py313`)
✅ Node.js and npm installed
✅ All dependencies from `requirements.txt` installed
✅ `.env` file configured with API keys

## Step-by-Step Launch

### Option 1: Using Start Scripts (Easiest)

#### Terminal 1 - Start Backend
```bash
cd cs614_genai_project
./start_backend.sh
```

Wait until you see:
```
✅ All components initialized successfully!
INFO:     Uvicorn running on http://0.0.0.0:8000
```

#### Terminal 2 - Start Frontend
```bash
cd cs614_genai_project/frontend
./start_frontend.sh
```

Wait for:
```
  VITE v5.x.x  ready in xxx ms
  ➜  Local:   http://localhost:3000/
```

### Option 2: Manual Start

#### Terminal 1 - Backend
```bash
cd "GenAI & LLM"
source genai_project_py313/bin/activate
cd cs614_genai_project
python api_server.py
```

#### Terminal 2 - Frontend
```bash
cd "GenAI & LLM/cs614_genai_project/frontend"
npm install  # First time only
npm run dev
```

## Access the App

🌐 Open your browser and go to: **http://localhost:3000**

You should see an Instagram-style chat interface!

## Test It Out

Try these example queries:
- "I ate burger at 1pm today"
- "What medications am I taking?"
- "Can I take paracetamol with coffee?"
- "What is the interaction between grapefruit and statins?"

## Troubleshooting

### Backend won't start

**Error:** `ModuleNotFoundError: No module named 'fastapi'`
```bash
source genai_project_py313/bin/activate
pip install fastapi "uvicorn[standard]"
```

**Error:** `Agent not initialized` or Ollama errors
```bash
# Make sure Ollama is running
ollama serve

# In another terminal, pull required models
ollama pull qwen3:8b
ollama pull nomic-embed-text
```

**Error:** `MYSQL_PASSWORD not set`
- Check your `.env` file has `MYSQL_PASSWORD=your_password`

### Frontend won't start

**Error:** `npm: command not found`
- Install Node.js from https://nodejs.org/

**Error:** Dependencies not installed
```bash
cd cs614_genai_project/frontend
npm install
```

### Connection Issues

**Error:** "Failed to get response from server"
- Make sure backend is running on port 8000
- Check `http://localhost:8000/health` in your browser
- Verify no firewall is blocking the connection

**CORS errors in browser console**
- Make sure both servers are running
- Check that frontend is on port 3000

## API Endpoints

You can test the API directly:

### Health Check
```bash
curl http://localhost:8000/health
```

### Send a Message
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, what can you do?", "thread_id": "USER:local"}'
```

### View API Documentation
Open in browser: http://localhost:8000/docs

## Architecture Overview

```
┌─────────────────┐      HTTP/REST      ┌──────────────────┐
│  React Frontend │ ◄─────────────────► │  FastAPI Backend │
│  (Port 3000)    │                     │   (Port 8000)    │
└─────────────────┘                     └──────────────────┘
                                                 │
                                                 ▼
                                        ┌─────────────────┐
                                        │  LangGraph      │
                                        │  Agent          │
                                        │  (new_agent_    │
                                        │   trial.py)     │
                                        └─────────────────┘
                                                 │
                                    ┌────────────┼────────────┐
                                    ▼            ▼            ▼
                                ┌────────┐  ┌────────┐  ┌────────┐
                                │ Ollama │  │  MCP   │  │ SQLite │
                                │  LLM   │  │ Servers│  │   DB   │
                                └────────┘  └────────┘  └────────┘
```

## Features

✨ **Instagram-Style UI** - Modern, beautiful chat interface
💬 **Persistent Conversations** - Chat history saved automatically
🔄 **Real-Time Updates** - Instant responses with loading indicators
🎯 **Smart Suggestions** - Quick-start suggestions for common queries
⚡ **Fast** - Optimized for speed with async processing
🔒 **Safe** - Clear warnings about medical advice limitations

## Next Steps

1. **Customize Suggestions** - Edit `frontend/src/App.jsx` to change suggestion chips
2. **Add Features** - Extend the API in `api_server.py`
3. **Style Changes** - Modify Tailwind classes in `App.jsx`
4. **Deploy** - See `README_UI.md` for production deployment guide

## Stopping the Servers

Press `Ctrl+C` in each terminal window to stop the servers.

## Need Help?

- Check backend logs in Terminal 1
- Check frontend console in Browser DevTools (F12)
- Review `README_UI.md` for detailed documentation
- Test API at http://localhost:8000/docs

Enjoy your Food & Drug Interaction Chatbot! 🎉




