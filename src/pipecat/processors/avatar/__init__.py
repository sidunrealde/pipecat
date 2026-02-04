"""
Avatar processors for real-time face reenactment and motion synthesis.

This module provides processors for driving photorealistic avatar animations
using audio and motion data.
"""

from .motion_vector_frame import MotionVectorFrame
from .liveportrait_processor import LivePortraitProcessor
from .sadtalker_processor import SadTalkerMotionProcessor

__all__ = [
    "MotionVectorFrame",
    "LivePortraitProcessor",
    "SadTalkerMotionProcessor",
]
