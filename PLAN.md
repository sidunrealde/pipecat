# Real-Time Photorealistic Avatar Conversational AI - Project Plan

## Executive Summary

Build a **HeyGen-competitive real-time photorealistic avatar system** using:
- **LivePortrait**: Real-time face reenactment (12.8ms per frame latency)
- **SadTalker**: Audio-driven motion synthesis
- **Pipecat**: Real-time conversational pipeline
- **Local Ollama**: Free LLM
- **3090 GPU**: All local processing

**Result**: Photorealistic talking avatar that responds to user speech with full lip-sync and expressions, entirely free and open-source.

---

## Architecture Overview

```
Browser (WebRTC)
    │
    ├─ Microphone audio stream
    │
    ▼
Pipecat Backend Pipeline
    │
    ├─ STT (Groq Whisper): ~500ms
    │  └─→ Transcription + confidence
    │
    ├─ LLM (Ollama 7B/13B): ~2-5 seconds
    │  └─→ Response text
    │
    ├─ TTS (Piper): ~500ms
    │  └─→ Audio + duration
    │
    ├─ SadTalker Motion (async): ~200-300ms
    │  └─→ 3D motion coefficients (head/expression/eyes)
    │     [Frame queue, doesn't block audio output]
    │
    ├─ LivePortrait Reenactment (real-time): 12.8ms/frame
    │  ├─ Input: Source image + motion vector
    │  ├─ Output: Reenacted frame (512×512)
    │  └─→ 30 FPS streaming
    │
    ├─ Optional: GFPGAN Enhancement: ~20ms
    │  └─→ Photorealism boost
    │
    └─ WebRTC Encoder + Transport
       └─→ H.264 video to browser

GPU Memory (3090, 12GB):
    ├─ LivePortrait: ~2-3GB (loaded continuously)
    ├─ SadTalker: ~3-4GB (loads during inference)
    ├─ STT/LLM/TTS: ~4-5GB
    ├─ GFPGAN: ~1GB (optional)
    └─ Buffers: ~1-2GB
    Total: ~11-12GB ✅
```

---

## Latency Breakdown

```
User speaks:           0ms
└─ Audio input         + 20ms (network buffer)
└─ STT processing      + 500ms (Groq Whisper)
└─ LLM generation      + 2-5 seconds (Ollama response time)
└─ TTS synthesis       + 500ms (Piper)
└─ SadTalker motion    + 200-300ms (runs async, doesn't block)
└─ LivePortrait stream + 50-100ms (30fps, 12.8ms per frame + buffering)
└─ WebRTC encode/send  + 50ms (H.264 encoder + network)
└─ Browser render      + 20-30ms (WebGL)
───────────────────────────────────
TOTAL: 3.5-7 seconds (mostly LLM response time)

Avatar responds with speech: Immediate (TTS streams to avatar)
Visual sync latency: ~100-150ms (acceptable for conversational AI)
```

---

## Pipecat Integration Architecture

### New Components to Create

**1. LivePortraitProcessor (Custom Processor)**
```python
class LivePortraitProcessor(FrameProcessor):
    """
    Real-time face reenactment using LivePortrait model.
    Input: VideoFrame (source image) + MotionVectorFrame (3D motion)
    Output: VideoFrame (reenacted video)
    Latency: 12.8ms per frame
    """
    async def process_frame(self, frame, motion_vector):
        # Reenact face using motion guidance
        # Returns frame in <15ms for streaming
```

**2. SadTalkerMotionProcessor (Custom Processor)**
```python
class SadTalkerMotionProcessor(FrameProcessor):
    """
    Extract audio-driven 3D motion coefficients from TTS audio.
    Input: AudioFrame (TTS output)
    Output: MotionVectorFrame (3D coefficients + metadata)
    Latency: 200-300ms (runs async, doesn't block audio)
    """
    async def process_frame(self, audio_frame):
        # Extract motion coefficients
        # Queue for LivePortrait
```

**3. MotionVectorFrame (New Frame Type)**
```python
class MotionVectorFrame(Frame):
    """Carries 3D motion data (head pose, expression, eye gaze)"""
    motion_coefficients: np.ndarray  # Shape: (6,) for head pose + expression
    eye_gaze: np.ndarray             # Shape: (2,) for eye direction
    timestamp: float                 # For sync with audio
```

### Pipeline Chain

```
User Audio
    ↓
STT Service (Groq Whisper)
    ↓
LLMResponseAggregator
    ↓
SimpleTextAggregator
    ├─→ TTS Service (Piper)
    │   ├─→ AudioFrame (output)
    │   └─→ [Async] SadTalkerMotionProcessor
    │       └─→ MotionVectorFrame
    │
    └─→ [Real-time] LivePortraitProcessor
        ├─ Input: VideoFrame (user image) + MotionVectorFrame
        ├─ Output: VideoFrame (reenacted)
        └─→ WebRTC Transport

Interruption Handler: UserTurnController
    └─ Detects speech via VAD
    └─ Cancels ongoing SadTalker motion computation
    └─ Stops LivePortrait animation
    └─ Returns to listening state
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1)

**1.1 - Get LivePortrait Running Locally**
- Clone [LivePortrait](https://github.com/KwaiVGI/LivePortrait)
- Install dependencies: `pip install -r requirements.txt`
- Download pretrained model (~200MB)
- Test on sample image: Run inference, measure latency on 3090
- **Acceptance criteria**: Verify 12.8ms per-frame latency on 3090

**1.2 - Test Pipecat Base Pipeline (No Avatar)**
- Create simple conversational loop: STT → LLM → TTS
- Use existing Pipecat examples: `07-interruptible-basic.py` as reference
- Configure Groq STT (free tier)
- Configure Ollama LLM (local, Mistral 7B)
- Configure Piper TTS (open-source)
- Test with microphone input, terminal output
- **Acceptance criteria**: Full conversation loop works, can interrupt

**1.3 - Set Up Project Structure**
```
src/
├── pipecat/
│   └── processors/
│       └── avatar/
│           ├── __init__.py
│           ├── liveportrait_processor.py
│           ├── sadtalker_processor.py
│           └── motion_vector_frame.py
│
examples/
└── avatar_conversation/
    ├── backend.py         # Main pipecat pipeline
    ├── frontend/
    │   ├── index.html
    │   ├── style.css
    │   └── main.js
    └── config.yaml

tests/
└── test_avatar_processors.py
```

---

### Phase 2: LivePortrait Integration (Week 2)

**2.1 - Create LivePortraitProcessor**
- Implement as custom Pipecat processor
- Load model on initialization (keep in GPU memory)
- Handle VideoFrame input + MotionVectorFrame input
- Output VideoFrame with reenacted face
- **Acceptance criteria**: Processor works in isolation, <15ms latency

**2.2 - Implement Frame Streaming**
- Create minimal motion vector (constant values for testing)
- Feed VideoFrame → LivePortraitProcessor → WebRTC
- Test video output quality and latency
- **Acceptance criteria**: Video streams to browser at 30 FPS, visual quality ✅

**2.3 - Build Web Frontend (Minimal)**
- Single page: Image upload + video display
- WebRTC video playback
- **Acceptance criteria**: Can upload image, see live video feed

**2.4 - Test GPU Memory**
- Verify LivePortrait + Ollama fit in 12GB
- Monitor memory during inference
- Optimize if needed (reduce resolution, etc.)
- **Acceptance criteria**: No OOM errors, sustained inference

---

### Phase 3: SadTalker Motion Integration (Week 3)

**3.1 - Create SadTalkerMotionProcessor**
- Load SadTalker model in separate GPU stream
- Accept AudioFrame (TTS output)
- Extract 3D motion coefficients (head pose, expression)
- Output MotionVectorFrame
- **Acceptance criteria**: Processor works, motion looks natural

**3.2 - Map Motion Vectors**
- SadTalker outputs: 3D FLAME coefficients (pose + expression)
- LivePortrait expects: 2D keypoint flow or optical flow
- Create mapper: 3D → 2D motion vectors
- **Acceptance criteria**: Motion transfers correctly between models

**3.3 - Async Processing Pipeline**
- SadTalkerMotionProcessor runs async (doesn't block audio output)
- Audio streams to TTS immediately
- Motion computed in parallel, queued for LivePortrait
- Graceful degradation if motion lags
- **Acceptance criteria**: Audio and video both stream smoothly

**3.4 - Synchronization**
- Align motion frame timing with audio
- Use timestamps to match video frames to audio segments
- Handle variable inference latency
- **Acceptance criteria**: Lip-sync within 100ms offset

---

### Phase 4: Complete Integration (Week 4)

**4.1 - Image Preprocessing Pipeline**
- User uploads portrait image
- Face detection (MediaPipe or RetinaFace)
- Auto-crop and align to 512×512
- Validate image quality, show warnings
- Fallback: Placeholder avatar on detection failure
- **Acceptance criteria**: Handles various image formats/qualities

**4.2 - Interruption Handling**
- Wire UserTurnController into pipeline
- Detect user speech via VAD
- Cancel ongoing SadTalker inference
- Stop LivePortrait animation smoothly
- Return to listening state
- **Acceptance criteria**: User can interrupt naturally, no artifacts

**4.3 - Build Full Web Frontend**
- Image upload with preview
- Microphone input with VAD indicator
- Full-screen video display
- Real-time status (listening/thinking/speaking)
- Error handling and fallbacks
- **Acceptance criteria**: Polished UX, no console errors

**4.4 - End-to-End Testing**
- Full conversation flow: Upload image → speak → see avatar respond → interrupt
- Measure latencies at each stage
- Verify quality (photorealism, lip-sync, expressions)
- Test edge cases (bad images, rapid interruptions, etc.)
- **Acceptance criteria**: Meets all success criteria (see below)

---

### Phase 5: Optimization & Polish (Week 5+)

**5.1 - Optional GFPGAN Enhancement**
- Add face enhancement layer (~20ms latency)
- Toggle on/off for quality vs. speed trade-off
- Test impact on photorealism
- **Acceptance criteria**: Noticeable quality improvement

**5.2 - GPU Memory Optimization**
- Profile memory usage
- Implement smart model loading/unloading
- Reduce resolution if needed (384×384 fallback)
- **Acceptance criteria**: Stable, no OOM errors

**5.3 - Latency Optimization**
- Profile each component
- Identify bottlenecks (SadTalker, WebRTC encoding, etc.)
- Consider quantization, pruning, or alternative models
- **Acceptance criteria**: Reduce total latency to <3 seconds

**5.4 - Quality Improvements**
- Fine-tune motion smoothness
- Improve lip-sync accuracy
- Add expression variation (from sentiment analysis)
- **Acceptance criteria**: Subjective quality matches HeyGen or better

---

## Dependencies & Installation

### Python Packages to Install

```bash
# Core
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install liveportrait
pip install sadtalker
pip install piper-tts
pip install groq
pip install ollama

# Optional enhancements
pip install gfpgan
pip install retinaface  # or mediapipe for face detection
pip install ffmpeg-python

# Pipecat already installed via uv sync
```

### External Dependencies

- **Ollama**: Download from https://ollama.ai
  - Pull model: `ollama pull mistral` (7B, ~4GB)
  - Or: `ollama pull llama2` (7B alternative)
  - Run: `ollama serve` (listens on localhost:11434)

- **FFMPEG**: Required for video encoding
  - Windows: Install via Chocolatey or direct download
  - Used by WebRTC transport for H.264 encoding

### Environment Setup

```bash
# Create .env file
GROQ_API_KEY=your_groq_key_here
OLLAMA_BASE_URL=http://localhost:11434

# Groq free tier: 6000 requests/month (enough for development/testing)
```

---

## Key Decisions & Rationale

### Why LivePortrait over SadTalker?

| Metric | SadTalker | LivePortrait |
|--------|-----------|---|
| **Latency per frame** | 200-500ms | **12.8ms** |
| **Streaming capable** | ❌ Batch only | ✅ Real-time |
| **Visual quality** | ★★★★★ | ★★★★★ |
| **Real-time feel** | ❌ Async/slow | ✅ Smooth 30 FPS |

**Decision**: LivePortrait for streaming, SadTalker for motion extraction (best-in-class audio sync).

### Why Groq STT + Ollama LLM + Piper TTS?

- **Groq**: Free tier, 6000 requests/month, fast inference (500ms)
- **Ollama**: Self-hosted, free, no API limits, instant response
- **Piper**: Open-source, no API costs, good quality
- **Together**: Cost-effective for all 3 components if needed later

### Why WebRTC over HLS?

- Real-time bidirectional (audio in, video out)
- Lower latency (<100ms vs. 2-10 seconds)
- Pipecat has native WebRTC support
- Browser native support (no extra plugins)

### Why 512×512 Resolution?

- Compromise between quality and speed
- 12.8ms/frame at 512×512 on RTX 4090 → ~10ms on 3090 (estimated)
- Still very high quality for avatars
- Fallback to 384×384 if latency issues

---

## Success Criteria

### Functional Requirements
- ✅ Photorealistic avatar from user-provided image
- ✅ Audio-driven lip-sync (within 100ms offset)
- ✅ Natural head movements + expression changes
- ✅ Real-time streaming (12.8ms LivePortrait + <150ms total overhead)
- ✅ User can interrupt and be heard immediately
- ✅ Full conversation loop: speak → bot responds with avatar

### Technical Requirements
- ✅ WebRTC delivery to browser
- ✅ Zero cost (all open-source)
- ✅ 3090 compatible (fits in 12GB VRAM)
- ✅ <7 seconds total latency (user speaks to avatar responds)
- ✅ 99%+ uptime (no crashes or OOM errors)

### Quality Requirements
- ✅ Photorealism matches or exceeds HeyGen
- ✅ Lip-sync subjectively indistinguishable from natural speech
- ✅ Head movements feel natural and varied
- ✅ Expressions change appropriately with content
- ✅ No artifacts (glitching, face warping, etc.)

---

## Potential Issues & Mitigation

| Issue | Impact | Mitigation |
|-------|--------|-----------|
| **SadTalker inference too slow** | Delays motion, async queue builds up | Reduce motion updates, use cached motion, or pre-compute |
| **LivePortrait drops frames** | Visual stuttering | Reduce streaming FPS (30 → 24), buffer frames |
| **WebRTC latency spikes** | Audio/video sync issues | Use HLS backup, add jitter buffer, adaptive bitrate |
| **Image preprocessing fails** | Avatar won't load | Fallback to placeholder, show error UI |
| **Ollama LLM too slow** | User waits 5+ seconds | Use smaller model (Mistral 7B), add typing indicator |
| **OOM during inference** | Crashes | Profile memory, implement model unloading, reduce batch size |
| **User interrupts during motion gen** | Stale motion vectors | Cancel async task, discard queue, restart |
| **Lip-sync drift over time** | Audio/video desyncs | Re-sync every N seconds, timestamp validation |

---

## Testing Strategy

### Unit Tests
- `test_liveportrait_processor.py`: Processor logic, latency, output shape
- `test_sadtalker_processor.py`: Motion extraction, coefficient format
- `test_motion_vector_frame.py`: Frame serialization

### Integration Tests
- `test_pipeline_audio_to_avatar.py`: Full audio → motion → video flow
- `test_interruption_handling.py`: VAD, turn control, graceful shutdown
- `test_webrtc_streaming.py`: Video stream quality, latency

### End-to-End Tests
- Manual: Upload image, speak, verify avatar responds with lip-sync
- Manual: Interrupt mid-sentence, verify clean transition
- Manual: Various image qualities, expressions, accents
- Performance: Measure latencies, GPU usage, memory

### Benchmarks
- LivePortrait: 12.8ms/frame target, 30 FPS streaming
- SadTalker: <300ms for motion extraction
- Total latency: <7 seconds (including LLM)
- GPU memory: <12GB sustained
- Video quality: 512×512, H.264, 24-30 FPS

---

## File Structure (Final)

```
pipecat/
├── PLAN.md (this file)
├── pyproject.toml (existing)
├── README.md (existing)
│
├── src/pipecat/
│   ├── processors/
│   │   ├── user_turn_processor.py (existing)
│   │   └── avatar/
│   │       ├── __init__.py
│   │       ├── liveportrait_processor.py (NEW)
│   │       ├── sadtalker_processor.py (NEW)
│   │       ├── motion_vector_frame.py (NEW)
│   │       └── utils.py
│   └── frames.py (modify to add MotionVectorFrame)
│
├── examples/avatar_conversation/
│   ├── backend.py (NEW - main pipecat pipeline)
│   ├── config.yaml (NEW - configuration)
│   ├── requirements.txt (NEW - additional deps)
│   └── frontend/
│       ├── index.html (NEW)
│       ├── style.css (NEW)
│       ├── main.js (NEW)
│       └── assets/ (avatars, icons, etc.)
│
└── tests/
    ├── test_avatar_processors.py (NEW)
    ├── test_avatar_pipeline.py (NEW)
    └── test_interruption_avatar.py (NEW)
```

---

## Timeline & Milestones

- **Week 1 (Feb 4-10)**: Foundation - Get LivePortrait running, basic Pipecat pipeline
- **Week 2 (Feb 11-17)**: LivePortrait integration - Streaming video to browser
- **Week 3 (Feb 18-24)**: SadTalker integration - Audio-driven motion
- **Week 4 (Feb 25-Mar 3)**: Full integration - Image upload, interruption, web frontend
- **Week 5+ (Mar 4+)**: Optimization and polish - Performance, quality, UX

---

## Success Definition

**Project succeeds when:**
1. User can upload a photo
2. User speaks into microphone
3. Avatar appears in browser
4. Avatar responds with speech + photorealistic lip-sync + expressions
5. User can interrupt naturally
6. Total latency is <7 seconds (mostly LLM)
7. No crashes, memory stable
8. Quality rivals or exceeds HeyGen

---

## Future Enhancements

1. **Expression Transfer**: Analyze sentiment/emotion from LLM output → modify avatar expressions
2. **Hand Gestures**: Add First Order Motion Model for arm movements
3. **Multi-Avatar**: Switch between multiple avatars mid-conversation
4. **Voice Clone**: Use TTS voice cloning for personalized audio
5. **Recording**: Save conversation video for playback
6. **Analytics**: Track conversation quality, user satisfaction
7. **Scalability**: Load balancing for multiple concurrent users
8. **Mobile**: React Native frontend for mobile deployment

---

**Document Version**: 1.0  
**Last Updated**: February 4, 2026  
**Status**: Ready for Implementation
