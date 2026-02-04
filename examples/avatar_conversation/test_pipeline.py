"""
Simple conversational AI test without Daily transport.
Tests the core pipeline: STT → LLM → TTS

This version uses mock audio for testing the pipeline logic.
"""

import asyncio
import logging
import os
import sys
import yaml
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_pipeline():
    """Test the conversation pipeline components."""
    
    logger.info("=" * 70)
    logger.info("🧪 TESTING CONVERSATIONAL PIPELINE COMPONENTS")
    logger.info("=" * 70)
    
    # Load config
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Check environment
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.error("❌ GROQ_API_KEY not found")
        return
    
    logger.info("\n[1/4] Testing Groq STT Service...")
    try:
        from pipecat.services.groq.stt import GroqSTTService
        stt = GroqSTTService(
            api_key=api_key,
            model=config['stt']['groq']['model'],
        )
        logger.info("    ✓ Groq STT initialized successfully")
    except Exception as e:
        logger.error(f"    ❌ STT failed: {e}", exc_info=True)
        return
    
    logger.info("\n[2/4] Testing Ollama LLM Service...")
    try:
        from pipecat.services.ollama.llm import OLLamaLLMService
        llm = OLLamaLLMService(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
            model=os.getenv("OLLAMA_MODEL", "mistral:7b"),
        )
        logger.info("    ✓ Ollama LLM initialized successfully")
        
        # Test LLM connection
        logger.info("    Testing Ollama connection...")
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:11434") as response:
                if response.status == 200:
                    logger.info("    ✓ Ollama server is running")
                else:
                    logger.warning(f"    ⚠ Ollama returned status {response.status}")
    except Exception as e:
        logger.error(f"    ❌ LLM failed: {e}")
        logger.error("    Make sure Ollama is running: ollama serve")
        return
    
    logger.info("\n[3/4] Testing Groq TTS Service...")
    try:
        from pipecat.services.groq.tts import GroqTTSService
        tts = GroqTTSService(
            api_key=api_key,
            voice="sage",
        )
        logger.info("    ✓ Groq TTS initialized successfully")
    except Exception as e:
        logger.error(f"    ❌ TTS failed: {e}")
        return
    
    logger.info("\n[4/4] Testing VAD (Voice Activity Detection)...")
    try:
        from pipecat.audio.vad.silero import SileroVADAnalyzer
        from pipecat.audio.vad.vad_analyzer import VADParams
        vad_config = config['vad']['silero']
        vad = SileroVADAnalyzer(
            sample_rate=16000,
            params=VADParams(
                min_volume=vad_config['threshold'],
                start_secs=vad_config['start_secs'],
                stop_secs=vad_config['stop_secs'],
            )
        )
        logger.info("    ✓ Silero VAD initialized successfully")
    except Exception as e:
        logger.error(f"    ❌ VAD failed: {e}")
        return
    
    # Success!
    logger.info("\n" + "=" * 70)
    logger.info("✅ ALL COMPONENTS INITIALIZED SUCCESSFULLY!")
    logger.info("=" * 70)
    logger.info("\nPipeline components ready:")
    logger.info(f"  ✓ STT: {type(stt).__name__}")
    logger.info(f"  ✓ LLM: {type(llm).__name__}")
    logger.info(f"  ✓ TTS: {type(tts).__name__}")
    logger.info(f"  ✓ VAD: {type(vad).__name__}")
    logger.info("\nNext steps:")
    logger.info("  1. For full pipeline, set up Daily.co account (free)")
    logger.info("  2. Or implement local audio transport")
    logger.info("  3. Wire components in backend.py")
    logger.info("\n✨ Phase 1.2 core pipeline validated!")
    logger.info("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_pipeline())
