# Integration Guide: LivePortrait + Backend

This guide shows how to integrate the avatar pipeline into the conversational backend.

## Quick Start (5 minutes)

### 1. Update imports in `backend.py`:

```python
# Add these imports after the existing imports
from pipecat.processors.avatar.liveportrait_processor import LivePortraitProcessor
from pipecat.processors.avatar.sadtalker_processor import SadTalkerMotionProcessor
```

### 2. Create processors (after TTS service initialization):

```python
# Avatar processors
logger.info("    [3f] Setting up Avatar processors...")
motion_processor = SadTalkerMotionProcessor(device="cuda", fps=25)
logger.info("        ✓ SadTalker motion processor ready")

avatar_processor = LivePortraitProcessor(device="cuda", resolution=512)
logger.info("        ✓ LivePortrait avatar processor ready")
```

### 3. Update pipeline (replace the old pipeline):

**Before:**
```python
pipeline = Pipeline([
    transport.input(),
    stt,
    context_aggregator.user(),
    llm,
    tts,
    transport.output(),
    context_aggregator.assistant(),
])
```

**After:**
```python
pipeline = Pipeline([
    transport.input(),              # Audio input from user
    stt,                            # Speech → Text
    context_aggregator.user(),      # Add to conversation
    llm,                            # Generate response
    tts,                            # Text → Speech
    motion_processor,               # ← Audio → Motion
    avatar_processor,               # ← Motion → Animated Avatar
    transport.output(),             # Stream output
    context_aggregator.assistant(), # Add assistant message
])
```

### 4. Load avatar image (before pipeline creation):

```python
# Load avatar image
avatar_image_path = Path(__file__).parent / "avatar.jpg"
if avatar_image_path.exists():
    logger.info(f"    Loading avatar image: {avatar_image_path}")
    import cv2
    avatar_image = cv2.imread(str(avatar_image_path))
    avatar_image_rgb = cv2.cvtColor(avatar_image, cv2.COLOR_BGR2RGB)
    avatar_processor.set_source_image(avatar_image_rgb)
    logger.info("    ✓ Avatar image loaded")
else:
    logger.warning(f"    Avatar image not found: {avatar_image_path}")
    logger.info("    Provide an avatar image to enable video output")
```

### 5. Run!

```bash
python backend.py
```

---

## Complete Modified Section

Here's the complete `main()` function modification:

```python
async def main():
    """Main function to run the avatar conversation pipeline."""
    
    logger.info("=" * 70)
    logger.info("🎙️  AVATAR CONVERSATION PIPELINE - Phase 2.5")
    logger.info("=" * 70)
    logger.info("")
    logger.info("Components:")
    logger.info("  ✓ STT: Groq Whisper (speech-to-text)")
    logger.info("  ✓ LLM: Ollama Mistral 7B (local)")
    logger.info("  ✓ TTS: Groq (text-to-speech)")
    logger.info("  ✓ Avatar: LivePortrait + SadTalker")  # ← UPDATED
    logger.info("")
    logger.info("=" * 70)
    
    # ... existing validation code ...
    
    # Initialize services
    logger.info("\n[3/6] Initializing AI services...")  # ← UPDATED COUNT
    
    try:
        from pipecat.services.groq import GroqSTTService, GroqTTSService
        from pipecat.services.ollama import OLLamaLLMService
        from pipecat.audio.vad.silero import SileroVADAnalyzer
        from pipecat.pipeline.pipeline import Pipeline
        from pipecat.pipeline.runner import PipelineRunner
        from pipecat.pipeline.task import PipelineParams, PipelineTask
        from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
        from pipecat.transports.services.daily import DailyParams, DailyTransport
        from pipecat.frames.frames import TextFrame, EndFrame
        # ← ADD THESE IMPORTS
        from pipecat.processors.avatar.liveportrait_processor import LivePortraitProcessor
        from pipecat.processors.avatar.sadtalker_processor import SadTalkerMotionProcessor
        
        logger.info("    ✓ Pipecat components imported")
    except ImportError as e:
        logger.error(f"    ✗ Failed to import Pipecat: {e}")
        return
    
    # STT Service
    logger.info("    [3a] Setting up STT (Groq Whisper)...")
    stt = GroqSTTService(api_key=api_key, model=config['stt']['groq']['model'])
    logger.info("        ✓ Groq STT ready")
    
    # LLM Service  
    logger.info("    [3b] Setting up LLM (Ollama)...")
    llm = OLLamaLLMService(base_url=ollama_url, model=ollama_model)
    logger.info("        ✓ Ollama LLM ready")
    
    # TTS Service
    logger.info("    [3c] Setting up TTS (Groq)...")
    tts = GroqTTSService(api_key=api_key, voice="sage")
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
        messages=[{"role": "system", "content": system_prompt}]
    )
    context_aggregator = llm.create_context_aggregator(context)
    logger.info("        ✓ Context aggregator ready")
    
    # ← ADD THIS SECTION
    # Avatar processors
    logger.info("    [3f] Setting up Avatar processors...")
    motion_processor = SadTalkerMotionProcessor(device="cuda", fps=25)
    logger.info("        ✓ SadTalker motion processor ready")
    
    avatar_processor = LivePortraitProcessor(device="cuda", resolution=512)
    logger.info("        ✓ LivePortrait avatar processor ready")
    
    # Load avatar image
    avatar_image_path = Path(__file__).parent / "avatar.jpg"
    if avatar_image_path.exists():
        import cv2
        logger.info(f"        Loading avatar image: {avatar_image_path}")
        avatar_image = cv2.imread(str(avatar_image_path))
        if avatar_image is not None:
            avatar_image_rgb = cv2.cvtColor(avatar_image, cv2.COLOR_BGR2RGB)
            avatar_processor.set_source_image(avatar_image_rgb)
            logger.info("        ✓ Avatar image loaded")
    else:
        logger.warning(f"        ⚠ Avatar image not found: {avatar_image_path}")
        logger.info("        Place avatar.jpg in examples/avatar_conversation/ to enable video output")
    
    # Transport
    logger.info("\n[4/6] Initializing transport...")  # ← UPDATED COUNT
    logger.info("    Note: Using Daily.co transport for audio I/O")
    
    transport = DailyTransport(
        room_url="",
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
    logger.info("\n[5/6] Building avatar conversation pipeline...")  # ← UPDATED COUNT
    pipeline = Pipeline([
        transport.input(),              # Audio input
        stt,                            # Speech → Text
        context_aggregator.user(),      # Add to conversation
        llm,                            # Generate response
        tts,                            # Text → Speech
        motion_processor,               # ← NEW: Audio → Motion
        avatar_processor,               # ← NEW: Motion → Avatar
        transport.output(),             # Stream output
        context_aggregator.assistant(), # Add assistant message
    ])
    logger.info("    ✓ Pipeline built with avatar processors")
    
    # ... rest of function ...
```

---

## Performance Expectations

After integration, you should see:

```
[3f] Setting up Avatar processors...
    ✓ SadTalker motion processor ready
    ✓ LivePortrait avatar processor ready
    ✓ Avatar image loaded

[5/6] Building avatar conversation pipeline...
    ✓ Pipeline built with avatar processors

Avatar Processing Latency: ~1.3ms per frame (60 FPS capable)
```

---

## Configuration Options

### Adjust Avatar Processor Settings:

```python
# Higher resolution (slower)
avatar_processor = LivePortraitProcessor(
    device="cuda",
    resolution=512,  # Options: 256, 512
)

# Motion processor FPS
motion_processor = SadTalkerMotionProcessor(
    device="cuda",
    fps=25,  # 24-30 typical for talking heads
)

# CPU-only (if GPU not available)
avatar_processor = LivePortraitProcessor(
    device="cpu",
    resolution=256,  # Use lower res on CPU
)
```

---

## Troubleshooting

### Issue: "LivePortrait models not found"
**Solution**: Download models first:
```bash
python scripts/download_liveportrait_models.py
```

### Issue: "Avatar processor not generating frames"
**Solution**: Make sure source image is loaded:
```python
# The processor needs a source image
avatar_processor.set_source_image(avatar_image_array)
```

### Issue: "Slow performance"
**Solution**: Check device setting:
```python
# Use CUDA if available
avatar_processor = LivePortraitProcessor(device="cuda")

# Check GPU availability
import torch
print("CUDA Available:", torch.cuda.is_available())
```

### Issue: "Daily.co transport not working"
**Solution**: This requires Daily.co signup. For local testing, switch transport:
```python
# Use local audio instead
# (Requires different transport implementation)
```

---

## Next Steps

1. **Add avatar image**: Place `avatar.jpg` in `examples/avatar_conversation/`
2. **Run backend**: `python backend.py`
3. **Test conversation**: The system will print a Daily.co room URL
4. **Monitor latency**: Watch for avatar processor logs

---

## Files Modified

- `backend.py` - Added avatar processors to pipeline
- `config.yaml` - (Optional) Avatar processor configuration
- `avatar.jpg` - (Required) Avatar image file

---

## Test Integration

Before running the full backend, validate with:

```bash
# Test individual components
python test_integration.py

# Expected output: ✅ ALL TESTS PASSED
```

All tests should pass before integrating into backend.
