#!/usr/bin/env python3
"""
Avatar Conversation - Custom WebRTC Server with Video Display
==============================================================

This script runs the avatar bot with a custom web interface that shows:
- The animated avatar with lip-sync
- Audio controls
- Chat interface
- Avatar upload

Usage:
    python run_avatar.py

Then open http://localhost:7860 in your browser.
"""

import asyncio
import base64
import os
import sys
import uuid
from pathlib import Path
from typing import Dict, Any, Optional

from dotenv import load_dotenv
from loguru import logger
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse
from pydantic import BaseModel

# Load environment
script_dir = Path(__file__).resolve().parent
load_dotenv(script_dir / ".env", override=True)

# Add parent to path for imports
sys.path.insert(0, str(script_dir))

# Pipecat imports
from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection, IceServer
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
from pipecat.transports.base_transport import TransportParams
from pipecat.runner.types import SmallWebRTCRunnerArguments

# Import the bot
from bot import run_bot, transport_params

# FastAPI app
app = FastAPI(title="Avatar Conversation")

# Store connections by pc_id
pcs_map: Dict[str, SmallWebRTCConnection] = {}

# ICE servers for WebRTC - empty for localhost (direct connection)
# STUN servers can cause issues when client and server are on same machine
ice_servers = []

# Avatar storage
current_avatar_bytes: Optional[bytes] = None
avatar_renderer = None

# Uploads directory
UPLOADS_DIR = script_dir / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)


# =============================================================================
# Custom HTML with Video and Avatar Upload
# =============================================================================

CUSTOM_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Avatar Conversation</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
            display: flex;
            flex-direction: column;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        h1 { text-align: center; font-size: 2rem; margin-bottom: 10px; }
        h2 { font-size: 1.2rem; margin-bottom: 15px; color: #aaa; }
        .main-content {
            display: grid;
            grid-template-columns: 300px 1fr 350px;
            gap: 20px;
            flex: 1;
        }
        .panel {
            background: rgba(0,0,0,0.3);
            border-radius: 12px;
            padding: 20px;
        }
        
        /* Avatar Upload Section */
        .upload-section { display: flex; flex-direction: column; }
        .upload-area {
            border: 2px dashed #4a90d9;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s;
            margin-bottom: 15px;
        }
        .upload-area:hover { border-color: #6bb0f9; background: rgba(74, 144, 217, 0.1); }
        .upload-area.dragover { border-color: #2ecc71; background: rgba(46, 204, 113, 0.1); }
        .upload-preview {
            width: 100%;
            aspect-ratio: 1;
            background: #000;
            border-radius: 8px;
            overflow: hidden;
            margin-bottom: 15px;
        }
        .upload-preview img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        .upload-status { font-size: 0.9rem; color: #888; }
        .upload-status.success { color: #2ecc71; }
        .upload-status.error { color: #e74c3c; }
        
        /* Video Section */
        .video-section { display: flex; flex-direction: column; align-items: center; }
        .video-container {
            width: 100%;
            max-width: 512px;
            aspect-ratio: 1;
            background: #000;
            border-radius: 8px;
            overflow: hidden;
            position: relative;
        }
        #remote-video {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        .video-placeholder {
            width: 100%;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #666;
            font-size: 1.2rem;
        }
        .controls {
            margin-top: 20px;
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            justify-content: center;
        }
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.2s;
        }
        .btn-primary { background: #4a90d9; color: white; }
        .btn-primary:hover { background: #3a7bc8; }
        .btn-primary:disabled { background: #666; cursor: not-allowed; }
        .btn-danger { background: #e74c3c; color: white; }
        .btn-danger:hover { background: #c0392b; }
        .btn-danger:disabled { background: #666; cursor: not-allowed; }
        
        /* Status */
        .status {
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.9rem;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 15px;
        }
        .status.disconnected { background: rgba(231, 76, 60, 0.3); }
        .status.connecting { background: rgba(241, 196, 15, 0.3); }
        .status.connected { background: rgba(46, 204, 113, 0.3); }
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
        }
        .disconnected .status-dot { background: #e74c3c; }
        .connecting .status-dot { background: #f1c40f; animation: pulse 1s infinite; }
        .connected .status-dot { background: #2ecc71; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        
        /* Chat Section */
        .chat-section { display: flex; flex-direction: column; }
        .chat-history {
            flex: 1;
            overflow-y: auto;
            margin-bottom: 15px;
            padding: 10px;
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
            min-height: 300px;
            max-height: 500px;
        }
        .message {
            margin-bottom: 10px;
            padding: 10px;
            border-radius: 8px;
        }
        .message.user { background: rgba(74, 144, 217, 0.3); margin-left: 20%; }
        .message.assistant { background: rgba(255, 255, 255, 0.1); margin-right: 20%; }
        .message.system { background: rgba(241, 196, 15, 0.2); text-align: center; font-size: 0.9rem; }
        
        /* Audio Meter */
        .audio-meter {
            height: 4px;
            background: #333;
            border-radius: 2px;
            margin-top: 10px;
            overflow: hidden;
        }
        .audio-meter-fill {
            height: 100%;
            background: linear-gradient(90deg, #2ecc71, #f1c40f, #e74c3c);
            width: 0%;
            transition: width 0.1s;
        }
        
        @media (max-width: 1200px) {
            .main-content { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎭 Avatar Conversation</h1>
        
        <div class="main-content">
            <!-- Left: Avatar Upload -->
            <div class="panel upload-section">
                <h2>📷 Avatar Image</h2>
                <div class="upload-preview" id="upload-preview">
                    <div class="video-placeholder">No avatar</div>
                </div>
                <div class="upload-area" id="upload-area">
                    <input type="file" id="file-input" accept="image/*" hidden>
                    <p>📁 Click or drag image</p>
                    <small>PNG, JPG (512×512 recommended)</small>
                </div>
                <div class="upload-status" id="upload-status"></div>
            </div>
            
            <!-- Center: Video Display -->
            <div class="panel video-section">
                <div class="status disconnected" id="status">
                    <span class="status-dot"></span>
                    <span id="status-text">Disconnected</span>
                </div>
                
                <div class="video-container">
                    <video id="remote-video" autoplay playsinline></video>
                </div>
                
                <div class="audio-meter">
                    <div class="audio-meter-fill" id="audio-meter"></div>
                </div>
                
                <div class="controls">
                    <button id="connect-btn" class="btn btn-primary">🎙️ Connect</button>
                    <button id="disconnect-btn" class="btn btn-danger" disabled>Disconnect</button>
                </div>
            </div>
            
            <!-- Right: Chat -->
            <div class="panel chat-section">
                <h2>💬 Conversation</h2>
                <div id="chat-history" class="chat-history">
                    <div class="message system">
                        Upload an avatar image and click "Connect" to start
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Elements
        const statusEl = document.getElementById('status');
        const statusText = document.getElementById('status-text');
        const connectBtn = document.getElementById('connect-btn');
        const disconnectBtn = document.getElementById('disconnect-btn');
        const remoteVideo = document.getElementById('remote-video');
        const chatHistory = document.getElementById('chat-history');
        const uploadArea = document.getElementById('upload-area');
        const fileInput = document.getElementById('file-input');
        const uploadPreview = document.getElementById('upload-preview');
        const uploadStatus = document.getElementById('upload-status');
        const audioMeter = document.getElementById('audio-meter');
        
        // State
        let pc = null;
        let localStream = null;
        let sessionId = null;
        let audioContext = null;
        let analyser = null;
        
        // Status helpers
        function setStatus(state, text) {
            statusEl.className = 'status ' + state;
            statusText.textContent = text;
        }
        
        function addMessage(role, content) {
            const div = document.createElement('div');
            div.className = 'message ' + role;
            div.textContent = content;
            chatHistory.appendChild(div);
            chatHistory.scrollTop = chatHistory.scrollHeight;
        }
        
        function showUploadStatus(msg, type = '') {
            uploadStatus.textContent = msg;
            uploadStatus.className = 'upload-status ' + type;
        }
        
        // Avatar upload
        uploadArea.addEventListener('click', () => fileInput.click());
        
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            if (e.dataTransfer.files.length > 0) {
                uploadAvatar(e.dataTransfer.files[0]);
            }
        });
        
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                uploadAvatar(e.target.files[0]);
            }
        });
        
        async function uploadAvatar(file) {
            showUploadStatus('Uploading...', '');
            
            try {
                const formData = new FormData();
                formData.append('file', file);
                
                const resp = await fetch('/upload-avatar', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await resp.json();
                
                if (data.success) {
                    showUploadStatus('Avatar uploaded!', 'success');
                    
                    // Show preview
                    const reader = new FileReader();
                    reader.onload = (e) => {
                        uploadPreview.innerHTML = `<img src="${e.target.result}" alt="Avatar">`;
                    };
                    reader.readAsDataURL(file);
                } else {
                    showUploadStatus(data.message || 'Upload failed', 'error');
                }
            } catch (err) {
                showUploadStatus('Error: ' + err.message, 'error');
            }
        }
        
        // Audio meter
        function updateAudioMeter() {
            if (!analyser) {
                requestAnimationFrame(updateAudioMeter);
                return;
            }
            
            const dataArray = new Uint8Array(analyser.frequencyBinCount);
            analyser.getByteFrequencyData(dataArray);
            const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
            audioMeter.style.width = Math.min(100, average * 2) + '%';
            
            requestAnimationFrame(updateAudioMeter);
        }
        updateAudioMeter();
        
        // WebRTC Connection
        async function connect() {
            setStatus('connecting', 'Connecting...');
            connectBtn.disabled = true;
            
            try {
                // Get microphone
                localStream = await navigator.mediaDevices.getUserMedia({ 
                    audio: {
                        echoCancellation: true,
                        noiseSuppression: true,
                        autoGainControl: true
                    },
                    video: false
                });
                
                // Setup audio analyzer
                audioContext = new (window.AudioContext || window.webkitAudioContext)();
                const source = audioContext.createMediaStreamSource(localStream);
                analyser = audioContext.createAnalyser();
                analyser.fftSize = 256;
                source.connect(analyser);
                
                // Create peer connection - no ICE servers for localhost
                // (STUN servers can cause issues when client and server are on same machine)
                pc = new RTCPeerConnection({
                    iceServers: []
                });
                
                // Add local audio track
                localStream.getAudioTracks().forEach(track => {
                    pc.addTrack(track, localStream);
                });
                
                // Add transceivers for receiving video and audio
                pc.addTransceiver('video', { direction: 'recvonly' });
                pc.addTransceiver('video', { direction: 'recvonly' });  // screen share placeholder
                pc.addTransceiver('audio', { direction: 'sendrecv' });
                
                // Handle incoming tracks
                pc.ontrack = (event) => {
                    console.log('Got track:', event.track.kind, event.streams);
                    if (event.track.kind === 'video' && event.streams[0]) {
                        remoteVideo.srcObject = event.streams[0];
                    }
                    if (event.track.kind === 'audio' && event.streams[0]) {
                        const audio = new Audio();
                        audio.srcObject = event.streams[0];
                        audio.play().catch(e => console.log('Audio play error:', e));
                    }
                };
                
                // Monitor connection state
                pc.onconnectionstatechange = () => {
                    console.log('Connection state:', pc.connectionState);
                    if (pc.connectionState === 'connected') {
                        setStatus('connected', 'Connected');
                        addMessage('system', 'Connected! Start speaking...');
                    } else if (pc.connectionState === 'failed' || pc.connectionState === 'disconnected') {
                        setStatus('disconnected', 'Connection lost');
                    }
                };
                
                pc.oniceconnectionstatechange = () => {
                    console.log('ICE state:', pc.iceConnectionState);
                };
                
                // Create offer
                const offer = await pc.createOffer();
                await pc.setLocalDescription(offer);
                
                // Wait for ICE gathering to complete (with timeout)
                await new Promise((resolve) => {
                    if (pc.iceGatheringState === 'complete') {
                        resolve();
                    } else {
                        const checkState = () => {
                            if (pc.iceGatheringState === 'complete') {
                                pc.removeEventListener('icegatheringstatechange', checkState);
                                resolve();
                            }
                        };
                        pc.addEventListener('icegatheringstatechange', checkState);
                        // Timeout fallback after 3 seconds
                        setTimeout(resolve, 3000);
                    }
                });
                
                // Send offer directly to /api/offer (simplified pattern)
                const offerResp = await fetch('/api/offer', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        sdp: pc.localDescription.sdp,
                        type: pc.localDescription.type
                    })
                });
                const answerData = await offerResp.json();
                console.log('Got answer:', answerData);
                
                // Store pc_id for potential renegotiation
                sessionId = answerData.pc_id;
                
                // Set remote description
                await pc.setRemoteDescription(new RTCSessionDescription({
                    type: answerData.type,
                    sdp: answerData.sdp
                }));
                
                setStatus('connecting', 'Establishing connection...');
                disconnectBtn.disabled = false;
                
            } catch (error) {
                console.error('Connection error:', error);
                setStatus('disconnected', 'Error: ' + error.message);
                connectBtn.disabled = false;
                addMessage('system', 'Connection failed: ' + error.message);
            }
        }
        
        function disconnect() {
            if (pc) {
                pc.close();
                pc = null;
            }
            if (localStream) {
                localStream.getTracks().forEach(track => track.stop());
                localStream = null;
            }
            if (audioContext) {
                audioContext.close();
                audioContext = null;
                analyser = null;
            }
            remoteVideo.srcObject = null;
            setStatus('disconnected', 'Disconnected');
            connectBtn.disabled = false;
            disconnectBtn.disabled = true;
            addMessage('system', 'Disconnected');
        }
        
        connectBtn.addEventListener('click', connect);
        disconnectBtn.addEventListener('click', disconnect);
        
        // Load existing avatar on page load
        async function loadExistingAvatar() {
            try {
                const resp = await fetch('/current-avatar');
                const data = await resp.json();
                if (data.avatar) {
                    uploadPreview.innerHTML = `<img src="${data.avatar}" alt="Avatar">`;
                    showUploadStatus('Avatar loaded', 'success');
                }
            } catch (e) {
                console.log('No existing avatar');
            }
        }
        loadExistingAvatar();
    </script>
</body>
</html>
"""


# =============================================================================
# Routes
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the custom HTML with video."""
    return HTMLResponse(content=CUSTOM_HTML)


@app.post("/api/offer")
async def offer(request: dict, background_tasks: BackgroundTasks):
    """Handle WebRTC offer - simplified pattern matching foundational example."""
    pc_id = request.get("pc_id")

    if pc_id and pc_id in pcs_map:
        pipecat_connection = pcs_map[pc_id]
        logger.info(f"Reusing existing connection for pc_id: {pc_id}")
        await pipecat_connection.renegotiate(
            sdp=request["sdp"],
            type=request["type"],
            restart_pc=request.get("restart_pc", False),
        )
    else:
        pipecat_connection = SmallWebRTCConnection(ice_servers)
        await pipecat_connection.initialize(sdp=request["sdp"], type=request["type"])

        @pipecat_connection.event_handler("closed")
        async def handle_disconnected(webrtc_connection: SmallWebRTCConnection):
            logger.info(f"Discarding peer connection for pc_id: {webrtc_connection.pc_id}")
            pcs_map.pop(webrtc_connection.pc_id, None)

        # Run bot with the connection
        async def run_bot_task(connection: SmallWebRTCConnection):
            params = transport_params["webrtc"]()
            transport = SmallWebRTCTransport(
                webrtc_connection=connection,
                params=params,
            )
            
            runner_args = SmallWebRTCRunnerArguments(
                webrtc_connection=connection,
                body=request,
            )
            
            await run_bot(transport, runner_args)
        
        background_tasks.add_task(run_bot_task, pipecat_connection)

    answer = pipecat_connection.get_answer()
    # Update the peer connection in the map
    pcs_map[answer["pc_id"]] = pipecat_connection

    return answer


# =============================================================================
# Avatar Upload Endpoints
# =============================================================================

@app.post("/upload-avatar")
async def upload_avatar(file: UploadFile = File(...)):
    """Upload an avatar image."""
    global current_avatar_bytes, avatar_renderer
    
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            return JSONResponse({
                "success": False,
                "message": "Please upload an image file (PNG, JPG)"
            }, status_code=400)
        
        # Read the file
        content = await file.read()
        
        if len(content) > 10 * 1024 * 1024:  # 10MB limit
            return JSONResponse({
                "success": False,
                "message": "File too large (max 10MB)"
            }, status_code=400)
        
        # Save to uploads directory
        file_path = UPLOADS_DIR / f"avatar_{uuid.uuid4().hex}.png"
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Store in memory
        current_avatar_bytes = content
        
        # Update the avatar processor if it exists
        try:
            from avatar_processor import AvatarRenderer
            # Create/update the global avatar renderer
            avatar_renderer = AvatarRenderer()
            avatar_renderer.load_image(str(file_path))
            
            # Store path for bot to pick up
            avatar_path_file = script_dir / ".current_avatar_path"
            with open(avatar_path_file, "w") as f:
                f.write(str(file_path))
            
            logger.info(f"Avatar uploaded and loaded: {file_path}")
        except Exception as e:
            logger.warning(f"Could not update avatar processor: {e}")
        
        return JSONResponse({
            "success": True,
            "message": "Avatar uploaded successfully",
            "path": str(file_path)
        })
        
    except Exception as e:
        logger.error(f"Avatar upload error: {e}")
        return JSONResponse({
            "success": False,
            "message": str(e)
        }, status_code=500)


@app.get("/current-avatar")
async def get_current_avatar():
    """Get the current avatar as base64."""
    global current_avatar_bytes
    
    # Check for saved avatar path
    avatar_path_file = script_dir / ".current_avatar_path"
    if avatar_path_file.exists():
        try:
            with open(avatar_path_file, "r") as f:
                path = f.read().strip()
            if Path(path).exists():
                with open(path, "rb") as f:
                    current_avatar_bytes = f.read()
        except Exception as e:
            logger.warning(f"Could not load saved avatar: {e}")
    
    if current_avatar_bytes:
        b64 = base64.b64encode(current_avatar_bytes).decode('utf-8')
        return JSONResponse({
            "avatar": f"data:image/png;base64,{b64}"
        })
    
    return JSONResponse({"avatar": None})


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 60)
    print("  Avatar Conversation with Video")
    print("=" * 60)
    print()
    print("  Open http://localhost:7860 in your browser")
    print()
    print("=" * 60)
    
    uvicorn.run(
        "run_avatar:app",
        host="0.0.0.0",
        port=7860,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
