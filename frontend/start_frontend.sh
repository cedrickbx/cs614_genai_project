#!/bin/bash

# Start the Food-Drug Chatbot Frontend

echo "🎨 Starting Food-Drug Interaction Chatbot Frontend..."
echo ""

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Start the development server
echo "✅ Starting frontend on http://localhost:3000"
echo ""
npm run dev









