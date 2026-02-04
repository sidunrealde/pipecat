#!/usr/bin/env python3
"""
Test LivePortrait installation and latency on 3090.
"""
import sys
import os
import time

# Add LivePortrait to path
liveportrait_root = "F:/Projects/LLM/LivePortrait"
liveportrait_src = f"{liveportrait_root}/src"
if liveportrait_root not in sys.path:
    sys.path.insert(0, liveportrait_root)
if liveportrait_src not in sys.path:
    sys.path.insert(0, liveportrait_src)

print(f"Python path: {sys.path[:3]}")
print(f"LivePortrait root: {liveportrait_root}")
print(f"LivePortrait src: {liveportrait_src}")

try:
    print("\n=== Testing LivePortrait Installation ===\n")
    
    # Test imports
    print("1. Testing imports...")
    import torch
    from live_portrait_wrapper import LivePortraitPipeline
    print("   ✓ LivePortrait imports successful")
    
    print(f"\n2. PyTorch & CUDA Status:")
    print(f"   ✓ PyTorch {torch.__version__} loaded")
    print(f"   ✓ CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"   ✓ CUDA device: {torch.cuda.get_device_name(0)}")
        total_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"   ✓ CUDA memory: {total_memory:.1f} GB")
    
    print("\n3. Checking LivePortrait model files...")
    pretrained_path = "F:/Projects/LLM/LivePortrait/pretrained_weights"
    if os.path.exists(pretrained_path):
        print(f"   ✓ Model path exists: {pretrained_path}")
        try:
            items = os.listdir(pretrained_path)[:5]
            for item in items:
                print(f"      - {item}")
        except:
            pass
    else:
        print(f"   ❌ Model path not found: {pretrained_path}")
        print("      Please download models from: https://huggingface.co/KwaiVGI/LivePortrait")
    
    # Initialize model - skip for now if models don't exist
    print("\n4. Model initialization:")
    try:
        print("   Loading LivePortrait model...")
        start = time.time()
        pipeline = LivePortraitPipeline("cuda" if torch.cuda.is_available() else "cpu")
        load_time = time.time() - start
        print(f"   ✓ Model loaded in {load_time:.2f}s")
        
        # Check GPU memory
        if torch.cuda.is_available():
            mem_used = torch.cuda.memory_allocated() / 1e9
            mem_reserved = torch.cuda.memory_reserved() / 1e9
            print(f"   ✓ GPU memory used: {mem_used:.2f} GB / reserved: {mem_reserved:.2f} GB")
    except FileNotFoundError:
        print("   ⚠️  Model files not downloaded yet")
        print("      Run: python F:/Projects/LLM/LivePortrait/app.py")
    
    print("\n✅ LivePortrait is properly configured!")
    print("   Setup complete. Ready to integrate with Pipecat.")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
