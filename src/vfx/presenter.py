"""Aspect-Ratio-Preserving Window Presenter.

Provides zero-allocation letterbox and pillarbox presentation for OpenCV windows,
preventing non-uniform scaling or stretching when window client dimensions differ
from native camera frame aspect ratios.
"""

from typing import Optional, Tuple
import cv2
import numpy as np


class AspectPreservingPresenter:
    """Presents video frames into OpenCV windows while strictly preserving aspect ratio."""

    def __init__(self, bg_color: Tuple[int, int, int] = (14, 16, 20)):
        self.bg_color = bg_color
        self._canvas: Optional[np.ndarray] = None
        self._cached_win_size: Tuple[int, int] = (0, 0)
        self._cached_frame_size: Tuple[int, int] = (0, 0)
        self._cached_roi_slice: Optional[np.ndarray] = None
        self._cached_target_size: Optional[Tuple[int, int]] = None
        self._needs_letterbox: bool = False

        # Public geometry properties for inspection and testing
        self.x_offset: int = 0
        self.y_offset: int = 0
        self.target_w: int = 0
        self.target_h: int = 0

    @property
    def is_letterboxed(self) -> bool:
        """True if the active presentation requires letterbox or pillarbox bars."""
        return self._needs_letterbox

    def prepare_presentation(
        self,
        frame: np.ndarray,
        win_w: int,
        win_h: int,
    ) -> np.ndarray:
        """Adapts frame to window client dimensions without aspect-ratio distortion.

        If window dimensions match frame dimensions or frame aspect ratio exactly,
        returns frame directly with zero copy.
        If window dimensions require letterbox/pillarbox, blits resized frame
        into a cached presentation canvas without per-frame memory allocations.

        Parameters
        ----------
        frame : Native rendered video frame.
        win_w : Window client area width in pixels.
        win_h : Window client area height in pixels.

        Returns
        -------
        Display-ready image matrix of shape (win_h, win_w, 3) or (frame_h, frame_w, 3).
        """
        if win_w <= 0 or win_h <= 0 or frame is None:
            return frame

        fh, fw = frame.shape[:2]

        # 1. Exact 1:1 dimension match: direct display with zero overhead
        if win_w == fw and win_h == fh:
            self._needs_letterbox = False
            self.x_offset = 0
            self.y_offset = 0
            self.target_w = fw
            self.target_h = fh
            return frame

        # 2. Exact aspect ratio match: OpenCV will scale isotropically with zero overhead
        if win_w * fh == win_h * fw:
            self._needs_letterbox = False
            self.x_offset = 0
            self.y_offset = 0
            self.target_w = win_w
            self.target_h = win_h
            return frame

        # 3. Mismatched aspect ratio: maintain geometry using cached letterbox/pillarbox canvas
        if (win_w, win_h) != self._cached_win_size or (fw, fh) != self._cached_frame_size:
            scale = min(win_w / float(fw), win_h / float(fh))
            target_w = max(1, int(round(fw * scale)))
            target_h = max(1, int(round(fh * scale)))
            x_offset = max(0, (win_w - target_w) // 2)
            y_offset = max(0, (win_h - target_h) // 2)

            # Reallocate or reuse canvas buffer
            if self._canvas is None or self._canvas.shape[:2] != (win_h, win_w):
                self._canvas = np.empty((win_h, win_w, 3), dtype=np.uint8)

            # Fill matte background
            self._canvas[:] = self.bg_color

            # Subtle frame border boundary line
            if x_offset > 0 or y_offset > 0:
                bx1 = max(0, x_offset - 1)
                by1 = max(0, y_offset - 1)
                bx2 = min(win_w - 1, x_offset + target_w)
                by2 = min(win_h - 1, y_offset + target_h)
                cv2.rectangle(self._canvas, (bx1, by1), (bx2, by2), (32, 38, 46), 1)

            self._cached_roi_slice = self._canvas[
                y_offset : y_offset + target_h,
                x_offset : x_offset + target_w,
            ]
            self._cached_target_size = (target_w, target_h)
            self._cached_win_size = (win_w, win_h)
            self._cached_frame_size = (fw, fh)
            self.x_offset = x_offset
            self.y_offset = y_offset
            self.target_w = target_w
            self.target_h = target_h
            self._needs_letterbox = True

        # In-place destination resize directly into canvas slice
        cv2.resize(
            frame,
            self._cached_target_size,
            dst=self._cached_roi_slice,
            interpolation=cv2.INTER_LINEAR,
        )
        return self._canvas
