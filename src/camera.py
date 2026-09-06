"""Camera capture management and synthetic test video generation.

Provides robust OpenCV webcam acquisition with Windows DirectShow support,
graceful fallback, error recovery, and synthetic video feed for automated testing.
"""

import math
import time
from typing import Optional, Tuple
import cv2
import numpy as np


class CameraManager:
    """Manages webcam capture lifecycle, backend selection, and frame acquisition."""

    def __init__(
        self,
        camera_id: int = 0,
        width: int = 640,
        height: int = 480,
        fps: int = 30,
        use_dshow: bool = True,
    ):
        self.camera_id = camera_id
        self.target_w = width
        self.target_h = height
        self.target_fps = fps
        self.use_dshow = use_dshow

        self.cap: Optional[cv2.VideoCapture] = None
        self.actual_w = width
        self.actual_h = height
        self._is_opened = False

    def open(self) -> bool:
        """Opens camera using optimal backend on Windows."""
        self.release()

        # Try DirectShow on Windows first for fast startup
        if self.use_dshow:
            self.cap = cv2.VideoCapture(self.camera_id, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                # Fallback to default
                self.cap = cv2.VideoCapture(self.camera_id)
        else:
            self.cap = cv2.VideoCapture(self.camera_id)

        if not self.cap or not self.cap.isOpened():
            self._is_opened = False
            return False

        # Set requested resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.target_w)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.target_h)
        self.cap.set(cv2.CAP_PROP_FPS, self.target_fps)

        self.actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or self.target_w
        self.actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or self.target_h
        self._is_opened = True
        return True

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Reads a frame and returns (success, frame)."""
        if not self._is_opened or self.cap is None:
            return False, None

        ret, frame = self.cap.read()
        if not ret or frame is None:
            return False, None

        return True, frame

    def is_opened(self) -> bool:
        return self._is_opened and (self.cap is not None and self.cap.isOpened())

    def release(self) -> None:
        """Safely release webcam device."""
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        self._is_opened = False

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


class SyntheticCamera:
    """Generates procedural video frames for headless testing and benchmark verification."""

    def __init__(self, width: int = 640, height: int = 480, fps: int = 30):
        self.w = width
        self.h = height
        self.fps = fps
        self.start_time = time.perf_counter()
        self.frame_idx = 0

    def is_opened(self) -> bool:
        return True

    def read_frame(self) -> Tuple[bool, np.ndarray]:
        """Generates a dark sci-fi gradient background frame."""
        t = (self.frame_idx / float(self.fps))
        self.frame_idx += 1

        # Dark subtle vignette background
        frame = np.zeros((self.h, self.w, 3), dtype=np.uint8)

        # Subtle dark ambient grid
        grid_spacing = 40
        grid_color = (18, 22, 28)
        for x in range(0, self.w, grid_spacing):
            cv2.line(frame, (x, 0), (x, self.h), grid_color, 1)
        for y in range(0, self.h, grid_spacing):
            cv2.line(frame, (0, y), (self.w, y), grid_color, 1)

        # Subtle moving ambient particle
        ax = int((self.w * 0.5) + math.sin(t * 1.5) * 100)
        ay = int((self.h * 0.5) + math.cos(t * 1.2) * 60)
        cv2.circle(frame, (ax, ay), 3, (40, 50, 60), -1)

        return True, frame

    def release(self) -> None:
        pass
