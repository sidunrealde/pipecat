"""
Test LivePortrait processor with a reference image.

This script:
1. Loads the LivePortrait processor
2. Sets a reference image (or uses a test face)
3. Generates test motion vectors
4. Renders animated frames
5. Measures latency
"""

import asyncio
import logging
import sys
import time
from pathlib import Path

import numpy as np
import cv2

# Add pipecat to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from pipecat.processors.avatar.liveportrait_processor import LivePortraitProcessor
from pipecat.processors.avatar.motion_vector_frame import MotionVectorFrame
from pipecat.frames.frames import ImageRawFrame

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_test_image(size=512):
    """Create a simple test face image if no reference is provided."""
    logger.info("Creating test image...")
    
    # Create a blank canvas
    img = np.ones((size, size, 3), dtype=np.uint8) * 230
    
    # Draw a simple face
    # Head circle
    cv2.circle(img, (size//2, size//2), size//3, (200, 150, 150), -1)
    
    # Eyes
    eye_y = size//2 - size//8
    cv2.circle(img, (size//2 - size//8, eye_y), size//20, (50, 50, 50), -1)
    cv2.circle(img, (size//2 + size//8, eye_y), size//20, (50, 50, 50), -1)
    
    # Nose
    pts = np.array([[size//2, size//2], 
                    [size//2 - size//40, size//2 + size//12],
                    [size//2 + size//40, size//2 + size//12]], np.int32)
    cv2.fillPoly(img, [pts], (180, 120, 120))
    
    # Mouth
    cv2.ellipse(img, (size//2, size//2 + size//6), 
                (size//8, size//16), 0, 0, 180, (100, 50, 50), 2)
    
    logger.info(f"✓ Test image created: {img.shape}")
    return img


def generate_test_motions(num_frames=10):
    """Generate test motion vectors for animation."""
    motions = []
    
    for i in range(num_frames):
        t = i / num_frames
        
        # Sinusoidal head motion (nodding)
        rotation = np.array([
            np.sin(t * 2 * np.pi * 0.5) * 0.1,  # pitch (nod)
            np.sin(t * 2 * np.pi * 0.3) * 0.05,  # yaw (turn)
            0.0,  # roll
        ])
        
        # Slight translation
        translation = np.array([
            np.sin(t * 2 * np.pi * 0.4) * 0.02,  # x
            0.0,  # y
            0.0,  # z
        ])
        
        # Eye gaze
        eye_gaze = np.array([
            np.sin(t * 2 * np.pi * 0.6) * 0.3,  # horizontal
            np.sin(t * 2 * np.pi * 0.4) * 0.2,  # vertical
        ])
        
        motion = MotionVectorFrame(
            motion_coefficients=np.concatenate([rotation, translation]),
            eye_gaze=eye_gaze,
            timestamp=t,
        )
        motions.append(motion)
    
    logger.info(f"✓ Generated {num_frames} test motion vectors")
    return motions


async def test_liveportrait():
    """Test LivePortrait processor end-to-end."""
    
    logger.info("="*70)
    logger.info("LIVEPORTRAIT PROCESSOR TEST")
    logger.info("="*70)
    
    # 1. Initialize processor
    logger.info("\n[1/5] Initializing LivePortrait processor...")
    try:
        processor = LivePortraitProcessor(
            device="cuda",
            resolution=512,
        )
        logger.info("    ✓ Processor created")
    except Exception as e:
        logger.error(f"    ❌ Failed to create processor: {e}")
        return
    
    # 2. Load reference image
    logger.info("\n[2/5] Loading reference image...")
    
    # Check for user-provided image
    ref_image_path = Path("reference_face.jpg")
    if ref_image_path.exists():
        logger.info(f"    Using reference image: {ref_image_path}")
        ref_image = cv2.imread(str(ref_image_path))
        ref_image = cv2.cvtColor(ref_image, cv2.COLOR_BGR2RGB)
    else:
        logger.info("    No reference_face.jpg found, using test image")
        ref_image = create_test_image(512)
    
    # Resize if needed
    if ref_image.shape[0] != 512 or ref_image.shape[1] != 512:
        logger.info(f"    Resizing from {ref_image.shape} to (512, 512)")
        ref_image = cv2.resize(ref_image, (512, 512))
    
    try:
        processor.set_source_image(ref_image)
        logger.info("    ✓ Reference image set")
    except Exception as e:
        logger.error(f"    ❌ Failed to set reference image: {e}")
        logger.error(f"    Error details: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return
    
    # 3. Generate test motions
    logger.info("\n[3/5] Generating test motion vectors...")
    test_motions = generate_test_motions(10)
    
    # 4. Process frames and measure latency
    logger.info("\n[4/5] Processing frames...")
    latencies = []
    
    for i, motion in enumerate(test_motions):
        start_time = time.time()
        
        try:
            output_frame = await processor.process_frame(motion)
            
            latency = (time.time() - start_time) * 1000  # ms
            latencies.append(latency)
            
            logger.info(f"    Frame {i+1}/10: {latency:.2f}ms")
            
            # Save first and last frame for visual inspection
            if i == 0 or i == len(test_motions) - 1:
                if isinstance(output_frame, ImageRawFrame):
                    img_data = np.frombuffer(output_frame.image, dtype=np.uint8)
                    img = cv2.imdecode(img_data, cv2.IMREAD_COLOR)
                    cv2.imwrite(f"output_frame_{i}.jpg", img)
                    logger.info(f"        Saved: output_frame_{i}.jpg")
        
        except Exception as e:
            logger.error(f"    ❌ Frame {i+1} failed: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # 5. Report results
    logger.info("\n[5/5] Results:")
    if latencies:
        logger.info(f"    Frames processed: {len(latencies)}")
        logger.info(f"    Average latency: {np.mean(latencies):.2f}ms")
        logger.info(f"    Min latency: {np.min(latencies):.2f}ms")
        logger.info(f"    Max latency: {np.max(latencies):.2f}ms")
        logger.info(f"    Target: <20ms for real-time (60 FPS = 16.67ms)")
        
        if np.mean(latencies) < 20:
            logger.info("    ✓ PASSED: Latency within real-time target!")
        else:
            logger.warning("    ⚠ Latency higher than target (but may be acceptable for 30 FPS)")
    else:
        logger.error("    ❌ No frames processed successfully")
    
    logger.info("\n" + "="*70)
    logger.info("TEST COMPLETE")
    logger.info("="*70)


if __name__ == "__main__":
    asyncio.run(test_liveportrait())
