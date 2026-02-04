# Phase 2 Status - LivePortrait Integration

**Date**: February 4, 2026  
**Status**: ⚠️ **Partial - Models Downloaded, Integration In Progress**

---

## ✅ Completed

### 1. Model Download (✓ DONE)
Downloaded all LivePortrait pretrained models from HuggingFace:
- **Size**: 2.14GB total (includes human + animal models)
- **Location**: `F:\Projects\LLM\LivePortrait\pretrained_weights\`
- **Components**:
  - Appearance feature extractor (`.pth`)
  - Motion extractor (`.pth`)
  - SPADE generator (`.pth`)
  - Warping module (`.pth`)
  - Stitching/retargeting module (`.pth`)
  - InsightFace models (`.onnx`)
  - Landmark detection (`.onnx`)

### 2. Processor Structure (✓ DONE)
Created `LivePortraitProcessor` class with:
- Device management (CUDA/CPU)
- Resolution support (256/384/512)
- Source image handling
- Motion vector processing
- Frame-by-frame inference interface

### 3. Test Infrastructure (✓ DONE)
Created comprehensive test script:
- `test_liveportrait.py` - End-to-end processor test
- Test image generation
- Motion vector generation
- Latency measurement
- Output frame saving

---

## ⚠️ Current Challenge

###Import Issues with LivePortrait
LivePortrait uses **relative imports** that don't work well when imported as a library:

```python
# In live_portrait_wrapper.py:
from .utils.timer import Timer  # Relative import fails
```

**Why This is Complex**:
1. LivePortrait was designed as a standalone app, not a library
2. Uses relative imports throughout the codebase
3. Requires specific directory structure to work
4. Has complex dependencies (gradio, safetensors, etc.)

---

## 🔧 Three Solutions (Choose One)

### Option 1: Wrapper Script (RECOMMENDED - Fast)
**Pros**: Works immediately, no code changes  
**Cons**: Adds ~50ms overhead for IPC

Create a subprocess wrapper that:
1. Runs LivePortrait in its own process
2. Communicates via pipes/sockets
3. Sends frames back to Pipecat

**Implementation**:
```python
# liveportrait_server.py (runs in subprocess)
- Load LivePortrait models
- Listen on socket for frames
- Process and return results

# LivePortraitProcessor (in Pipecat)
- Start subprocess
- Send frames via socket
- Receive animated frames
```

**Time**: ~2 hours to implement

### Option 2: Modify LivePortrait (CLEANEST - Slow)
**Pros**: Clean integration, no overhead  
**Cons**: Requires forking and modifying LivePortrait

Steps:
1. Fork LivePortrait repository
2. Convert all relative imports to absolute
3. Add `__init__.py` files
4. Make it pip-installable
5. Import directly in Pipecat

**Time**: ~1 day to properly refactor

### Option 3: ONNX Export (FASTEST - Best Long-term)
**Pros**: Maximum performance, no Python overhead  
**Cons**: Need to export models to ONNX first

Steps:
1. Export LivePortrait PyTorch models to ONNX
2. Use ONNXRuntime for inference
3. Direct integration in Pipecat

**Time**: ~4 hours to export and integrate

---

## 📊 What Works Right Now

✅ **Foundation Complete**:
- LivePortrait models downloaded (2.14GB)
- Processor class structure correct
- Pipeline integration points defined
- Test framework ready
- Motion vector system working

✅ **Phase 1.2 Fully Working**:
- STT (Groq Whisper) ✓
- LLM (Ollama Mistral) ✓
- TTS (Groq) ✓
- VAD (Silero) ✓
- Voice conversation working end-to-end

⚠️ **Phase 2 Needs**:
- LivePortrait integration method (choose from 3 options above)
- Test with real face image
- Latency measurement
- Output video stream

---

## 🎯 Recommended Next Steps

### Immediate (Option 1 - Subprocess Wrapper)

**Why**: Gets you a working avatar in ~2 hours with minimal risk

1. **Create LivePortrait Server** (30 min)
   ```bash
   cd F:\Projects\LLM\LivePortrait
   python liveportrait_server.py
   ```
   - Loads models once
   - Listens on port 8765
   - Accepts frame requests
   - Returns animated frames

2. **Update LivePortraitProcessor** (60 min)
   - Add socket client
   - Send frames to server
   - Receive results
   - Handle errors/timeouts

3. **Test Integration** (30 min)
   - Run conversation pipeline
   - Stream video output
   - Measure latency
   - Verify quality

**Expected Performance**:
- Subprocess overhead: ~10-20ms
- LivePortrait inference: ~12-15ms on RTX 3090
- **Total**: ~25-35ms per frame (still real-time at 30 FPS)

### Long-term (Option 3 - ONNX)

After validating with Option 1, optimize with ONNX:
- Export models to ONNX format
- Direct ONNXRuntime inference
- Target: <15ms per frame
- Best for production deployment

---

## 📂 File Structure

```
pipecat/
├── src/pipecat/processors/avatar/
│   ├── liveportrait_processor.py  ✓ Structure complete
│   ├── motion_vector_frame.py     ✓ Working
│   └── sadtalker_processor.py     ⏳ Phase 3
├── examples/avatar_conversation/
│   ├── test_liveportrait.py       ✓ Test ready
│   ├── backend.py                 ✓ Pipeline ready
│   └── config.yaml                ✓ Configured
└── scripts/
    ├── download_liveportrait_models.py  ✓ Complete
    └── liveportrait_server.py          ⏳ Need to create (Option 1)

LivePortrait/
├── pretrained_weights/  ✓ 2.14GB downloaded
│   ├── liveportrait/
│   │   ├── base_models/
│   │   └── retargeting_models/
│   └── insightface/
└── src/                 ✓ Code available
    ├── live_portrait_pipeline.py
    └── modules/
```

---

## 💡 Quick Decision Guide

**Want it working TODAY?**  
→ Option 1 (Subprocess) - 2 hours

**Want cleanest code?**  
→ Option 2 (Refactor) - 1 day

**Want best performance?**  
→ Option 3 (ONNX) - 4 hours

**My Recommendation**:  
Start with Option 1, validate everything works, then optimize to Option 3.

---

## 🔬 Testing Checklist (Once Integrated)

- [ ] Load reference face image
- [ ] Extract appearance features
- [ ] Generate motion from audio
- [ ] Render first frame
- [ ] Measure latency (<20ms target)
- [ ] Stream 30 frames
- [ ] Verify lip sync accuracy
- [ ] Check eye gaze
- [ ] Test head rotation
- [ ] Measure GPU memory usage
- [ ] Test with different faces
- [ ] Validate output quality

---

## ⏱️ Expected Timeline

| Task | Time | Status |
|------|------|--------|
| Download models | Done | ✅ |
| Create processor | Done | ✅ |
| Choose integration | 5 min | ⏳ |
| Implement wrapper | 2 hours | ⏳ |
| Test & validate | 1 hour | ⏳ |
| **Total** | **~3 hours** | **Ready to start** |

---

## 🎬 What You'll Get After Phase 2

A working conversational avatar that:
- Listens to your voice (STT)
- Thinks with local LLM (Ollama)
- Speaks naturally (TTS)
- **Shows photorealistic face animation** ← Phase 2
- Lip syncs perfectly
- Has natural eye movement
- Rotates head naturally

---

**Current Blocker**: Choose integration method (Option 1 recommended)  
**Ready**: Models downloaded, infrastructure complete  
**Need**: 2-3 hours implementation time  

Would you like me to implement Option 1 (subprocess wrapper) now?
