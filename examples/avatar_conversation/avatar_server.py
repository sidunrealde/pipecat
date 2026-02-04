#!/usr/bin/env python3
"""
Avatar Conversation Server
==========================

A complete server that:
1. Serves the web frontend
2. Handles avatar image uploads
3. Runs the pipecat conversation pipeline with lip-sync

Usage:
    python avatar_server.py
    
Then open http://localhost:7860 in your browser
"""

import asyncio
import base64
import io
import os
import json
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from loguru import logger
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse

# Load environment
script_dir = Path(__file__).resolve().parent
load_dotenv(script_dir / ".env", override=True)

# Pipecat imports
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import Frame, LLMRunFrame, ImageRawFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.services.groq.stt import GroqSTTService
from pipecat.services.groq.tts import GroqTTSService
from pipecat.services.ollama.llm import OLLamaLLMService
from pipecat.turns.user_turn_strategies import UserTurnStrategies

# Try smart turn
try:
    from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
    from pipecat.turns.user_stop import TurnAnalyzerUserTurnStopStrategy
    HAS_SMART_TURN = True
except ImportError:
    HAS_SMART_TURN = False

# Avatar processor
try:
    from avatar_processor import AvatarRenderer
    HAS_AVATAR = True
except ImportError:
    HAS_AVATAR = False
    logger.warning("Avatar processor not available")

# FastAPI app
app = FastAPI(title="Avatar Conversation")

# State
current_avatar_image: Optional[bytes] = None
avatar_renderer: Optional[AvatarRenderer] = None

# Uploads directory
UPLOADS_DIR = script_dir / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)


# =============================================================================
# Static files and pages
# =============================================================================

# Serve static files
app.mount("/static", StaticFiles(directory=str(script_dir / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main page."""
    index_path = script_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return HTMLResponse("<h1>Avatar Conversation</h1><p>index.html not found</p>")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "avatar_loaded": current_avatar_image is not None,
        "has_avatar_processor": HAS_AVATAR,
        "has_smart_turn": HAS_SMART_TURN,
    }


# =============================================================================
# Avatar Upload
# =============================================================================

@app.post("/upload-avatar")
async def upload_avatar(file: UploadFile = File(...)):
    """
    Upload an avatar image.
    
    The image will be processed and used for lip-sync animation.
    """
    global current_avatar_image, avatar_renderer
    
    try:
        # Read file
        contents = await file.read()
        
        # Validate it's an image
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(400, "File must be an image")
        
        # Save to uploads
        filename = f"avatar_{file.filename}"
        filepath = UPLOADS_DIR / filename
        with open(filepath, "wb") as f:
            f.write(contents)
        
        # Store in memory
        current_avatar_image = contents
        
        # Initialize avatar renderer if available
        if HAS_AVATAR:
            avatar_renderer = AvatarRenderer(fps=25, output_size=(512, 512))
            success = avatar_renderer.set_avatar_from_bytes(contents)
            if success:
                logger.info(f"Avatar loaded successfully: {filename}")
            else:
                logger.warning("Failed to process avatar image")
        
        return {
            "success": True,
            "filename": filename,
            "size": len(contents),
            "message": "Avatar uploaded successfully"
        }
        
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(500, str(e))


@app.get("/current-avatar")
async def get_current_avatar():
    """Get the current avatar image as base64."""
    if current_avatar_image is None:
        return {"avatar": None}
    
    b64 = base64.b64encode(current_avatar_image).decode()
    return {"avatar": f"data:image/png;base64,{b64}"}


# =============================================================================
# WebSocket for conversation
# =============================================================================

class WebSocketAudioTransport:
    """
    Simple WebSocket transport for audio/video.
    
    This is a simplified transport that works with WebSocket
    instead of full WebRTC (easier for development).
    """
    
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.input_queue = asyncio.Queue()
        self.is_connected = True
    
    async def send_audio(self, audio_data: bytes, sample_rate: int = 16000):
        """Send audio data to the client."""
        if not self.is_connected:
            return
        try:
            b64_audio = base64.b64encode(audio_data).decode()
            await self.websocket.send_json({
                "type": "audio",
                "data": b64_audio,
                "sample_rate": sample_rate,
            })
        except Exception as e:
            logger.error(f"Failed to send audio: {e}")
    
    async def send_video(self, frame_data: bytes, width: int, height: int):
        """Send video frame to the client."""
        if not self.is_connected:
            return
        try:
            b64_frame = base64.b64encode(frame_data).decode()
            await self.websocket.send_json({
                "type": "video",
                "data": b64_frame,
                "width": width,
                "height": height,
            })
        except Exception as e:
            logger.error(f"Failed to send video: {e}")
    
    async def send_text(self, text: str, role: str = "assistant"):
        """Send text message to the client."""
        if not self.is_connected:
            return
        try:
            await self.websocket.send_json({
                "type": "text",
                "role": role,
                "content": text,
            })
        except Exception as e:
            logger.error(f"Failed to send text: {e}")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time conversation.
    
    Protocol:
    - Client sends: {"type": "audio", "data": base64_audio}
    - Server sends: {"type": "audio", "data": base64_audio}
    - Server sends: {"type": "video", "data": base64_frame}
    - Server sends: {"type": "text", "role": "assistant", "content": "..."}
    """
    await websocket.accept()
    transport = WebSocketAudioTransport(websocket)
    
    logger.info("Client connected")
    
    # Send current avatar if available
    if current_avatar_image:
        b64 = base64.b64encode(current_avatar_image).decode()
        await websocket.send_json({
            "type": "avatar",
            "data": b64,
        })
    
    try:
        # Simple conversation loop
        # Note: For full pipecat integration, use the WebRTC transport
        # This is a simplified demo
        
        await websocket.send_json({
            "type": "status",
            "message": "Connected! Ready for conversation.",
        })
        
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "audio":
                # Decode audio
                audio_b64 = data.get("data", "")
                audio_bytes = base64.b64decode(audio_b64)
                
                # TODO: Process through pipecat pipeline
                # For now, echo back a response
                await websocket.send_json({
                    "type": "status",
                    "message": f"Received {len(audio_bytes)} bytes of audio",
                })
            
            elif data.get("type") == "text":
                # Text input
                text = data.get("content", "")
                logger.info(f"User: {text}")
                
                # TODO: Process through LLM
                # For now, echo back
                await transport.send_text(f"You said: {text}")
                
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        transport.is_connected = False


# =============================================================================
# Main entry point
# =============================================================================

def main():
    """Run the avatar conversation server."""
    print("=" * 60)
    print("  Avatar Conversation Server")
    print("=" * 60)
    print()
    print("  Open http://localhost:7860 in your browser")
    print()
    print("  Features:")
    print("    - Upload avatar image")
    print("    - Real-time lip-sync")
    print("    - Voice conversation")
    print()
    print("=" * 60)
    
    uvicorn.run(
        "avatar_server:app",
        host="0.0.0.0",
        port=7860,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
