"""
Export LivePortrait PyTorch models to ONNX format - Using official API.

This uses LivePortrait's built-in model loading to ensure correct initialization.

Exports:
1. Appearance Feature Extractor
2. Motion Extractor  
3. SPADE Generator
4. Warping Module
"""

import sys
import torch
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# LivePortrait paths
LIVEPORTRAIT_PATH = Path("F:/Projects/LLM/LivePortrait")
MODEL_DIR = LIVEPORTRAIT_PATH / "pretrained_weights"
ONNX_OUTPUT_DIR = MODEL_DIR / "onnx_models"

sys.path.insert(0, str(LIVEPORTRAIT_PATH / "src"))


def export_appearance_extractor():
    """Export appearance feature extractor to ONNX."""
    logger.info("\n[1/4] Exporting Appearance Feature Extractor...")
    
    try:
        from live_portrait_wrapper import LivePortraitWrapper
        
        wrapper = LivePortraitWrapper(device='cpu')
        model = wrapper.appearance_extractor
        model.eval()
        
        # Create dummy input (batch, channels, height, width)
        dummy_input = torch.randn(1, 3, 256, 256)
        
        # Export to ONNX
        output_path = ONNX_OUTPUT_DIR / "appearance_feature_extractor.onnx"
        torch.onnx.export(
            model,
            dummy_input,
            str(output_path),
            export_params=True,
            opset_version=14,
            do_constant_folding=True,
            input_names=['image'],
            output_names=['features'],
            dynamic_axes={
                'image': {0: 'batch_size'},
                'features': {0: 'batch_size'}
            }
        )
        
        logger.info(f"    ✓ Exported to: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"    ❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def export_motion_extractor():
    """Export motion extractor to ONNX."""
    logger.info("\n[2/4] Exporting Motion Extractor...")
    
    try:
        from live_portrait_wrapper import LivePortraitWrapper
        
        wrapper = LivePortraitWrapper(device='cpu')
        model = wrapper.motion_extractor
        model.eval()
        
        # Create dummy input
        dummy_input = torch.randn(1, 3, 256, 256)
        
        # Export to ONNX
        output_path = ONNX_OUTPUT_DIR / "motion_extractor.onnx"
        torch.onnx.export(
            model,
            dummy_input,
            str(output_path),
            export_params=True,
            opset_version=14,
            do_constant_folding=True,
            input_names=['image'],
            output_names=['motion'],
            dynamic_axes={
                'image': {0: 'batch_size'},
                'motion': {0: 'batch_size'}
            }
        )
        
        logger.info(f"    ✓ Exported to: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"    ❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def export_generator():
    """Export SPADE generator to ONNX."""
    logger.info("\n[3/4] Exporting SPADE Generator...")
    
    try:
        from live_portrait_wrapper import LivePortraitWrapper
        
        wrapper = LivePortraitWrapper(device='cpu')
        model = wrapper.spade_generator
        model.eval()
        
        # Create dummy inputs (appearance feature + motion feature)
        dummy_app = torch.randn(1, 256, 16, 16)
        dummy_motion = torch.randn(1, 21, 16, 16)
        
        # Export to ONNX
        output_path = ONNX_OUTPUT_DIR / "spade_generator.onnx"
        torch.onnx.export(
            model,
            (dummy_app, dummy_motion),
            str(output_path),
            export_params=True,
            opset_version=14,
            do_constant_folding=True,
            input_names=['appearance', 'motion_features'],
            output_names=['image'],
            dynamic_axes={
                'appearance': {0: 'batch_size'},
                'motion_features': {0: 'batch_size'},
                'image': {0: 'batch_size'}
            }
        )
        
        logger.info(f"    ✓ Exported to: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"    ❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def export_warping_module():
    """Export warping module to ONNX."""
    logger.info("\n[4/4] Exporting Warping Module...")
    
    try:
        from live_portrait_wrapper import LivePortraitWrapper
        
        wrapper = LivePortraitWrapper(device='cpu')
        model = wrapper.warping_module
        model.eval()
        
        # Create dummy inputs (source image + keypoints)
        dummy_source = torch.randn(1, 3, 256, 256)
        dummy_kp = torch.randn(1, 10, 2)  # 10 keypoints
        
        # Export to ONNX
        output_path = ONNX_OUTPUT_DIR / "warping_network.onnx"
        torch.onnx.export(
            model,
            (dummy_source, dummy_kp),
            str(output_path),
            export_params=True,
            opset_version=14,
            do_constant_folding=True,
            input_names=['source_image', 'keypoints'],
            output_names=['warped_image'],
            dynamic_axes={
                'source_image': {0: 'batch_size'},
                'keypoints': {0: 'batch_size'},
                'warped_image': {0: 'batch_size'}
            }
        )
        
        logger.info(f"    ✓ Exported to: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"    ❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Export all LivePortrait models to ONNX."""
    logger.info("="*70)
    logger.info("LIVEPORTRAIT ONNX EXPORT")
    logger.info("="*70)
    
    # Create output directory
    ONNX_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"\nOutput directory: {ONNX_OUTPUT_DIR}\n")
    
    # Export all models
    results = {
        'appearance_extractor': export_appearance_extractor(),
        'motion_extractor': export_motion_extractor(),
        'generator': export_generator(),
        'warping_module': export_warping_module(),
    }
    
    # Summary
    logger.info("\n" + "="*70)
    logger.info("EXPORT SUMMARY")
    logger.info("="*70)
    
    success_count = sum(results.values())
    total_count = len(results)
    
    for name, success in results.items():
        status = "✓" if success else "❌"
        logger.info(f"  {status} {name}")
    
    logger.info(f"\nTotal: {success_count}/{total_count} models exported successfully")
    
    if success_count == total_count:
        logger.info("\n🎉 All models exported! Ready for ONNX inference.")
        logger.info(f"\nONNX models location: {ONNX_OUTPUT_DIR}")
    else:
        logger.warning("\n⚠ Some exports failed. Check errors above.")
    
    logger.info("="*70)


if __name__ == "__main__":
    main()
