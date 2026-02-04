"""
Avatar Conversation Backend - Phase 1.2
Real-time conversational AI pipeline with speech-to-speech capabilities.

Architecture:
    Audio Input → STT (Groq) → LLM (Ollama) → TTS (Groq) → Audio Output

Features:
    - Real-time speech-to-speech conversation
    - Voice activity detection (VAD)
    - Context-aware responses
    - Interruption handling

Usage:
    python backend.py

Environment variables:
    GROQ_API_KEY=your_groq_api_key
    OLLAMA_BASE_URL=http://localhost:11434 (default)
    OLLAMA_MODEL=mistral:7b (default)
"""

import asyncio
import logging
import os
import sys
import yaml
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """
    Main function to run the conversational AI pipeline.
    
    This creates a simple speech-to-speech conversation system:
    1. Listen to microphone input
    2. Convert speech to text (Groq STT)
    3. Generate response with LLM (Ollama)
    4. Convert response to speech (Groq TTS)
    5. Play audio output
    """
    logger.info("=" * 70)
    logger.info("🎙️  AVATAR CONVERSATION PIPELINE - Phase 1.2")
    logger.info("=" * 70)
    logger.info("")
    logger.info("Components:")
    logger.info("  ✓ STT: Groq Whisper (speech-to-text)")
    logger.info("  ✓ LLM: Ollama Mistral 7B (local)")
    logger.info("  ✓ TTS: Groq (text-to-speech)")
    logger.info("  ⏳ Avatar: Coming in Phase 2")
    logger.info("")
    logger.info("=" * 70)
    
    # Validate environment
    logger.info("\n[1/5] Validating environment...")
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.error("    ✗ GROQ_API_KEY not found in environment")
        logger.error("    Please set it in .env file or export it")
        return
    logger.info("    ✓ GROQ_API_KEY found")
    
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "mistral:7b")
    logger.info(f"    ✓ Ollama URL: {ollama_url}")
    logger.info(f"    ✓ Ollama Model: {ollama_model}")
    
    # Load configuration
    logger.info("\n[2/5] Loading configuration...")
    config_path = Path(__file__).parent / "config.yaml"
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"    ✓ Configuration loaded from {config_path}")
    except Exception as e:
        logger.error(f"    ✗ Failed to load configuration: {e}")
        return
    
    # Initialize services
    logger.info("\n[3/5] Initializing AI services...")
    
    try:
        # Import Pipecat components
        from pipecat.services.groq import GroqSTTService, GroqTTSService
        from pipecat.services.ollama import OLLamaLLMService
        from pipecat.audio.vad.silero import SileroVADAnalyzer
        from pipecat.pipeline.pipeline import Pipeline
        from pipecat.pipeline.runner import PipelineRunner
        from pipecat.pipeline.task import PipelineParams, PipelineTask
        from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
        from pipecat.transports.services.daily import DailyParams, DailyTransport
        from pipecat.frames.frames import TextFrame, EndFrame
        
        logger.info("    ✓ Pipecat components imported")
    except ImportError as e:
        logger.error(f"    ✗ Failed to import Pipecat: {e}")
        logger.error("    Run: pip install pipecat-ai[daily,groq,ollama,silero]")
        return
    
    # STT Service
    logger.info("    [3a] Setting up STT (Groq Whisper)...")
    stt = GroqSTTService(
        api_key=api_key,
        model=config['stt']['groq']['model'],
    )
    logger.info("        ✓ Groq STT ready")
    
    # LLM Service  
    logger.info("    [3b] Setting up LLM (Ollama)...")
    llm = OLLamaLLMService(
        base_url=ollama_url,
        model=ollama_model,
    )
    logger.info("        ✓ Ollama LLM ready")
    
    # TTS Service
    logger.info("    [3c] Setting up TTS (Groq)...")
    tts = GroqTTSService(
        api_key=api_key,
        voice="sage",  # Available voices: alloy, echo, fable, onyx, nova, shimmer, sage
    )
    logger.info("        ✓ Groq TTS ready")
    
    # VAD Analyzer
    logger.info("    [3d] Setting up VAD (Voice Activity Detection)...")
    vad_config = config['vad']['silero']
    vad = SileroVADAnalyzer(
        params=SileroVADAnalyzer.Params(
            min_volume=vad_config['threshold'],
            start_secs=vad_config['start_secs'],
            stop_secs=vad_config['stop_secs'],
        )
    )
    logger.info("        ✓ Silero VAD ready")
    
    # Context Manager
    logger.info("    [3e] Setting up conversation context...")
    system_prompt = config['llm']['ollama']['system_prompt']
    context = OpenAILLMContext(
        messages=[
            {"role": "system", "content": system_prompt}
        ]
    )
    context_aggregator = llm.create_context_aggregator(context)
    logger.info("        ✓ Context aggregator ready")
    
    # Transport (using Daily.co for simplicity - can switch to local later)
    logger.info("\n[4/5] Initializing transport...")
    logger.info("    Note: Using Daily.co transport for audio I/O")
    logger.info("    You'll get a room URL to join in your browser")
    
    transport = DailyTransport(
        room_url="",  # Will auto-create a room
        token="",
        bot_name="AI Assistant",
        params=DailyParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_enabled=True,
            vad_analyzer=vad,
        )
    )
    logger.info("    ✓ Transport initialized")
    
    # Build pipeline
    logger.info("\n[5/5] Building conversational pipeline...")
    pipeline = Pipeline([
        transport.input(),           # Audio input
        stt,                         # Speech → Text
        context_aggregator.user(),   # Add user message to context
        llm,                         # Generate response
        tts,                         # Text → Speech
        transport.output(),          # Audio output
        context_aggregator.assistant(),  # Add assistant message to context
    ])
    logger.info("    ✓ Pipeline built")
    
    # Create task
    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=config['pipeline']['interruption_enabled'],
            enable_metrics=True,
            enable_usage_metrics=True,
        )
    )
    
    # Initialize runner
    runner = PipelineRunner()
    
    # Display info
    logger.info("\n" + "=" * 70)
    logger.info("🚀 PIPELINE READY!")
    logger.info("=" * 70)
    logger.info("\nStarting conversation...")
    logger.info("The system will:")
    logger.info("  1. Create a Daily.co room")
    logger.info("  2. Print the room URL")
    logger.info("  3. Wait for you to join via browser")
    logger.info("  4. Start listening and responding to your voice")
    logger.info("\nPress Ctrl+C to stop the conversation")
    logger.info("=" * 70)
    
    try:
        # Send greeting
        await task.queue_frame(
            TextFrame("Hello! I'm your AI assistant. How can I help you today?")
        )
        
        # Run the pipeline
        await runner.run(task)
        
    except KeyboardInterrupt:
        logger.info("\n\n" + "=" * 70)
        logger.info("🛑 Shutting down gracefully...")
        logger.info("=" * 70)
    except Exception as e:
        logger.error(f"\n❌ Error: {e}", exc_info=True)
    finally:
        # Cleanup
        await task.queue_frame(EndFrame())
        await runner.stop()
        logger.info("\n✓ Pipeline stopped. Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())
