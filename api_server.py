import os
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from langchain_core.messages import HumanMessage, AIMessage
import sys
import io
import uvicorn
sys.path.insert(0, os.path.dirname(__file__))
from new_agent_trial import build_once
from voice_service import get_voice_service

app = FastAPI(title="Food-Drug Interaction Chatbot API")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables to store agent components
client = None
agent = None
graph = None
voice_service = None

class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = "USER:local"

class ChatResponse(BaseModel):
    message: str
    timestamp: str

@app.on_event("startup")
async def startup_event():
    """Initialize the agent when the server starts"""
    global client, agent, graph
    print("Initializing Food-Drug Interaction Agent...")
    try:
        client, agent, graph = await build_once()
        print("Agent initialized successfully!")
    except Exception as e:
        print(f"Failed to initialize agent: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources"""
    global client
    if client:
        pass

@app.get("/")
async def root():
    return {"message": "Food-Drug Interaction Chatbot API", "status": "running"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent_initialized": graph is not None
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint that processes user messages and returns agent responses
    """
    global graph
    
    if graph is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    try:
        # Create the user message
        user_message = HumanMessage(content=request.message)
        
        # Process through the graph with the specified thread_id
        print(f"Processing message: {request.message[:50]}...")
        final_state = await graph.with_config({
            "recursion_limit": 15,  
            "configurable": {"thread_id": request.thread_id}
        }).ainvoke({"messages": [user_message]})
        
        # Extract the latest AI response
        messages = final_state.get("messages", [])
        last_ai_message = next(
            (m for m in reversed(messages) if isinstance(m, AIMessage)), 
            None
        )
        
        if last_ai_message:
            response_text = last_ai_message.content.strip()
        else:
            response_text = "I apologize, but I couldn't generate a response. Please try again."
        
        print(f"Response generated: {response_text[:50]}...")
        
        from datetime import datetime
        return ChatResponse(
            message=response_text,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        print(f"Error processing chat: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")

@app.post("/reset")
async def reset_conversation(thread_id: str = "USER:local"):
    """
    Reset the conversation history for a specific thread
    """
    return {"message": "Conversation reset", "thread_id": thread_id}

@app.get("/threads")
async def list_threads():
    """
    List available conversation threads
    """
    return {"threads": ["USER:local"]}

# ==================== Voice Endpoints ====================

class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "female"  

@app.post("/tts")
async def text_to_speech(request: TTSRequest):
    """
    Text-to-Speech endpoint using FREE Microsoft Edge TTS
    - No API key required
    - Unlimited usage
    - High quality voices
    
    Args:
        request: TTSRequest with text and optional voice type
        
    Returns:
        Audio file (MP3 format)
    """
    global voice_service
    
    try:
        # Lazy load voice service
        if voice_service is None:
            print("Initializing voice service...")
            voice_service = get_voice_service(voice=request.voice)
        
        if not request.text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        print(f"TTS request: {request.text[:50]}...")
        print(f"Text length: {len(request.text)} characters")
        
        # Generate speech (use async version to avoid event loop conflict)
        result = await voice_service.synthesize_to_bytes_async(request.text)
        print(f"TTS result: {result.get('success')}")
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "TTS failed"))
        
        # Return audio as streaming response
        audio_bytes = result["audio_bytes"]
        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f"attachment; filename=speech.mp3",
                "Accept-Ranges": "bytes"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"TTS error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"TTS failed: {str(e)}")

if __name__ == "__main__":
    print("Starting Food-Drug Interaction Chatbot API...")
    print("API will be available at: http://localhost:8000")
    print("API docs available at: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)


