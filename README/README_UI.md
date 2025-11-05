# Food & Drug Interaction Chatbot UI

Instagram-style React UI integrated with LangGraph agent backend.

## Architecture

```
Frontend (React + Vite)  ←→  Backend (FastAPI)  ←→  LangGraph Agent
     Port 3000                  Port 8000            (new_agent_trial.py)
```

## Setup Instructions

### 1. Install Backend Dependencies

```bash
# Make sure you're in the genai_project_py313 virtual environment
source genai_project_py313/bin/activate

# Install FastAPI and Uvicorn
pip install fastapi uvicorn[standard]
```

### 2. Install Frontend Dependencies

```bash
cd cs614_genai_project/frontend
npm install
```

### 3. Start the Backend Server

```bash
# From the cs614_genai_project directory
cd cs614_genai_project
python api_server.py
```

The API will be available at:
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### 4. Start the Frontend Development Server

```bash
# In a new terminal
cd cs614_genai_project/frontend
npm run dev
```

The UI will be available at: http://localhost:3000

## Features

✅ **Instagram-style UI** with modern design
✅ **Real-time chat** with the LangGraph agent
✅ **Conversation memory** using thread-based persistence
✅ **Loading indicators** while waiting for responses
✅ **Suggestion chips** for common queries
✅ **Error handling** with user-friendly messages
✅ **Responsive design** works on mobile and desktop

## API Endpoints

### POST /chat
Send a message to the agent and get a response.

**Request:**
```json
{
  "message": "I ate burger at 1pm today",
  "thread_id": "USER:local"
}
```

**Response:**
```json
{
  "message": "I've logged your meal...",
  "timestamp": "2025-11-02T19:30:00+08:00"
}
```

### GET /health
Check if the server is running and agent is initialized.

### POST /reset
Reset the conversation history for a thread.

## Customization

### Change Suggestions
Edit `src/App.jsx` and modify the `suggestions` array:

```javascript
const suggestions = [
  { icon: "🍔", text: "Your custom suggestion" },
  // Add more...
];
```

### Change API URL
Edit `src/App.jsx` and modify `API_BASE_URL`:

```javascript
const API_BASE_URL = 'http://your-backend-url:8000';
```

### Styling
The UI uses Tailwind CSS. Modify colors and styles in `src/App.jsx` or add custom CSS in `src/index.css`.

## Production Deployment

### Backend
```bash
# Use Gunicorn for production
pip install gunicorn
gunicorn api_server:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Frontend
```bash
npm run build
# Deploy the 'dist' folder to your hosting service
```

## Troubleshooting

### "Agent not initialized" error
- Make sure Ollama is running
- Check that all dependencies are installed
- Verify `.env` file has required credentials

### CORS errors
- Ensure the frontend URL is added to `allow_origins` in `api_server.py`
- Check that the backend is running before starting frontend

### Connection refused
- Verify backend is running on port 8000
- Check firewall settings
- Try http://127.0.0.1:8000 instead of localhost

## Tech Stack

**Frontend:**
- React 18
- Vite
- Tailwind CSS
- Lucide React (icons)
- Axios (HTTP client)

**Backend:**
- FastAPI
- Uvicorn
- LangGraph
- LangChain
- Ollama




