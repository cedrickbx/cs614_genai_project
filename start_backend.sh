#!/bin/bash

# Start the Food-Drug Chatbot Backend

echo "🚀 Starting Food-Drug Interaction Chatbot Backend..."
echo "📍 Make sure Ollama is running!"
echo ""

# Activate virtual environment if needed
if [ -d "../genai_project_py313" ]; then
    source ../genai_project_py313/bin/activate
fi

# Check if FastAPI is installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "❌ FastAPI not found. Installing..."
    pip install fastapi uvicorn[standard]
fi

# Start the server
echo "✅ Starting server on http://localhost:8000"
echo "📖 API docs available at http://localhost:8000/docs"
echo ""
python api_server.py


