"""
Simple Avatar Lip-Sync Processor
================================

A lightweight lip-sync solution that works with any character image.
Uses audio analysis to drive simple mouth movements.

This is a simplified version that doesn't require heavy ML models.
For production quality, use LivePortrait or SadTalker.
"""

import asyncio
import io
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import logging

import numpy as np
import cv2
from PIL import Image

from pipecat.frames.frames import (
    Frame,
    ImageRawFrame,
    OutputImageRawFrame,
    AudioRawFrame,
    TTSAudioRawFrame,
)
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection

logger = logging.getLogger(__name__)


class MouthShape:
    """Predefined mouth shapes for phoneme-based lip sync."""
    CLOSED = 0      # m, b, p - lips together
    SLIGHTLY_OPEN = 1  # most consonants
    OPEN = 2        # a, ah
    WIDE = 3        # ee, i
    ROUNDED = 4     # o, oo
    RELAXED = 5     # neutral/rest


# Phoneme to mouth shape mapping (simplified)
PHONEME_SHAPES = {
    'silence': MouthShape.CLOSED,
    'low': MouthShape.SLIGHTLY_OPEN,
    'mid': MouthShape.OPEN,
    'high': MouthShape.WIDE,
}


class SimpleLipSyncProcessor(FrameProcessor):
    """
    Simple lip-sync processor that animates a character image based on audio.
    
    This processor:
    1. Accepts a source image (the character/avatar)
    2. Listens to TTS audio output
    3. Generates lip-synced video frames
    
    Uses energy-based mouth movement (simple but effective).
    For more realistic results, consider using Wav2Lip or similar.
    """
    
    def __init__(
        self,
        fps: int = 25,
        sample_rate: int = 16000,
        mouth_region: Optional[Tuple[int, int, int, int]] = None,  # x, y, w, h
    ):
        """
        Initialize the lip-sync processor.
        
        Args:
            fps: Frame rate for video output
            sample_rate: Expected audio sample rate
            mouth_region: Optional manual mouth region coordinates (x, y, width, height)
        """
        super().__init__()
        self.fps = fps
        self.sample_rate = sample_rate
        self.manual_mouth_region = mouth_region
        
        # State
        self._source_image: Optional[np.ndarray] = None
        self._mouth_region: Optional[Tuple[int, int, int, int]] = None
        self._current_mouth_shape = MouthShape.CLOSED
        self._frame_count = 0
        self._last_frame_time = 0
        self._audio_energy_buffer: List[float] = []
        
        # Mouth overlay images (will be generated)
        self._mouth_overlays: Dict[int, np.ndarray] = {}
        
        # Face detection (optional, for automatic mouth region detection)
        self._face_cascade = None
        try:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self._face_cascade = cv2.CascadeClassifier(cascade_path)
        except Exception as e:
            logger.warning(f"Face cascade not available: {e}")
        
        logger.info(f"SimpleLipSyncProcessor initialized (fps={fps})")
    
    def set_source_image(self, image: np.ndarray) -> bool:
        """
        Set the source/character image.
        
        Args:
            image: Source image as numpy array (H, W, 3) in RGB or BGR format
            
        Returns:
            True if image was set successfully
        """
        try:
            self._source_image = image.copy()
            
            # Detect or set mouth region
            if self.manual_mouth_region:
                self._mouth_region = self.manual_mouth_region
            else:
                self._mouth_region = self._detect_mouth_region(image)
            
            # Pre-generate mouth overlay shapes
            if self._mouth_region:
                self._generate_mouth_overlays()
            
            logger.info(f"Source image set: {image.shape}, mouth region: {self._mouth_region}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set source image: {e}")
            return False
    
    def _detect_mouth_region(self, image: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """
        Detect the mouth region in the image.
        
        Args:
            image: Source image
            
        Returns:
            Tuple of (x, y, width, height) for mouth region, or None
        """
        if self._face_cascade is None:
            # Fallback: assume mouth is in bottom-center third of image
            h, w = image.shape[:2]
            mouth_w = w // 3
            mouth_h = h // 6
            x = (w - mouth_w) // 2
            y = int(h * 0.65)  # 65% down from top
            logger.info(f"Using estimated mouth region: ({x}, {y}, {mouth_w}, {mouth_h})")
            return (x, y, mouth_w, mouth_h)
        
        try:
            # Convert to grayscale for detection
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            else:
                gray = image
            
            # Detect faces
            faces = self._face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50)
            )
            
            if len(faces) > 0:
                # Use largest face
                x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
                
                # Estimate mouth region within face
                mouth_x = x + int(w * 0.25)
                mouth_y = y + int(h * 0.6)
                mouth_w = int(w * 0.5)
                mouth_h = int(h * 0.25)
                
                logger.info(f"Detected mouth region: ({mouth_x}, {mouth_y}, {mouth_w}, {mouth_h})")
                return (mouth_x, mouth_y, mouth_w, mouth_h)
            else:
                # No face found, use center-bottom estimate
                h, w = image.shape[:2]
                mouth_w = w // 3
                mouth_h = h // 6
                x = (w - mouth_w) // 2
                y = int(h * 0.65)
                return (x, y, mouth_w, mouth_h)
                
        except Exception as e:
            logger.warning(f"Face detection failed: {e}")
            return None
    
    def _generate_mouth_overlays(self):
        """Generate simple mouth shape overlays for lip-sync."""
        if self._mouth_region is None or self._source_image is None:
            return
        
        x, y, w, h = self._mouth_region
        
        # Create mouth overlays for each shape
        for shape in [MouthShape.CLOSED, MouthShape.SLIGHTLY_OPEN, 
                      MouthShape.OPEN, MouthShape.WIDE, MouthShape.ROUNDED]:
            overlay = np.zeros((h, w, 4), dtype=np.uint8)  # RGBA
            
            # Draw mouth shape (simple ellipse-based)
            center = (w // 2, h // 2)
            
            if shape == MouthShape.CLOSED:
                # Thin horizontal line
                cv2.ellipse(overlay, center, (w // 3, h // 10), 0, 0, 360, (0, 0, 0, 100), -1)
            elif shape == MouthShape.SLIGHTLY_OPEN:
                cv2.ellipse(overlay, center, (w // 3, h // 6), 0, 0, 360, (40, 20, 20, 120), -1)
            elif shape == MouthShape.OPEN:
                cv2.ellipse(overlay, center, (w // 3, h // 3), 0, 0, 360, (50, 30, 30, 140), -1)
            elif shape == MouthShape.WIDE:
                cv2.ellipse(overlay, center, (w // 2, h // 4), 0, 0, 360, (45, 25, 25, 130), -1)
            elif shape == MouthShape.ROUNDED:
                cv2.ellipse(overlay, center, (w // 4, h // 3), 0, 0, 360, (48, 28, 28, 135), -1)
            
            self._mouth_overlays[shape] = overlay
        
        logger.info(f"Generated {len(self._mouth_overlays)} mouth overlays")
    
    def _audio_to_mouth_shape(self, audio_energy: float) -> int:
        """
        Convert audio energy to mouth shape.
        
        Args:
            audio_energy: Normalized audio energy [0, 1]
            
        Returns:
            MouthShape constant
        """
        if audio_energy < 0.05:
            return MouthShape.CLOSED
        elif audio_energy < 0.2:
            return MouthShape.SLIGHTLY_OPEN
        elif audio_energy < 0.5:
            return MouthShape.OPEN
        elif audio_energy < 0.8:
            return MouthShape.WIDE
        else:
            return MouthShape.ROUNDED
    
    def _render_frame(self, mouth_shape: int) -> np.ndarray:
        """
        Render a video frame with the current mouth shape.
        
        Args:
            mouth_shape: MouthShape constant
            
        Returns:
            Rendered frame as numpy array (H, W, 3) in RGB
        """
        if self._source_image is None:
            # Return a default avatar placeholder
            frame = np.zeros((512, 512, 3), dtype=np.uint8)
            # Dark gradient background
            for i in range(512):
                frame[i, :] = [20 + i//10, 20 + i//15, 40 + i//10]
            
            # Simple avatar circle (head)
            cv2.circle(frame, (256, 180), 80, (100, 100, 120), -1)
            cv2.circle(frame, (256, 180), 80, (60, 60, 80), 2)
            
            # Eyes
            cv2.circle(frame, (226, 165), 12, (200, 200, 220), -1)
            cv2.circle(frame, (286, 165), 12, (200, 200, 220), -1)
            cv2.circle(frame, (226, 165), 5, (40, 40, 60), -1)
            cv2.circle(frame, (286, 165), 5, (40, 40, 60), -1)
            
            # Mouth based on shape
            mouth_center = (256, 210)
            if mouth_shape == MouthShape.CLOSED:
                cv2.line(frame, (236, 210), (276, 210), (80, 60, 80), 3)
            elif mouth_shape == MouthShape.SLIGHTLY_OPEN:
                cv2.ellipse(frame, mouth_center, (20, 8), 0, 0, 360, (80, 40, 60), -1)
            elif mouth_shape == MouthShape.OPEN:
                cv2.ellipse(frame, mouth_center, (25, 15), 0, 0, 360, (60, 30, 50), -1)
            elif mouth_shape == MouthShape.WIDE:
                cv2.ellipse(frame, mouth_center, (30, 12), 0, 0, 360, (70, 35, 55), -1)
            else:  # ROUNDED
                cv2.ellipse(frame, mouth_center, (18, 18), 0, 0, 360, (65, 32, 52), -1)
            
            # Body silhouette
            cv2.ellipse(frame, (256, 400), (100, 80), 0, 0, 360, (80, 80, 100), -1)
            
            # Text hint
            cv2.putText(frame, "Upload Avatar Image", (140, 480), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (120, 120, 140), 1)
            
            return frame
        
        # Start with source image copy
        frame = self._source_image.copy()
        
        # Apply mouth overlay if available
        if mouth_shape in self._mouth_overlays and self._mouth_region:
            x, y, w, h = self._mouth_region
            overlay = self._mouth_overlays[mouth_shape]
            
            # Blend overlay onto frame
            if overlay.shape[2] == 4:  # RGBA
                alpha = overlay[:, :, 3:4] / 255.0
                overlay_rgb = overlay[:, :, :3]
                
                # Ensure dimensions match
                region = frame[y:y+h, x:x+w]
                if region.shape[:2] == overlay_rgb.shape[:2]:
                    blended = region * (1 - alpha) + overlay_rgb * alpha
                    frame[y:y+h, x:x+w] = blended.astype(np.uint8)
        
        return frame
    
    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """
        Process incoming frames.
        
        Handles:
        - ImageRawFrame: Set as source image
        - TTSAudioRawFrame: Analyze for lip-sync and generate video frames
        """
        await super().process_frame(frame, direction)
        
        if isinstance(frame, ImageRawFrame):
            # Decode and set source image
            try:
                image_data = np.frombuffer(frame.image, dtype=np.uint8)
                image = cv2.imdecode(image_data, cv2.IMREAD_COLOR)
                if image is not None:
                    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                    self.set_source_image(image_rgb)
            except Exception as e:
                logger.error(f"Failed to decode source image: {e}")
            
            # Pass through the image frame
            await self.push_frame(frame, direction)
            
        elif isinstance(frame, (TTSAudioRawFrame, AudioRawFrame)):
            # Analyze audio and generate video frame
            try:
                audio_data = np.frombuffer(frame.audio, dtype=np.int16).astype(np.float32)
                
                # Calculate energy
                if len(audio_data) > 0:
                    energy = np.sqrt(np.mean(audio_data ** 2)) / 32768.0  # Normalize
                else:
                    energy = 0.0
                
                # Smooth energy
                self._audio_energy_buffer.append(energy)
                if len(self._audio_energy_buffer) > 5:
                    self._audio_energy_buffer.pop(0)
                smooth_energy = np.mean(self._audio_energy_buffer)
                
                # Get mouth shape
                mouth_shape = self._audio_to_mouth_shape(smooth_energy)
                
                # Generate video frame at target FPS
                current_time = time.time()
                frame_interval = 1.0 / self.fps
                
                if current_time - self._last_frame_time >= frame_interval:
                    video_frame = self._render_frame(mouth_shape)
                    self._last_frame_time = current_time
                    self._frame_count += 1
                    
                    # Output raw RGB bytes (WebRTC transport expects uncompressed data)
                    frame_bytes = video_frame.astype(np.uint8).tobytes()
                    
                    # Create and push video frame (use OutputImageRawFrame for transport)
                    video_output = OutputImageRawFrame(
                        image=frame_bytes,
                        size=(video_frame.shape[1], video_frame.shape[0]),
                        format="RGB"
                    )
                    await self.push_frame(video_output, direction)
                
            except Exception as e:
                logger.error(f"Audio processing error: {e}")
            
            # Always pass through audio
            await self.push_frame(frame, direction)
            
        else:
            # Pass through other frames
            await self.push_frame(frame, direction)
    
    def __repr__(self) -> str:
        return f"SimpleLipSyncProcessor(fps={self.fps})"


class AvatarRenderer(FrameProcessor):
    """
    Complete avatar rendering pipeline.
    
    Combines:
    - Image loading and face detection
    - Audio-driven lip sync
    - Video frame generation and encoding
    
    This is the main class to use for avatar conversations.
    """
    
    def __init__(
        self,
        avatar_image_path: Optional[str] = None,
        fps: int = 25,
        output_size: Tuple[int, int] = (512, 512),
    ):
        """
        Initialize the avatar renderer.
        
        Args:
            avatar_image_path: Path to the avatar/character image
            fps: Output video frame rate
            output_size: Output video dimensions (width, height)
        """
        super().__init__()
        self.fps = fps
        self.output_size = output_size
        
        # Lip sync processor
        self._lip_sync = SimpleLipSyncProcessor(fps=fps)
        
        # Load avatar image if provided
        if avatar_image_path:
            self.load_avatar(avatar_image_path)
    
    def load_avatar(self, image_path: str) -> bool:
        """
        Load an avatar image.
        
        Args:
            image_path: Path to the avatar image file
            
        Returns:
            True if loaded successfully
        """
        try:
            path = Path(image_path)
            if not path.exists():
                logger.error(f"Avatar image not found: {image_path}")
                return False
            
            # Load image
            image = cv2.imread(str(path))
            if image is None:
                logger.error(f"Failed to decode image: {image_path}")
                return False
            
            # Convert to RGB and resize
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            image_resized = cv2.resize(image_rgb, self.output_size)
            
            # Set in lip sync processor
            return self._lip_sync.set_source_image(image_resized)
            
        except Exception as e:
            logger.error(f"Failed to load avatar: {e}")
            return False
    
    def set_avatar_from_bytes(self, image_bytes: bytes) -> bool:
        """
        Set avatar from image bytes.
        
        Args:
            image_bytes: Image data as bytes (JPEG, PNG, etc.)
            
        Returns:
            True if set successfully
        """
        try:
            # Decode image
            image_array = np.frombuffer(image_bytes, dtype=np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            
            if image is None:
                logger.error("Failed to decode image bytes")
                return False
            
            # Convert and resize
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            image_resized = cv2.resize(image_rgb, self.output_size)
            
            return self._lip_sync.set_source_image(image_resized)
            
        except Exception as e:
            logger.error(f"Failed to set avatar from bytes: {e}")
            return False
    
    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Process frames through the avatar pipeline."""
        await super().process_frame(frame, direction)
        
        if isinstance(frame, (TTSAudioRawFrame, AudioRawFrame)):
            # Process audio for lip sync and generate video frames
            try:
                audio_data = np.frombuffer(frame.audio, dtype=np.int16).astype(np.float32)
                
                # Calculate energy
                if len(audio_data) > 0:
                    energy = np.sqrt(np.mean(audio_data ** 2)) / 32768.0
                else:
                    energy = 0.0
                
                # Get mouth shape
                mouth_shape = self._lip_sync._audio_to_mouth_shape(energy)
                
                # Generate video frame
                video_frame = self._lip_sync._render_frame(mouth_shape)
                
                if video_frame is not None:
                    # Output raw RGB bytes (WebRTC transport expects uncompressed data)
                    frame_bytes = video_frame.astype(np.uint8).tobytes()
                    
                    # Create and push video frame (use OutputImageRawFrame for transport)
                    video_output = OutputImageRawFrame(
                        image=frame_bytes,
                        size=(video_frame.shape[1], video_frame.shape[0]),
                        format="RGB"
                    )
                    await self.push_frame(video_output, direction)
                
            except Exception as e:
                logger.error(f"Avatar render error: {e}")
            
            # Pass through audio
            await self.push_frame(frame, direction)
        else:
            # Pass through other frames
            await self.push_frame(frame, direction)
    
    def __repr__(self) -> str:
        return f"AvatarRenderer(fps={self.fps}, size={self.output_size})"
