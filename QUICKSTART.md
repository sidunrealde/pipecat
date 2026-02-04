# Quick Start - Avatar Conversation Project

## Current Status

✅ **Phase 1 Foundation - 60% Complete**
- ✅ Step 1.1: LivePortrait cloned & dependencies installed
- ✅ Step 1.3: Project structure created with avatar processors
- ⏳ Step 1.2: Base Pipecat pipeline (in progress)

## Project Files

### Core Avatar Code
```
src/pipecat/processors/avatar/
├── __init__.py                  # Module exports
├── motion_vector_frame.py       # 3D motion data frame (✓ working)
├── liveportrait_processor.py    # Real-time face reenactment (stub)
└── sadtalker_processor.py       # Audio-to-motion synthesis (stub)
```

### Tests
```
tests/test_avatar_processors.py  # 10 passing tests ✓
```

### Documentation
```
PLAN.md                          # Detailed 5-week implementation plan
PHASE_1_SUMMARY.md               # What was completed in Phase 1
```

### Example Application
```
examples/avatar_conversation/
├── backend.py                   # Pipecat pipeline (Phase 1.2)
├── config.yaml                  # Configuration
├── requirements.txt             # Dependencies
└── frontend/                     # Web UI (Phase 4)
```

## Quick Commands

### Run Tests
```bash
uv run pytest tests/test_avatar_processors.py -v
```

Output should show:
```
10 passed in 1.43s ✓
```

### Check Installation
```bash
python test_liveportrait_setup.py
```

This verifies:
- ✓ PyTorch and CUDA setup
- ✓ LivePortrait imports
- ✓ Model path availability

### Next: Implement Phase 1.2
```bash
# Edit the example backend
code examples/avatar_conversation/backend.py

# TODO: Complete the conversational pipeline
```

## Architecture Overview

### Frame Flow (Future)
```
User Audio
  ↓ (Groq STT)
Transcription
  ↓ (Ollama LLM)
LLM Response
  ↓ (Piper TTS)
TTS Audio
  ├─→ Speaker Output
  └─→ (SadTalker) Motion Extraction
  ↓
Motion Vectors
  ↓ (LivePortrait)
Animated Avatar
  ↓
WebRTC Video Stream → Browser
```

### Key Data Structures

**MotionVectorFrame** (3D motion data)
```python
frame = MotionVectorFrame(
    motion_coefficients=np.array([pitch, yaw, roll, expr1, expr2, expr3]),
    eye_gaze=np.array([h_gaze, v_gaze]),
    timestamp=1.5,  # seconds
    frame_index=10,
    metadata={"source": "sadtalker"}
)
```

### GPU Requirements (3090 - 12GB VRAM)
- LivePortrait: ~2-3GB
- SadTalker: ~3-4GB
- STT/LLM/TTS: ~4-5GB
- Buffers: ~1-2GB
- **Total: ~11-12GB** ✓ Fits

## Phase Roadmap

| Phase | Task | Status | Duration |
|-------|------|--------|----------|
| 1.1 | Clone LivePortrait | ✅ DONE | - |
| 1.2 | Base Pipecat pipeline | ⏳ IN PROGRESS | Week 1 |
| 1.3 | Project structure | ✅ DONE | - |
| 2.1 | LivePortrait processor | ⏹ TODO | Week 2 |
| 2.2 | Frame streaming | ⏹ TODO | Week 2 |
| 2.3 | Web frontend | ⏹ TODO | Week 2 |
| 3.1 | SadTalker processor | ⏹ TODO | Week 3 |
| 3.2 | Motion vector mapping | ⏹ TODO | Week 3 |
| 3.3 | Async processing | ⏹ TODO | Week 3 |
| 4.1 | Image preprocessing | ⏹ TODO | Week 4 |
| 4.2 | Interruption handling | ⏹ TODO | Week 4 |
| 4.3 | Full web UI | ⏹ TODO | Week 4 |
| 4.4 | E2E testing | ⏹ TODO | Week 4 |

## Key Technologies

- **Framework**: Pipecat (real-time AI pipeline)
- **Face Reenactment**: LivePortrait (12.8ms/frame latency)
- **Motion Synthesis**: SadTalker (200-300ms, async)
- **STT**: Groq Whisper (free tier, 500ms)
- **LLM**: Ollama (local, self-hosted)
- **TTS**: Piper (open-source, local)
- **Transport**: WebRTC (low-latency streaming)
- **GPU**: NVIDIA RTX 3090 (12GB VRAM)

## Key Metrics (Target)

| Metric | Target | Status |
|--------|--------|--------|
| **Latency** | <7 seconds total | Design ready |
| **Avatar Quality** | ⭐⭐⭐⭐⭐ Photorealistic | Design ready |
| **Lip-Sync** | <100ms offset | Design ready |
| **Cost** | $0 (all open-source) | ✓ Achieved |
| **Interruption** | User can interrupt naturally | Design ready |
| **GPU Fit** | <12GB VRAM | ✓ Achieves 11-12GB |

## Environment Setup

### Required Environment Variables
```bash
# For Groq API (free tier)
GROQ_API_KEY=your_groq_api_key_here

# For Ollama (default)
OLLAMA_BASE_URL=http://localhost:11434
```

### Required External Services
- **Ollama**: Download from https://ollama.ai
  - Pull a model: `ollama pull mistral` (7B)
  - Run: `ollama serve`

## Next Steps

1. **Complete Phase 1.2**: Implement base Pipecat pipeline with Groq STT, Ollama LLM, Piper TTS
2. **Download LivePortrait models**: Run `python LivePortrait/app.py` to auto-download
3. **Test inference latency**: Run LivePortrait on 3090, verify ~12.8ms per frame
4. **Implement Phase 2**: Integrate LivePortrait processor into Pipecat

## Useful Links

- **Pipecat**: https://docs.pipecat.ai
- **LivePortrait**: https://github.com/KwaiVGI/LivePortrait
- **SadTalker**: https://github.com/OpenTalker/SadTalker
- **Plan Document**: See `PLAN.md` for detailed phase-by-phase breakdown

---

**Last Updated**: February 4, 2026
**Next Milestone**: Phase 1.2 - Voice conversation without avatar
