#!/usr/bin/env python3
"""
Avatar Conversation Bot - Pipecat Pipeline
===========================================
Continuous interruptible conversation with lip-synced avatar.

Features:
- Upload a character image
- Real-time lip-sync animation based on TTS audio
- WebRTC transport for browser-based interaction

Usage:
    python bot.py -t webrtc
    Then open the provided URL in your browser.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

# Load .env from the same directory as this script
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
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.transports.websocket.fastapi import FastAPIWebsocketParams
from pipecat.turns.user_turn_strategies import UserTurnStrategies

# Try to import smart turn analyzer for better interruption handling
try:
    from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
    from pipecat.turns.user_stop import TurnAnalyzerUserTurnStopStrategy
    HAS_SMART_TURN = True
except ImportError:
    HAS_SMART_TURN = False
    logger.warning("Smart turn analyzer not available. Install with: pip install pipecat-ai[local-smart-turn-v3]")

# Services - using Groq and Ollama (local/free options)
from pipecat.services.groq.stt import GroqSTTService
from pipecat.services.groq.tts import GroqTTSService
from pipecat.services.ollama.llm import OLLamaLLMService

# Try to import Piper for local TTS (much faster, no network latency)
try:
    from pipecat.services.piper.tts import PiperTTSService
    HAS_PIPER = True
except ImportError:
    HAS_PIPER = False

# Import avatar processor for lip-sync
try:
    from avatar_processor import AvatarRenderer, SimpleLipSyncProcessor
    HAS_AVATAR = True
except ImportError:
    HAS_AVATAR = False
    logger.warning("Avatar processor not available - run from avatar_conversation directory")

# =============================================================================
# Configuration
# =============================================================================

SYSTEM_PROMPT = """You are a friendly AI avatar assistant. You are having a natural 
voice conversation with the user. Keep your responses concise and conversational 
since they will be spoken aloud. Avoid using special characters, emojis, or 
bullet points. Be helpful, warm, and engaging."""

# Transport parameters for different modes
transport_params = {
    "twilio": lambda: FastAPIWebsocketParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
    ),
    "webrtc": lambda: TransportParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        video_out_enabled=True,  # Enable video output for avatar
        video_out_width=512,
        video_out_height=512,
    ),
}


# =============================================================================
# Custom Processors
# =============================================================================

class TranscriptionLogger(FrameProcessor):
    """Logs transcriptions for debugging."""
    
    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        
        # Log transcription frames
        frame_name = type(frame).__name__
        if "Transcription" in frame_name:
            logger.info(f"📝 {frame}")
        
        await self.push_frame(frame, direction)


# =============================================================================
# Bot Implementation
# =============================================================================

async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    """Run the avatar conversation bot with pipecat pipeline."""
    logger.info("Starting Avatar Conversation Bot")
    
    # -------------------------------------------------------------------------
    # Initialize Services
    # -------------------------------------------------------------------------
    
    # STT: Groq Whisper (fast, accurate)
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        logger.warning("GROQ_API_KEY not set - STT/TTS will not work")
        logger.warning("Get a free key at: https://console.groq.com/keys")
    
    stt = GroqSTTService(api_key=groq_api_key) if groq_api_key else None
    
    # TTS: Use Groq (Piper has compatibility issues with Python 3.13)
    tts = None
    if groq_api_key:
        tts = GroqTTSService(
            api_key=groq_api_key,
        )
        logger.info("TTS: Groq (cloud)")
    
    if tts is None:
        logger.warning("No TTS available - set GROQ_API_KEY")
    
    # LLM: Ollama (local, free)
    ollama_model = os.getenv("OLLAMA_MODEL", "mistral")
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    logger.info(f"[DEBUG] OLLAMA_BASE_URL from env: {ollama_base_url}")
    
    llm = OLLamaLLMService(
        model=ollama_model,
        base_url=ollama_base_url,
    )
    logger.info(f"LLM: Ollama ({ollama_model}) at {ollama_base_url}")
    
    # Avatar: Lip-sync processor for animated avatar
    avatar_renderer = None
    avatar_image_path = os.getenv("AVATAR_IMAGE", None)
    
    # Check for uploaded avatar from web interface
    uploaded_avatar_path = script_dir / ".current_avatar_path"
    if uploaded_avatar_path.exists():
        try:
            with open(uploaded_avatar_path, "r") as f:
                saved_path = f.read().strip()
            if Path(saved_path).exists():
                avatar_image_path = saved_path
                logger.info(f"Using uploaded avatar: {saved_path}")
        except Exception as e:
            logger.warning(f"Could not load uploaded avatar path: {e}")
    
    if HAS_AVATAR:
        avatar_renderer = AvatarRenderer(
            avatar_image_path=avatar_image_path,
            fps=25,
            output_size=(512, 512),
        )
        if avatar_image_path:
            logger.info(f"Avatar: Loaded from {avatar_image_path}")
        else:
            logger.info("Avatar: Ready (upload image via web interface)")
    else:
        logger.warning("Avatar processor not available")
    
    # Transcription logger
    transcription_logger = TranscriptionLogger()
    
    # -------------------------------------------------------------------------
    # Context and Aggregators
    # -------------------------------------------------------------------------
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]
    
    context = LLMContext(messages)
    
    # Build user turn strategies based on available features
    if HAS_SMART_TURN:
        # Use smart turn analyzer for intelligent end-of-turn detection
        user_turn_strategies = UserTurnStrategies(
            stop=[TurnAnalyzerUserTurnStopStrategy(
                turn_analyzer=LocalSmartTurnAnalyzerV3()
            )]
        )
        logger.info("✓ Using Smart Turn Analyzer for natural conversation flow")
    else:
        user_turn_strategies = None
        logger.info("Using basic VAD for turn detection")
    
    # Create context aggregators with VAD for natural turn-taking
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            user_turn_strategies=user_turn_strategies,
            # Use Silero VAD for voice activity detection
            vad_analyzer=SileroVADAnalyzer(
                params=VADParams(
                    stop_secs=0.2,  # Quick response after speech stops
                )
            ),
        ),
    )
    
    # -------------------------------------------------------------------------
    # Build Pipeline
    # -------------------------------------------------------------------------
    
    if stt and tts:
        # Build pipeline processors list
        processors = [
            transport.input(),       # Audio/video from user
            stt,                     # Speech to text
            transcription_logger,   # Log what user said
            user_aggregator,        # Collect user messages
            llm,                    # Generate response
            tts,                    # Text to speech
        ]
        
        # Add avatar processor if available
        if avatar_renderer:
            processors.append(avatar_renderer)
            logger.info("✓ Full pipeline: STT → LLM → TTS → Avatar")
        else:
            logger.info("✓ Full pipeline: STT → LLM → TTS")
        
        processors.extend([
            transport.output(),     # Audio/video to user
            assistant_aggregator,   # Track assistant responses
        ])
        
        pipeline = Pipeline(processors)
    else:
        # Minimal pipeline (no audio, just LLM)
        logger.warning("Running without STT/TTS - set GROQ_API_KEY for voice")
        pipeline = Pipeline([
            transport.input(),
            user_aggregator,
            llm,
            transport.output(),
            assistant_aggregator,
        ])
    
    # -------------------------------------------------------------------------
    # Create Task
    # -------------------------------------------------------------------------
    
    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
            allow_interruptions=True,  # Enable interruptions!
        ),
        idle_timeout_secs=runner_args.pipeline_idle_timeout_secs,
    )
    
    # -------------------------------------------------------------------------
    # Event Handlers
    # -------------------------------------------------------------------------
    
    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("👤 Client connected")
        # Start the conversation with a greeting
        messages.append({
            "role": "system", 
            "content": "Greet the user warmly and ask how you can help them today."
        })
        await task.queue_frames([LLMRunFrame()])
    
    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("👤 Client disconnected")
        await task.cancel()
    
    # -------------------------------------------------------------------------
    # Run Pipeline
    # -------------------------------------------------------------------------
    
    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)
    
    logger.info("=" * 50)
    logger.info("Avatar Conversation Bot Ready!")
    logger.info("=" * 50)
    
    await runner.run(task)


# =============================================================================
# Entry Point
# =============================================================================

async def bot(runner_args: RunnerArguments):
    """Main bot entry point compatible with Pipecat runner."""
    transport = await create_transport(runner_args, transport_params)
    await run_bot(transport, runner_args)


if __name__ == "__main__":
    from pipecat.runner.run import main
    
    print("=" * 60)
    print("  Avatar Conversation Bot (Pipecat)")
    print("=" * 60)
    print("")
    print("  Usage:")
    print("    python bot.py -t webrtc     # Browser-based (recommended)")
    print("    python bot.py -t twilio     # Twilio integration")
    print("")
    print("  Requirements:")
    print("    - GROQ_API_KEY in .env (for STT/TTS)")
    print("    - Ollama running locally (for LLM)")
    print("")
    print("=" * 60)
    
    main()
