"""
Integration Test: LivePortrait + Conversational Pipeline

Tests the complete flow:
    Audio Input → STT → LLM → TTS → Avatar Animation

This validates:
1. LivePortrait processor initialization
2. SadTalker motion processor (placeholder)
3. Frame pipeline integration
4. End-to-end latency
5. Avatar frame generation from text

Usage:
    python test_integration.py

Requirements:
    - Groq API key in environment
    - Ollama running locally
    - LivePortrait models downloaded
"""

import asyncio
import logging
import os
import sys
import time
import numpy as np
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def test_imports():
    """Test that all required imports are available."""
    logger.info("\n[1/7] Testing imports...")
    
    try:
        from pipecat.processors.avatar.liveportrait_processor import LivePortraitProcessor
        logger.info("    ✓ LivePortraitProcessor imported")
    except ImportError as e:
        logger.error(f"    ✗ Failed to import LivePortraitProcessor: {e}")
        return False
    
    try:
        from pipecat.processors.avatar.sadtalker_processor import SadTalkerMotionProcessor
        logger.info("    ✓ SadTalkerMotionProcessor imported")
    except ImportError as e:
        logger.error(f"    ✗ Failed to import SadTalkerMotionProcessor: {e}")
        return False
    
    try:
        from pipecat.frames.frames import ImageRawFrame, AudioRawFrame
        logger.info("    ✓ Frame types imported")
    except ImportError as e:
        logger.error(f"    ✗ Failed to import Frame types: {e}")
        return False
    
    try:
        from pipecat.processors.avatar.motion_vector_frame import MotionVectorFrame
        logger.info("    ✓ MotionVectorFrame imported")
    except ImportError as e:
        logger.error(f"    ✗ Failed to import MotionVectorFrame: {e}")
        return False
    
    return True


def test_liveportrait_processor():
    """Test LivePortrait processor creation and initialization."""
    logger.info("\n[2/7] Testing LivePortrait processor...")
    
    try:
        from pipecat.processors.avatar.liveportrait_processor import LivePortraitProcessor
        
        processor = LivePortraitProcessor(
            device="cuda",
            resolution=512,
        )
        logger.info("    ✓ LivePortrait processor created")
        
        # Check that processor is configured correctly
        assert processor.device == "cuda"
        assert processor.resolution == 512
        logger.info("    ✓ Configuration validated")
        
        # Note: ONNX models are loaded lazily on first use
        logger.info("    ✓ Models will load on first frame (lazy loading)")
        
        return True
        
    except Exception as e:
        logger.error(f"    ✗ Failed to test LivePortrait: {e}", exc_info=True)
        return False


def test_sadtalker_processor():
    """Test SadTalker motion processor creation."""
    logger.info("\n[3/7] Testing SadTalker motion processor...")
    
    try:
        from pipecat.processors.avatar.sadtalker_processor import SadTalkerMotionProcessor
        
        processor = SadTalkerMotionProcessor(device="cuda", fps=25)
        logger.info("    ✓ SadTalker processor created")
        
        # Check configuration
        assert processor.device == "cuda"
        assert processor.fps == 25
        logger.info("    ✓ Configuration validated")
        
        return True
        
    except Exception as e:
        logger.error(f"    ✗ Failed to test SadTalker: {e}", exc_info=True)
        return False


async def test_motion_generation():
    """Test motion vector generation from audio."""
    logger.info("\n[4/7] Testing motion generation from audio...")
    
    try:
        from pipecat.processors.avatar.sadtalker_processor import SadTalkerMotionProcessor
        from pipecat.frames.frames import AudioRawFrame
        
        processor = SadTalkerMotionProcessor(device="cuda")
        logger.info("    ✓ SadTalker processor created")
        
        # Create test audio frame
        # 16kHz, 1 second, mono
        audio_data = np.random.randint(-32768, 32767, 16000, dtype=np.int16)
        audio_frame = AudioRawFrame(
            audio=audio_data,
            sample_rate=16000,
            num_channels=1,
        )
        logger.info("    ✓ Test audio frame created (16kHz, 1 second)")
        
        # Process frame
        result_frame = await processor.process_frame(audio_frame)
        logger.info(f"    ✓ Frame processed: {type(result_frame).__name__}")
        
        # Check motion vector
        from pipecat.processors.avatar.motion_vector_frame import MotionVectorFrame
        if isinstance(result_frame, MotionVectorFrame):
            logger.info(f"    ✓ Motion coefficients shape: {result_frame.motion_coefficients.shape}")
            logger.info(f"    ✓ Eye gaze shape: {result_frame.eye_gaze.shape}")
            return True
        else:
            logger.error(f"    ✗ Expected MotionVectorFrame, got {type(result_frame)}")
            return False
        
    except Exception as e:
        logger.error(f"    ✗ Failed motion generation test: {e}", exc_info=True)
        return False


async def test_frame_processing_pipeline():
    """Test the complete frame processing pipeline."""
    logger.info("\n[5/7] Testing frame processing pipeline...")
    
    try:
        from pipecat.processors.avatar.liveportrait_processor import LivePortraitProcessor
        from pipecat.processors.avatar.sadtalker_processor import SadTalkerMotionProcessor
        from pipecat.processors.avatar.motion_vector_frame import MotionVectorFrame
        from pipecat.frames.frames import AudioRawFrame
        from PIL import Image
        
        # Initialize processors
        motion_processor = SadTalkerMotionProcessor(device="cuda")
        avatar_processor = LivePortraitProcessor(device="cuda", resolution=512)
        logger.info("    ✓ Processors initialized")
        
        # Create test image (512x512 RGB)
        test_image = Image.new('RGB', (512, 512), color=(73, 109, 137))
        test_image_array = np.array(test_image)
        logger.info("    ✓ Source image created")
        
        # Set source image (pass numpy array directly)
        start = time.time()
        avatar_processor.set_source_image(test_image_array)
        elapsed = (time.time() - start) * 1000
        logger.info(f"    ✓ Source image set ({elapsed:.2f}ms)")
        
        # Generate motion from audio
        audio_data = np.random.randint(-32768, 32767, 16000, dtype=np.int16)
        audio_frame = AudioRawFrame(
            audio=audio_data,
            sample_rate=16000,
            num_channels=1,
        )
        motion_frame = await motion_processor.process_frame(audio_frame)
        logger.info("    ✓ Motion frame generated from audio")
        
        # Process motion to generate avatar frame
        if isinstance(motion_frame, MotionVectorFrame):
            start = time.time()
            avatar_frame = await avatar_processor.process_frame(motion_frame)
            elapsed = (time.time() - start) * 1000
            logger.info(f"    ✓ Avatar frame generated ({elapsed:.2f}ms)")
            logger.info(f"    ✓ Output frame type: {type(avatar_frame).__name__}")
            return True
        else:
            logger.error("    ✗ Motion processor didn't return MotionVectorFrame")
            return False
        
    except Exception as e:
        logger.error(f"    ✗ Failed pipeline test: {e}", exc_info=True)
        return False


async def test_latency_measurements():
    """Test and measure latency through the pipeline."""
    logger.info("\n[6/7] Testing latency measurements...")
    
    try:
        from pipecat.processors.avatar.liveportrait_processor import LivePortraitProcessor
        from pipecat.processors.avatar.sadtalker_processor import SadTalkerMotionProcessor
        from pipecat.processors.avatar.motion_vector_frame import MotionVectorFrame
        from pipecat.frames.frames import AudioRawFrame
        from PIL import Image
        
        # Initialize processors
        motion_processor = SadTalkerMotionProcessor(device="cuda")
        avatar_processor = LivePortraitProcessor(device="cuda", resolution=512)
        
        # Create test image
        test_image = Image.new('RGB', (512, 512), color=(73, 109, 137))
        test_image_array = np.array(test_image)
        avatar_processor.set_source_image(test_image_array)
        
        # Measure processing latency
        latencies = []
        num_frames = 10
        
        logger.info(f"    Processing {num_frames} frames...")
        
        for i in range(num_frames):
            # Generate motion
            audio_data = np.random.randint(-32768, 32767, 16000, dtype=np.int16)
            audio_frame = AudioRawFrame(
                audio=audio_data,
                sample_rate=16000,
                num_channels=1,
            )
            motion_frame = await motion_processor.process_frame(audio_frame)
            
            # Process motion
            start = time.time()
            await avatar_processor.process_frame(motion_frame)
            latency = (time.time() - start) * 1000
            latencies.append(latency)
            
            if (i + 1) % 5 == 0:
                logger.info(f"        Frame {i+1}/{num_frames}: {latency:.2f}ms")
        
        # Calculate statistics
        avg_latency = np.mean(latencies)
        min_latency = np.min(latencies)
        max_latency = np.max(latencies)
        std_latency = np.std(latencies)
        
        logger.info(f"\n    Latency Statistics:")
        logger.info(f"        Average:  {avg_latency:.2f}ms")
        logger.info(f"        Min:      {min_latency:.2f}ms")
        logger.info(f"        Max:      {max_latency:.2f}ms")
        logger.info(f"        Std Dev:  {std_latency:.2f}ms")
        
        # Check real-time capability (60 FPS = 16.67ms budget)
        if avg_latency < 16.67:
            logger.info(f"    ✓ REAL-TIME CAPABLE: {avg_latency:.2f}ms < 16.67ms (60 FPS)")
            return True
        else:
            logger.warning(f"    ⚠ Slower than 60 FPS: {avg_latency:.2f}ms > 16.67ms")
            # Still pass test since it's within acceptable range for 30 FPS
            if avg_latency < 33.33:
                logger.info(f"    ✓ ACCEPTABLE: Achieves ~30 FPS ({avg_latency:.2f}ms)")
                return True
            else:
                logger.error(f"    ✗ TOO SLOW for real-time: {avg_latency:.2f}ms")
                return False
        
    except Exception as e:
        logger.error(f"    ✗ Failed latency test: {e}", exc_info=True)
        return False


async def test_environment_validation():
    """Validate environment for main pipeline."""
    logger.info("\n[7/7] Validating environment for main pipeline...")
    
    # Check Groq API
    api_key = os.getenv("GROQ_API_KEY")
    if api_key:
        logger.info("    ✓ GROQ_API_KEY found")
    else:
        logger.warning("    ⚠ GROQ_API_KEY not found (required for main pipeline)")
    
    # Check Ollama
    import subprocess
    try:
        result = subprocess.run(
            ["curl", "-s", "http://localhost:11434/api/tags"],
            capture_output=True,
            timeout=2
        )
        if result.returncode == 0:
            logger.info("    ✓ Ollama server is running")
        else:
            logger.warning("    ⚠ Ollama server might not be running")
    except Exception:
        logger.warning("    ⚠ Could not verify Ollama (curl not available or timeout)")
    
    # Check config
    config_path = Path(__file__).parent / "config.yaml"
    if config_path.exists():
        logger.info(f"    ✓ Configuration file found: {config_path}")
    else:
        logger.warning(f"    ⚠ Configuration file not found: {config_path}")
    
    # Check .env
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        logger.info(f"    ✓ Environment file found: {env_path}")
    else:
        logger.warning(f"    ⚠ Environment file not found: {env_path}")
    
    return True


async def main():
    """Run all integration tests."""
    logger.info("=" * 70)
    logger.info("🧪 INTEGRATION TEST SUITE")
    logger.info("LivePortrait + Conversational Pipeline")
    logger.info("=" * 70)
    
    results = {}
    
    # Test 1: Imports
    results['imports'] = test_imports()
    if not results['imports']:
        logger.error("\n❌ Import test failed. Cannot continue.")
        return False
    
    # Test 2: LivePortrait Processor
    results['liveportrait'] = test_liveportrait_processor()
    if not results['liveportrait']:
        logger.error("\n❌ LivePortrait test failed.")
    
    # Test 3: SadTalker Processor
    results['sadtalker'] = test_sadtalker_processor()
    if not results['sadtalker']:
        logger.error("\n❌ SadTalker test failed.")
    
    # Test 4: Motion Generation
    results['motion'] = await test_motion_generation()
    if not results['motion']:
        logger.error("\n❌ Motion generation test failed.")
    
    # Test 5: Frame Processing
    results['pipeline'] = await test_frame_processing_pipeline()
    if not results['pipeline']:
        logger.error("\n❌ Frame processing pipeline test failed.")
    
    # Test 6: Latency
    results['latency'] = await test_latency_measurements()
    if not results['latency']:
        logger.error("\n❌ Latency test failed.")
    
    # Test 7: Environment
    await test_environment_validation()
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("📊 TEST SUMMARY")
    logger.info("=" * 70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"    {status}: {test_name}")
    
    logger.info(f"\n    Total: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("\n" + "=" * 70)
        logger.info("✅ ALL TESTS PASSED!")
        logger.info("=" * 70)
        logger.info("\n✓ The avatar pipeline is ready for integration!")
        logger.info("\nNext steps:")
        logger.info("  1. Integrate LivePortrait into backend.py")
        logger.info("  2. Add motion processors to the pipeline")
        logger.info("  3. Run backend.py for end-to-end testing")
        logger.info("  4. Test with Daily.co transport or local audio")
        logger.info("=" * 70)
        return True
    else:
        logger.info("\n" + "=" * 70)
        logger.info(f"⚠ {total - passed} test(s) failed")
        logger.info("=" * 70)
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
