#!/usr/bin/env python3
"""
Trae AI Conversational Assistant with HuggingFace Integration
Multimodal chat assistant for coding with voice, screen sharing, and keyboard input
"""

import os
import asyncio
import json
import base64
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import torch
import requests
from huggingface_hub import hf_hub_download, snapshot_download
from transformers import AutoTokenizer, AutoModelForCausalLM
from PIL import Image
import io
import numpy as np
import cv2
import subprocess
import tempfile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Trae AI Conversational Assistant",
    description="Multimodal chat assistant with HuggingFace LLM integration",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: str
    message_type: str = "text"  # text, image, code, screen

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    multimodal_data: Optional[Dict[str, Any]] = None

class SystemStatus(BaseModel):
    status: str
    model_loaded: bool
    gpu_available: bool
    memory_usage: Dict[str, float]

# Global variables
conversations: Dict[str, List[ChatMessage]] = {}
connected_clients: Dict[str, WebSocket] = {}
model_cache = {}

class TraeAIAssistant:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_name = "unsloth/gemma-2-9b-it-bnb-4bit"  # Optimized Gemma model
        
        # Initialize models
        self.tokenizer = None
        self.model = None
        
        logger.info(f"Initializing Trae AI Assistant on {self.device}")
        
    async def load_models(self):
        """Load the main language model"""
        try:
            logger.info("Loading Gemma model from HuggingFace...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map="auto" if self.device == "cuda" else None,
                trust_remote_code=True,
                load_in_4bit=True if self.device == "cuda" else False
            )
            
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            logger.info("Model loaded successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False
    
    async def generate_response(self, prompt: str, conversation_history: List[ChatMessage] = None, multimodal_data: Dict = None) -> str:
        """Generate AI response with context awareness"""
        try:
            # Build conversation context
            context = self._build_context(conversation_history)
            
            # Handle multimodal input (simplified)
            if multimodal_data:
                if "image" in multimodal_data:
                    context += "\n[User shared an image]"
                if "screen" in multimodal_data:
                    context += "\n[User shared screen content]"
            
            # Create system prompt for coding assistant
            system_prompt = """You are Trae AI, an advanced coding assistant. You help developers with code generation, debugging, optimization, architecture design, and best practices. Always provide helpful, accurate responses with working code examples when appropriate."""
            
            # Format the full prompt using Gemma chat template
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{context}\n\n{prompt}"}
            ]
            
            # Apply chat template
            formatted_prompt = self.tokenizer.apply_chat_template(
                messages, 
                tokenize=False, 
                add_generation_prompt=True
            )
            
            # Generate response
            inputs = self.tokenizer(formatted_prompt, return_tensors="pt", truncation=True, max_length=2048)
            if self.device == "cuda":
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=512,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=self.tokenizer.pad_token_id,
                    repetition_penalty=1.1,
                    top_p=0.9
                )
            
            response = self.tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return f"I apologize, but I encountered an error while processing your request: {str(e)}"
    
    def _build_context(self, conversation_history: List[ChatMessage]) -> str:
        """Build conversation context from history"""
        if not conversation_history:
            return ""
        
        context_lines = []
        for msg in conversation_history[-10:]:  # Last 10 messages
            role = "User" if msg.role == "user" else "Assistant"
            context_lines.append(f"{role}: {msg.content}")
        
        return "\n".join(context_lines)
    
    async def process_image(self, image_data: str) -> str:
        """Basic image processing placeholder"""
        try:
            # For now, just acknowledge image upload
            # Can be enhanced with vision models later
            return "Image received and processed"
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            return "Unable to process image"
    
    async def process_speech(self, audio_data: bytes) -> str:
        """Basic speech processing placeholder"""
        try:
            # For now, return placeholder
            # Can be enhanced with Whisper or other STT models later
            return "Speech processing not yet implemented"
        except Exception as e:
            logger.error(f"Error processing speech: {e}")
            return ""

# Initialize assistant
assistant = TraeAIAssistant()

@app.on_event("startup")
async def startup_event():
    """Load models on startup"""
    logger.info("Starting Trae AI Assistant...")
    success = await assistant.load_models()
    if success:
        logger.info("Assistant ready!")
    else:
        logger.error("Failed to load models")

# Static files
app.mount("/static", StaticFiles(directory="../client"), name="static")

@app.get("/", response_class=HTMLResponse)
async def get_index():
    """Serve the main chat interface"""
    with open("../client/index-chat.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    gpu_available = torch.cuda.is_available()
    memory_info = {}
    
    if gpu_available:
        memory_info = {
            "gpu_memory_allocated": torch.cuda.memory_allocated() / 1024**3,
            "gpu_memory_reserved": torch.cuda.memory_reserved() / 1024**3,
            "gpu_memory_total": torch.cuda.get_device_properties(0).total_memory / 1024**3
        }
    
    return SystemStatus(
        status="healthy",
        model_loaded=assistant.model is not None,
        gpu_available=gpu_available,
        memory_usage=memory_info
    )

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """Main chat endpoint"""
    try:
        conversation_id = request.conversation_id or "default"
        
        # Get conversation history
        history = conversations.get(conversation_id, [])
        
        # Add user message to history
        user_message = ChatMessage(
            role="user",
            content=request.message,
            timestamp=datetime.now().isoformat(),
            message_type="text"
        )
        history.append(user_message)
        
        # Generate AI response
        ai_response = await assistant.generate_response(
            request.message, 
            history, 
            request.multimodal_data
        )
        
        # Add AI response to history
        assistant_message = ChatMessage(
            role="assistant",
            content=ai_response,
            timestamp=datetime.now().isoformat(),
            message_type="text"
        )
        history.append(assistant_message)
        
        # Update conversation
        conversations[conversation_id] = history
        
        # Broadcast to connected clients
        await broadcast_message(conversation_id, assistant_message)
        
        return {
            "response": ai_response,
            "conversation_id": conversation_id,
            "timestamp": assistant_message.timestamp
        }
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload-image")
async def upload_image(file: UploadFile = File(...), conversation_id: str = "default"):
    """Handle image uploads"""
    try:
        # Read and encode image
        image_data = await file.read()
        image_b64 = base64.b64encode(image_data).decode()
        
        # Process image
        description = await assistant.process_image(f"data:image/jpeg;base64,{image_b64}")
        
        return {
            "description": description,
            "image_data": f"data:image/jpeg;base64,{image_b64}"
        }
        
    except Exception as e:
        logger.error(f"Image upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/speech-to-text")
async def speech_to_text(file: UploadFile = File(...)):
    """Convert speech to text"""
    try:
        audio_data = await file.read()
        text = await assistant.process_speech(audio_data)
        
        return {"text": text}
        
    except Exception as e:
        logger.error(f"Speech processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket for real-time communication"""
    await websocket.accept()
    connected_clients[client_id] = websocket
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data["type"] == "chat":
                # Handle chat message
                response = await chat_endpoint(ChatRequest(**message_data["data"]))
                await websocket.send_text(json.dumps({
                    "type": "chat_response",
                    "data": response
                }))
            
            elif message_data["type"] == "screen_share":
                # Handle screen sharing
                screen_data = message_data["data"]["screen"]
                analysis = await assistant.process_image(screen_data)
                await websocket.send_text(json.dumps({
                    "type": "screen_analysis",
                    "data": {"analysis": analysis}
                }))
            
            elif message_data["type"] == "typing":
                # Broadcast typing indicator
                await broadcast_typing(client_id, message_data["data"])
                
    except WebSocketDisconnect:
        del connected_clients[client_id]
        logger.info(f"Client {client_id} disconnected")

async def broadcast_message(conversation_id: str, message: ChatMessage):
    """Broadcast message to all connected clients"""
    message_data = {
        "type": "new_message",
        "data": message.dict(),
        "conversation_id": conversation_id
    }
    
    disconnected_clients = []
    for client_id, websocket in connected_clients.items():
        try:
            await websocket.send_text(json.dumps(message_data))
        except:
            disconnected_clients.append(client_id)
    
    # Clean up disconnected clients
    for client_id in disconnected_clients:
        del connected_clients[client_id]

async def broadcast_typing(sender_id: str, typing_data: dict):
    """Broadcast typing indicator"""
    message_data = {
        "type": "typing",
        "data": typing_data,
        "sender_id": sender_id
    }
    
    for client_id, websocket in connected_clients.items():
        if client_id != sender_id:
            try:
                await websocket.send_text(json.dumps(message_data))
            except:
                pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )