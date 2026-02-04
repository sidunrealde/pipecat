"""
Motion vector frame for carrying 3D motion data between processors.
"""
from typing import Optional

import numpy as np

from pipecat.frames.frames import Frame


class MotionVectorFrame(Frame):
    """
    Carries 3D motion coefficients from SadTalker for face reenactment.
    
    This frame type encapsulates all motion data needed to drive LivePortrait:
    - Head pose (rotation, pitch, yaw, roll)
    - Facial expressions (emotion coefficients)
    - Eye gaze direction
    
    Attributes:
        motion_coefficients: numpy array of shape (6,) containing head pose and expression data
        eye_gaze: numpy array of shape (2,) containing eye direction
        timestamp: float timestamp for synchronization with audio
        frame_index: int frame number for sequencing
        metadata: dict for additional motion information
    """
    
    def __init__(
        self,
        motion_coefficients: np.ndarray,
        eye_gaze: Optional[np.ndarray] = None,
        timestamp: float = 0.0,
        frame_index: int = 0,
        metadata: Optional[dict] = None,
    ):
        """
        Initialize a MotionVectorFrame.
        
        Args:
            motion_coefficients: Array of motion data, shape (6,) or (3,) for head pose
            eye_gaze: Array of eye gaze data, shape (2,)
            timestamp: Synchronization timestamp in seconds
            frame_index: Sequential frame number
            metadata: Additional motion metadata
        """
        super().__init__()
        
        # Ensure motion coefficients are numpy arrays
        if not isinstance(motion_coefficients, np.ndarray):
            motion_coefficients = np.array(motion_coefficients, dtype=np.float32)
        else:
            motion_coefficients = motion_coefficients.astype(np.float32)
        
        self.motion_coefficients = motion_coefficients
        
        # Default eye gaze if not provided
        if eye_gaze is None:
            eye_gaze = np.array([0.0, 0.0], dtype=np.float32)
        elif not isinstance(eye_gaze, np.ndarray):
            eye_gaze = np.array(eye_gaze, dtype=np.float32)
        else:
            eye_gaze = eye_gaze.astype(np.float32)
        
        self.eye_gaze = eye_gaze
        self.timestamp = timestamp
        self.frame_index = frame_index
        self.metadata = metadata or {}
    
    def __repr__(self) -> str:
        return (
            f"MotionVectorFrame("
            f"motion_shape={self.motion_coefficients.shape}, "
            f"timestamp={self.timestamp:.3f}, "
            f"frame_index={self.frame_index})"
        )
