#!/usr/bin/env python3
"""
Avatar Conversation Server - Pipecat Integration
=================================================
A WebSocket-based application for real-time avatar conversations using pipecat pipelines.

Features:
- Upload custom avatar images
- Record audio with STT (Speech-to-Text)
- LLM-powered AI responses
- TTS (Text-to-Speech) output
- Animated avatar display
- Continuous conversation mode

Usage:
    python server.py
    Then open http://localhost:5000
"""

import os
import sys
import json
import base64
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

import numpy as np
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Flask imports
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename

# Pipecat imports
try:
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.runner import PipelineRunner
    from pipecat.pipeline.task import PipelineParams, PipelineTask
    from pipecat.processors.aggregators.llm_context import LLMContext
    from pipecat.frames.frames import TextFrame, AudioRawFrame
    HAS_PIPECAT = True
except ImportError:
    HAS_PIPECAT = False
    print("Note: Pipecat not fully installed. Running in standalone mode.")

# STT Service
try:
    from pipecat.services.groq.stt import GroqSTTService
    HAS_STT = True
except ImportError:
    HAS_STT = False

# LLM Service
try:
    from pipecat.services.ollama.llm import OLLamaLLMService
    HAS_LLM = True
except ImportError:
    HAS_LLM = False

# TTS Service
try:
    from pipecat.services.groq.tts import GroqTTSService
    HAS_TTS = True
except ImportError:
    HAS_TTS = False

# Try to import optional dependencies
try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
    print("Warning: OpenCV not installed. Avatar animation will be limited.")

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("Warning: Pillow not installed. Image processing will be limited.")

# =============================================================================
# Configuration
# =============================================================================

BASE_DIR = Path(__file__).parent
UPLOADS_DIR = BASE_DIR / "uploads"
LOGS_DIR = BASE_DIR / "logs"
STATIC_DIR = BASE_DIR / "static"

# Create directories
UPLOADS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)

# Settings
SAMPLE_RATE = 16000
AVATAR_SIZE = 512
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# =============================================================================
# Logging Setup
# =============================================================================

log_file = LOGS_DIR / f"server_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# =============================================================================
# Flask Application
# =============================================================================

app = Flask(__name__, template_folder=str(BASE_DIR), static_folder=str(STATIC_DIR))
app.config['SECRET_KEY'] = 'avatar-conversation-secret-key'
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# =============================================================================
# Pipecat Services Initialization
# =============================================================================

# Initialize pipecat services if available
stt_service = None
llm_service = None
tts_service = None

def init_pipecat_services():
    """Initialize pipecat STT, LLM, and TTS services."""
    global stt_service, llm_service, tts_service
    
    # STT: Groq Whisper
    if HAS_STT and os.getenv("GROQ_API_KEY"):
        try:
            stt_service = GroqSTTService(api_key=os.getenv("GROQ_API_KEY"))
            logger.info("✓ STT Service: Groq Whisper initialized")
        except Exception as e:
            logger.warning(f"STT initialization failed: {e}")
    
    # LLM: Ollama (local)
    if HAS_LLM:
        try:
            llm_service = OLLamaLLMService(
                model=os.getenv("OLLAMA_MODEL", "mistral"),
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
            )
            logger.info("✓ LLM Service: Ollama initialized")
        except Exception as e:
            logger.warning(f"LLM initialization failed: {e}")
    
    # TTS: Groq
    if HAS_TTS and os.getenv("GROQ_API_KEY"):
        try:
            tts_service = GroqTTSService(api_key=os.getenv("GROQ_API_KEY"))
            logger.info("✓ TTS Service: Groq initialized")
        except Exception as e:
            logger.warning(f"TTS initialization failed: {e}")

# =============================================================================
# Avatar Session Management
# =============================================================================

class AvatarSession:
    """Manages state for each connected client with pipecat integration."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.avatar_image: Optional[np.ndarray] = None
        self.avatar_path: Optional[str] = None
        self.conversation_history: list = []
        
        # AI Settings
        self.system_prompt = "You are a helpful, friendly AI assistant named Avatar."
        self.temperature = 0.7
        self.max_tokens = 500
        self.continuous_mode = False
        self.avatar_name = "Avatar"
        
        # Pipecat context
        if HAS_PIPECAT:
            self.context = LLMContext([
                {"role": "system", "content": self.system_prompt}
            ])
        
        logger.info(f"Session created: {session_id}")
    
    def set_avatar_image(self, image_path: str):
        """Load avatar image from file."""
        self.avatar_path = image_path
        if HAS_CV2:
            self.avatar_image = cv2.imread(image_path)
            if self.avatar_image is not None:
                # Resize to standard size
                self.avatar_image = cv2.resize(self.avatar_image, (AVATAR_SIZE, AVATAR_SIZE))
                logger.info(f"Avatar image loaded: {image_path}")
            else:
                logger.error(f"Failed to load avatar image: {image_path}")
        elif HAS_PIL:
            img = Image.open(image_path)
            img = img.resize((AVATAR_SIZE, AVATAR_SIZE))
            self.avatar_image = np.array(img)
            logger.info(f"Avatar image loaded (PIL): {image_path}")
    
    def generate_response(self, user_text: str) -> str:
        """Generate AI response using pipecat LLM service or fallback."""
        # Store in history
        self.conversation_history.append({"role": "user", "content": user_text})
        
        response = ""
        
        # Try using pipecat LLM service
        if llm_service:
            try:
                # Build messages for LLM
                messages = [
                    {"role": "system", "content": self.system_prompt}
                ] + self.conversation_history
                
                # Use asyncio to run the LLM (simplified for demo)
                # In production, use proper async pipeline
                import httpx
                base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
                
                resp = httpx.post(
                    f"{base_url}/api/chat",
                    json={
                        "model": os.getenv("OLLAMA_MODEL", "mistral"),
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": self.temperature,
                            "num_predict": self.max_tokens
                        }
                    },
                    timeout=60.0
                )
                
                if resp.status_code == 200:
                    response = resp.json().get("message", {}).get("content", "")
                    logger.info(f"LLM response received ({len(response)} chars)")
                else:
                    logger.warning(f"LLM request failed: {resp.status_code}")
                    response = f"I received your message: \"{user_text}\". (LLM unavailable)"
            except Exception as e:
                logger.error(f"LLM error: {e}")
                response = f"I heard you say: \"{user_text}\". (LLM connection error)"
        else:
            # Fallback: simple echo response
            response = f"Hello! You said: \"{user_text}\". I'm {self.avatar_name}, your AI assistant."
        
        self.conversation_history.append({"role": "assistant", "content": response})
        return response
    
    def generate_avatar_frame(self, talking: bool = False) -> Optional[bytes]:
        """Generate a single avatar frame."""
        if self.avatar_image is None:
            # Generate placeholder frame
            if HAS_CV2:
                frame = np.zeros((AVATAR_SIZE, AVATAR_SIZE, 3), dtype=np.uint8)
                frame[:] = (50, 50, 50)  # Dark gray background
                
                # Draw placeholder avatar (circle for head)
                center = (AVATAR_SIZE // 2, AVATAR_SIZE // 2)
                cv2.circle(frame, center, 150, (100, 150, 200), -1)  # Face
                cv2.circle(frame, (center[0] - 50, center[1] - 30), 20, (255, 255, 255), -1)  # Left eye
                cv2.circle(frame, (center[0] + 50, center[1] - 30), 20, (255, 255, 255), -1)  # Right eye
                cv2.circle(frame, (center[0] - 50, center[1] - 30), 10, (50, 50, 50), -1)  # Left pupil
                cv2.circle(frame, (center[0] + 50, center[1] - 30), 10, (50, 50, 50), -1)  # Right pupil
                
                # Mouth (changes when talking)
                if talking:
                    cv2.ellipse(frame, (center[0], center[1] + 60), (40, 25), 0, 0, 180, (50, 50, 50), -1)
                else:
                    cv2.ellipse(frame, (center[0], center[1] + 60), (30, 10), 0, 0, 180, (50, 50, 50), -1)
                
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                return buffer.tobytes()
            return None
        
        # Use uploaded avatar image
        frame = self.avatar_image.copy()
        
        if talking and HAS_CV2:
            # Simple animation: slight brightness variation
            alpha = 1.0 + np.random.uniform(-0.05, 0.05)
            frame = np.clip(frame * alpha, 0, 255).astype(np.uint8)
        
        if HAS_CV2:
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            return buffer.tobytes()
        
        return None

# Session storage
sessions: dict[str, AvatarSession] = {}

# =============================================================================
# Routes
# =============================================================================

@app.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files."""
    return send_from_directory(str(STATIC_DIR), filename)

@app.route('/uploads/<path:filename>')
def serve_uploads(filename):
    """Serve uploaded files."""
    return send_from_directory(str(UPLOADS_DIR), filename)

@app.route('/api/status')
def api_status():
    """Get server status including pipecat services."""
    return jsonify({
        'status': 'running',
        'sessions': len(sessions),
        'pipecat': {
            'available': HAS_PIPECAT,
            'stt': stt_service is not None,
            'llm': llm_service is not None,
            'tts': tts_service is not None,
        },
        'features': {
            'cv2': HAS_CV2,
            'pil': HAS_PIL,
        },
        'avatar_size': AVATAR_SIZE,
        'sample_rate': SAMPLE_RATE
    })

@app.route('/api/upload', methods=['POST'])
def api_upload():
    """Handle avatar image upload."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate extension
        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        if ext not in ALLOWED_EXTENSIONS:
            return jsonify({'error': f'Invalid file type. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
        
        # Save file
        filename = secure_filename(f"avatar_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}")
        filepath = UPLOADS_DIR / filename
        file.save(filepath)
        
        logger.info(f"Avatar uploaded: {filepath}")
        
        # Get session and update avatar
        session_id = request.form.get('session_id')
        if session_id and session_id in sessions:
            sessions[session_id].set_avatar_image(str(filepath))
        
        return jsonify({
            'success': True,
            'filename': filename,
            'url': f'/uploads/{filename}'
        })
    
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs')
def api_logs():
    """Get recent logs."""
    try:
        limit = request.args.get('limit', 50, type=int)
        logs = []
        
        log_files = sorted(LOGS_DIR.glob('*.log'), reverse=True)
        if log_files:
            with open(log_files[0], 'r', encoding='utf-8') as f:
                logs = f.readlines()[-limit:]
        
        return jsonify({'logs': [l.strip() for l in logs]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =============================================================================
# WebSocket Events
# =============================================================================

@socketio.on('connect')
def handle_connect():
    """Handle new client connection."""
    session_id = request.sid
    sessions[session_id] = AvatarSession(session_id)
    emit('connected', {'session_id': session_id})
    logger.info(f"Client connected: {session_id}")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    session_id = request.sid
    if session_id in sessions:
        del sessions[session_id]
    logger.info(f"Client disconnected: {session_id}")

@socketio.on('update_settings')
def handle_settings(data):
    """Update session settings."""
    session_id = request.sid
    if session_id not in sessions:
        return
    
    session = sessions[session_id]
    
    if 'system_prompt' in data:
        session.system_prompt = data['system_prompt']
    if 'temperature' in data:
        session.temperature = float(data['temperature'])
    if 'max_tokens' in data:
        session.max_tokens = int(data['max_tokens'])
    if 'continuous_mode' in data:
        session.continuous_mode = bool(data['continuous_mode'])
    if 'avatar_name' in data:
        session.avatar_name = data['avatar_name']
    
    emit('settings_updated', {'success': True})
    logger.info(f"Settings updated for {session_id}")

@socketio.on('send_text')
def handle_text(data):
    """Handle text message from client."""
    session_id = request.sid
    if session_id not in sessions:
        emit('error', {'message': 'Session not found'})
        return
    
    session = sessions[session_id]
    user_text = data.get('text', '').strip()
    
    if not user_text:
        return
    
    logger.info(f"User ({session_id}): {user_text}")
    
    # Generate response
    response = session.generate_response(user_text)
    logger.info(f"Avatar ({session_id}): {response}")
    
    emit('response', {'text': response})
    
    # Send avatar frames (talking animation)
    for i in range(30):  # ~1 second of animation at 30fps
        frame = session.generate_avatar_frame(talking=True)
        if frame:
            emit('avatar_frame', {
                'frame': base64.b64encode(frame).decode('utf-8'),
                'index': i
            })
            socketio.sleep(0.033)  # ~30fps
    
    # Send final still frame
    frame = session.generate_avatar_frame(talking=False)
    if frame:
        emit('avatar_frame', {
            'frame': base64.b64encode(frame).decode('utf-8'),
            'final': True
        })
    
    emit('response_complete', {})

@socketio.on('send_audio')
def handle_audio(data):
    """Handle audio data from client."""
    session_id = request.sid
    if session_id not in sessions:
        emit('error', {'message': 'Session not found'})
        return
    
    session = sessions[session_id]
    
    # Decode audio
    audio_b64 = data.get('audio', '')
    if not audio_b64:
        return
    
    try:
        audio_bytes = base64.b64decode(audio_b64)
        # TODO: Integrate with STT service (Whisper, Groq, etc.)
        # For now, simulate transcription
        transcription = "[Audio received - STT integration pending]"
        
        emit('transcription', {'text': transcription})
        
        # Generate response
        response = session.generate_response(transcription)
        emit('response', {'text': response})
        
        # Send avatar frames
        for i in range(30):
            frame = session.generate_avatar_frame(talking=True)
            if frame:
                emit('avatar_frame', {
                    'frame': base64.b64encode(frame).decode('utf-8'),
                    'index': i
                })
                socketio.sleep(0.033)
        
        # Final frame
        frame = session.generate_avatar_frame(talking=False)
        if frame:
            emit('avatar_frame', {
                'frame': base64.b64encode(frame).decode('utf-8'),
                'final': True
            })
        
        emit('response_complete', {})
        
    except Exception as e:
        logger.error(f"Audio processing error: {e}")
        emit('error', {'message': str(e)})

@socketio.on('get_avatar_frame')
def handle_get_frame():
    """Get current avatar frame (for idle animation)."""
    session_id = request.sid
    if session_id not in sessions:
        return
    
    session = sessions[session_id]
    frame = session.generate_avatar_frame(talking=False)
    if frame:
        emit('avatar_frame', {
            'frame': base64.b64encode(frame).decode('utf-8'),
            'idle': True
        })

# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Start the server with pipecat services."""
    print("=" * 60)
    print("  Avatar Conversation Server (Pipecat)")
    print("=" * 60)
    
    # Initialize pipecat services
    init_pipecat_services()
    
    print("")
    print("  Services Status:")
    print(f"    Pipecat: {'✓' if HAS_PIPECAT else '✗'}")
    print(f"    STT:     {'✓ Groq Whisper' if stt_service else '✗ Not configured'}")
    print(f"    LLM:     {'✓ Ollama' if llm_service else '✗ Not configured'}")
    print(f"    TTS:     {'✓ Groq' if tts_service else '✗ Not configured'}")
    print(f"    OpenCV:  {'✓' if HAS_CV2 else '✗'}")
    print("")
    print(f"  URL: http://localhost:5000")
    print(f"  Logs: {log_file}")
    print(f"  Uploads: {UPLOADS_DIR}")
    print("=" * 60)
    print("  Press Ctrl+C to stop")
    print("=" * 60)
    
    try:
        socketio.run(app, host='127.0.0.1', port=5000, debug=True, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
