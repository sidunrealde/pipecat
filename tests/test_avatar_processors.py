"""
Tests for avatar processors - Phase 1.3

Tests for:
- MotionVectorFrame data structure
- LivePortraitProcessor (placeholder)
- SadTalkerMotionProcessor (placeholder)
"""

import pytest
import numpy as np

from src.pipecat.processors.avatar import (
    MotionVectorFrame,
    LivePortraitProcessor,
    SadTalkerMotionProcessor,
)


class TestMotionVectorFrame:
    """Test MotionVectorFrame data structure."""
    
    def test_creation_with_numpy_arrays(self):
        """Test creating MotionVectorFrame with numpy arrays."""
        motion = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6])
        eye_gaze = np.array([0.01, 0.02])
        
        frame = MotionVectorFrame(
            motion_coefficients=motion,
            eye_gaze=eye_gaze,
            timestamp=1.5,
            frame_index=10,
        )
        
        assert frame.motion_coefficients.shape == (6,)
        assert frame.eye_gaze.shape == (2,)
        assert frame.timestamp == 1.5
        assert frame.frame_index == 10
        assert np.allclose(frame.motion_coefficients, motion)
    
    def test_creation_with_lists(self):
        """Test creating MotionVectorFrame with lists."""
        motion = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
        eye_gaze = [0.01, 0.02]
        
        frame = MotionVectorFrame(
            motion_coefficients=motion,
            eye_gaze=eye_gaze,
        )
        
        assert isinstance(frame.motion_coefficients, np.ndarray)
        assert isinstance(frame.eye_gaze, np.ndarray)
    
    def test_default_eye_gaze(self):
        """Test default eye gaze when not provided."""
        motion = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6])
        frame = MotionVectorFrame(motion_coefficients=motion)
        
        assert np.allclose(frame.eye_gaze, [0.0, 0.0])
    
    def test_metadata(self):
        """Test metadata storage."""
        motion = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6])
        metadata = {"source": "sadtalker", "confidence": 0.95}
        
        frame = MotionVectorFrame(
            motion_coefficients=motion,
            metadata=metadata,
        )
        
        assert frame.metadata == metadata
    
    def test_repr(self):
        """Test string representation."""
        motion = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6])
        frame = MotionVectorFrame(
            motion_coefficients=motion,
            timestamp=1.5,
            frame_index=5,
        )
        
        repr_str = repr(frame)
        assert "MotionVectorFrame" in repr_str
        assert "motion_shape=(6,)" in repr_str
        assert "timestamp=1.500" in repr_str
        assert "frame_index=5" in repr_str


class TestLivePortraitProcessor:
    """Test LivePortrait processor (placeholder tests for Phase 2)."""
    
    def test_initialization(self):
        """Test processor initialization."""
        processor = LivePortraitProcessor(
            device="cuda",
            resolution=512,
            enable_gfpgan=False,
        )
        
        assert processor.device == "cuda"
        assert processor.resolution == 512
        assert processor.enable_gfpgan == False
    
    def test_repr(self):
        """Test string representation."""
        processor = LivePortraitProcessor(
            device="cuda",
            resolution=512,
            enable_gfpgan=True,
        )
        
        repr_str = repr(processor)
        assert "LivePortraitProcessor" in repr_str
        assert "device=cuda" in repr_str
        assert "resolution=512" in repr_str
        assert "gfpgan=True" in repr_str


class TestSadTalkerMotionProcessor:
    """Test SadTalker motion processor (placeholder tests for Phase 3)."""
    
    def test_initialization(self):
        """Test processor initialization."""
        processor = SadTalkerMotionProcessor(
            device="cuda",
            fps=25,
        )
        
        assert processor.device == "cuda"
        assert processor.fps == 25
    
    def test_placeholder_motion_generation(self):
        """Test placeholder motion generation."""
        processor = SadTalkerMotionProcessor()
        
        motion = processor._generate_placeholder_motion()
        
        assert motion.shape == (6,)
        assert motion.dtype == np.float32
    
    def test_repr(self):
        """Test string representation."""
        processor = SadTalkerMotionProcessor(
            device="cuda",
            fps=30,
        )
        
        repr_str = repr(processor)
        assert "SadTalkerMotionProcessor" in repr_str
        assert "device=cuda" in repr_str
        assert "fps=30" in repr_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
