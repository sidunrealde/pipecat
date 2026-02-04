#!/usr/bin/env python3
"""
Comprehensive System Test for Avatar Conversation Project

Tests:
1. ✓ Pipecat installation and imports
2. ✓ Avatar processor modules
3. ✓ Frame structures
4. ✓ GPU/CUDA availability
5. ✓ All dependencies installed
6. ✓ Configuration loading

Run: python test_system.py
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, List, Tuple

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text: str):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}{Colors.ENDC}\n")

def print_test(name: str, passed: bool, details: str = ""):
    status = f"{Colors.OKGREEN}✓ PASS{Colors.ENDC}" if passed else f"{Colors.FAIL}✗ FAIL{Colors.ENDC}"
    print(f"  {status} | {name}")
    if details:
        print(f"       {Colors.OKCYAN}{details}{Colors.ENDC}")

def print_warning(text: str):
    print(f"  {Colors.WARNING}⚠ {text}{Colors.ENDC}")

def print_info(text: str):
    print(f"  {Colors.OKBLUE}ℹ {text}{Colors.ENDC}")

def test_pipecat_installation() -> bool:
    """Test Pipecat framework installation."""
    print_header("1. Testing Pipecat Installation")
    
    try:
        import pipecat
        from pipecat.frames.frames import Frame
        from pipecat.processors.frame_processor import FrameProcessor
        
        print_test("Pipecat import", True, f"Version: {pipecat.__version__ if hasattr(pipecat, '__version__') else 'unknown'}")
        print_test("Frame class import", True)
        print_test("FrameProcessor class import", True)
        
        return True
    except ImportError as e:
        print_test("Pipecat installation", False, str(e))
        return False

def test_avatar_processors() -> bool:
    """Test avatar processor modules."""
    print_header("2. Testing Avatar Processor Modules")
    
    try:
        from src.pipecat.processors.avatar import (
            MotionVectorFrame,
            LivePortraitProcessor,
            SadTalkerMotionProcessor,
        )
        
        print_test("MotionVectorFrame import", True)
        print_test("LivePortraitProcessor import", True)
        print_test("SadTalkerMotionProcessor import", True)
        
        return True
    except ImportError as e:
        print_test("Avatar processors import", False, str(e))
        return False

def test_motion_vector_frame() -> bool:
    """Test MotionVectorFrame functionality."""
    print_header("3. Testing MotionVectorFrame")
    
    try:
        import numpy as np
        from src.pipecat.processors.avatar import MotionVectorFrame
        
        # Test with numpy arrays
        motion = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6], dtype=np.float32)
        eye_gaze = np.array([0.01, 0.02], dtype=np.float32)
        
        frame = MotionVectorFrame(
            motion_coefficients=motion,
            eye_gaze=eye_gaze,
            timestamp=1.5,
            frame_index=10,
            metadata={"test": "value"}
        )
        
        print_test("Frame creation with numpy arrays", True)
        print_test("Motion coefficients shape", frame.motion_coefficients.shape == (6,), f"Shape: {frame.motion_coefficients.shape}")
        print_test("Eye gaze shape", frame.eye_gaze.shape == (2,), f"Shape: {frame.eye_gaze.shape}")
        print_test("Timestamp", frame.timestamp == 1.5)
        print_test("Frame index", frame.frame_index == 10)
        print_test("Metadata", frame.metadata.get("test") == "value")
        print_test("String representation", "MotionVectorFrame" in repr(frame))
        
        return True
    except Exception as e:
        print_test("MotionVectorFrame tests", False, str(e))
        return False

def test_processors() -> bool:
    """Test processor initialization."""
    print_header("4. Testing Processor Classes")
    
    try:
        from src.pipecat.processors.avatar import LivePortraitProcessor, SadTalkerMotionProcessor
        
        # Test LivePortrait
        lp = LivePortraitProcessor(device="cpu", resolution=512, enable_gfpgan=False)
        print_test("LivePortraitProcessor initialization", True, f"Device: {lp.device}")
        print_test("LivePortrait configuration", lp.resolution == 512 and lp.enable_gfpgan == False)
        
        # Test SadTalker
        st = SadTalkerMotionProcessor(device="cpu", fps=25)
        print_test("SadTalkerMotionProcessor initialization", True, f"Device: {st.device}")
        print_test("SadTalker configuration", st.fps == 25)
        
        # Test placeholder motion generation
        motion = st._generate_placeholder_motion()
        print_test("Placeholder motion generation", motion.shape == (6,), f"Shape: {motion.shape}")
        
        return True
    except Exception as e:
        print_test("Processor initialization", False, str(e))
        return False

def test_gpu_cuda() -> bool:
    """Test GPU/CUDA availability."""
    print_header("5. Testing GPU/CUDA Setup")
    
    try:
        import torch
        
        cuda_available = torch.cuda.is_available()
        print_test("PyTorch installation", True, f"Version: {torch.__version__}")
        print_test("CUDA availability", cuda_available)
        
        if cuda_available:
            device_name = torch.cuda.get_device_name(0)
            device_props = torch.cuda.get_device_properties(0)
            total_memory_gb = device_props.total_memory / 1e9
            
            print_test("CUDA device detection", True, device_name)
            print_test("GPU memory", True, f"{total_memory_gb:.1f} GB")
            
            # Check if it's a 3090
            if "3090" in device_name or "RTX 3090" in device_name:
                print_info(f"Detected RTX 3090 - Perfect for this project!")
            elif "4090" in device_name:
                print_info(f"Detected RTX 4090 - Excellent performance!")
            else:
                print_info(f"GPU detected but not RTX 3090 - may have different latencies")
        else:
            print_warning("CUDA not available - will use CPU (much slower)")
        
        return True
    except ImportError:
        print_test("PyTorch installation", False, "PyTorch not installed")
        return False
    except Exception as e:
        print_test("GPU/CUDA test", False, str(e))
        return False

def test_dependencies() -> bool:
    """Test critical dependencies."""
    print_header("6. Testing Critical Dependencies")
    
    dependencies = [
        ("numpy", "Numerical computing"),
        ("cv2", "Computer vision"),
        ("PIL", "Image processing"),
        ("pyyaml", "Configuration"),
        ("pydantic", "Data validation"),
    ]
    
    all_passed = True
    for package, description in dependencies:
        try:
            __import__(package)
            print_test(f"{package}", True, description)
        except ImportError:
            print_test(f"{package}", False, f"Missing: {description}")
            all_passed = False
    
    return all_passed

def test_project_structure() -> bool:
    """Test project directory structure."""
    print_header("7. Testing Project Structure")
    
    root = Path(".")
    required_dirs = [
        ("src/pipecat/processors/avatar", "Avatar processors"),
        ("examples/avatar_conversation", "Example application"),
        ("tests", "Test suite"),
    ]
    
    all_passed = True
    for dir_path, description in required_dirs:
        full_path = root / dir_path
        exists = full_path.exists()
        print_test(dir_path, exists, description)
        if not exists:
            all_passed = False
    
    # Check for key files
    required_files = [
        ("src/pipecat/processors/avatar/__init__.py", "Avatar module init"),
        ("src/pipecat/processors/avatar/motion_vector_frame.py", "Motion frame"),
        ("src/pipecat/processors/avatar/liveportrait_processor.py", "LivePortrait processor"),
        ("src/pipecat/processors/avatar/sadtalker_processor.py", "SadTalker processor"),
        ("tests/test_avatar_processors.py", "Avatar tests"),
        ("examples/avatar_conversation/backend.py", "Backend pipeline"),
        ("examples/avatar_conversation/config.yaml", "Configuration"),
        ("PLAN.md", "Implementation plan"),
    ]
    
    print("\n  Key files:")
    for file_path, description in required_files:
        full_path = root / file_path
        exists = full_path.exists()
        status = f"{Colors.OKGREEN}✓{Colors.ENDC}" if exists else f"{Colors.FAIL}✗{Colors.ENDC}"
        print(f"    {status} {file_path}")
        if not exists:
            all_passed = False
    
    return all_passed

def test_configuration() -> bool:
    """Test configuration loading."""
    print_header("8. Testing Configuration")
    
    try:
        import yaml
        
        config_path = Path("examples/avatar_conversation/config.yaml")
        if not config_path.exists():
            print_test("Config file exists", False, "config.yaml not found")
            return False
        
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        print_test("Configuration loading", True, "YAML parsed successfully")
        
        # Check for required sections
        required_sections = ["stt", "llm", "tts", "vad", "transport", "pipeline"]
        for section in required_sections:
            exists = section in config
            print_test(f"Config section: {section}", exists)
        
        return True
    except Exception as e:
        print_test("Configuration test", False, str(e))
        return False

def run_quick_import_test() -> bool:
    """Quick test of all imports."""
    print_header("9. Quick Import Test")
    
    try:
        # Import all modules
        import pipecat
        from pipecat.frames.frames import Frame
        from pipecat.processors.frame_processor import FrameProcessor
        from src.pipecat.processors.avatar import (
            MotionVectorFrame,
            LivePortraitProcessor,
            SadTalkerMotionProcessor,
        )
        
        print_test("All imports successful", True)
        print_info("Ready for Phase 1.2 implementation")
        
        return True
    except Exception as e:
        print_test("Import test", False, str(e))
        return False

def main():
    """Run all tests."""
    print(f"\n{Colors.BOLD}{Colors.OKCYAN}")
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║   Avatar Conversation System - Comprehensive Test Suite            ║")
    print("║   Testing Phase 1 Foundation Setup                                ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.ENDC}\n")
    
    # Run all tests
    results = {
        "Pipecat Installation": test_pipecat_installation(),
        "Avatar Processors": test_avatar_processors(),
        "MotionVectorFrame": test_motion_vector_frame(),
        "Processor Classes": test_processors(),
        "GPU/CUDA Setup": test_gpu_cuda(),
        "Dependencies": test_dependencies(),
        "Project Structure": test_project_structure(),
        "Configuration": test_configuration(),
        "Import Test": run_quick_import_test(),
    }
    
    # Summary
    print_header("Test Summary")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = f"{Colors.OKGREEN}✓{Colors.ENDC}" if result else f"{Colors.FAIL}✗{Colors.ENDC}"
        print(f"  {status} {test_name}")
    
    print(f"\n{Colors.BOLD}Results: {passed}/{total} test suites passed{Colors.ENDC}")
    
    if passed == total:
        print(f"\n{Colors.OKGREEN}{Colors.BOLD}✓ All systems operational!{Colors.ENDC}")
        print(f"{Colors.OKGREEN}Ready to proceed with Phase 1.2 implementation.{Colors.ENDC}\n")
        return 0
    else:
        print(f"\n{Colors.FAIL}{Colors.BOLD}✗ Some tests failed{Colors.ENDC}")
        print(f"{Colors.FAIL}Please review errors above before proceeding.{Colors.ENDC}\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
