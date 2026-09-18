"""Holographic Hand Cursor for Touchless UI Interaction.

Provides a smooth, normalized-coordinate holographic reticle that tracks the user's
hand, provides hover highlights, detects pinch-to-click, and supports dwell selection.
"""

import math
import time
from typing import Optional, Tuple
import cv2
import numpy as np

from src.filters import PointFilter
from src.hand_tracker import HandData
from src.vfx.color_themes import ColorTheme


class HandCursor:
    """Holographic reticle cursor driven by hand tracking."""

    def __init__(
        self,
        dwell_time_thresh: float = 0.75,
        dwell_motion_thresh_px: float = 14.0,
    ):
        self.x_px: float = 0.0
        self.y_px: float = 0.0
        self.norm_x: float = 0.5
        self.norm_y: float = 0.5
        self.is_active: bool = False
        self.is_pinching: bool = False
        self.is_hovered: bool = False

        # Smoothing filter
        self._filter = PointFilter(mincutoff=1.8, beta=0.04)

        # Dwell selection tracking
        self.dwell_time_thresh = dwell_time_thresh
        self.dwell_motion_thresh = dwell_motion_thresh_px
        self.dwell_start_time: float = 0.0
        self.dwell_anchor_px: Tuple[float, float] = (0.0, 0.0)
        self.dwell_progress: float = 0.0  # 0.0 to 1.0
        self.dwell_triggered: bool = False

        # Click event state (single-fire rising edge)
        self._prev_pinching: bool = False
        self.click_event: bool = False

    def update(
        self,
        hand: Optional[HandData],
        frame_width: int,
        frame_height: int,
        dt: float = 0.033,
        timestamp: Optional[float] = None,
    ) -> None:
        """Updates cursor position, smoothing, pinch click events, and dwell progress."""
        now = time.perf_counter() if timestamp is None else timestamp

        if hand is None or not hand.landmarks_px:
            self.is_active = False
            self.is_pinching = False
            self.click_event = False
            self.dwell_progress = 0.0
            self.dwell_triggered = False
            return

        self.is_active = True
        raw_x, raw_y = hand.pinch_point_px
        filtered_pt = self._filter.filter_pt((raw_x, raw_y), timestamp=now)

        self.x_px = float(filtered_pt[0])
        self.y_px = float(filtered_pt[1])

        # Clamped normalized coordinates for aspect-ratio-independent hit testing
        self.norm_x = max(0.0, min(1.0, self.x_px / float(max(1, frame_width))))
        self.norm_y = max(0.0, min(1.0, self.y_px / float(max(1, frame_height))))

        # Detect single-fire click event on pinch transition (False -> True)
        curr_pinch = bool(hand.is_pinching)
        if curr_pinch and not self._prev_pinching:
            self.click_event = True
        else:
            self.click_event = False
        self._prev_pinching = curr_pinch
        self.is_pinching = curr_pinch

        # Dwell progress calculation
        dist_from_anchor = math.hypot(self.x_px - self.dwell_anchor_px[0], self.y_px - self.dwell_anchor_px[1])
        if dist_from_anchor > self.dwell_motion_thresh or self.is_pinching:
            # Hand moved significantly or is pinching: re-anchor dwell
            self.dwell_anchor_px = (self.x_px, self.y_px)
            self.dwell_start_time = now
            self.dwell_progress = 0.0
            self.dwell_triggered = False
        else:
            elapsed = now - self.dwell_start_time
            self.dwell_progress = max(0.0, min(1.0, elapsed / max(0.01, self.dwell_time_thresh)))
            if self.dwell_progress >= 1.0 and not self.dwell_triggered:
                self.dwell_triggered = True
                self.click_event = True  # Dwell triggers selection

    def reset(self) -> None:
        """Resets cursor tracking and dwell states."""
        self.is_active = False
        self.is_pinching = False
        self.is_hovered = False
        self.click_event = False
        self.dwell_progress = 0.0
        self.dwell_triggered = False
        self._prev_pinching = False
        self._filter.reset()

    def render(self, frame: np.ndarray, theme: ColorTheme) -> None:
        """Renders subtle, futuristic holographic reticle at cursor coordinates."""
        if not self.is_active:
            return

        cx, cy = int(round(self.x_px)), int(round(self.y_px))
        h_frame, w_frame = frame.shape[:2]

        if not (0 <= cx < w_frame and 0 <= cy < h_frame):
            return

        primary_color = theme.ring_primary
        accent_color = theme.hud_accent
        active_color = (120, 255, 200) if self.is_hovered else primary_color

        # Base radius: contracts on pinch, expands on hover
        if self.is_pinching:
            reticle_r = 5
            crosshair_len = 8
            core_r = 3
        elif self.is_hovered:
            reticle_r = 13
            crosshair_len = 18
            core_r = 4
        else:
            reticle_r = 9
            crosshair_len = 14
            core_r = 2

        # 1. Inner glowing core dot
        cv2.circle(frame, (cx, cy), core_r, (255, 255, 255), -1, cv2.LINE_AA)

        # 2. Concentric targeting ring
        cv2.circle(frame, (cx, cy), reticle_r, active_color, 1, cv2.LINE_AA)

        # 3. Four crosshair ticks
        for (dx, dy) in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            x1 = cx + dx * (reticle_r + 2)
            y1 = cy + dy * (reticle_r + 2)
            x2 = cx + dx * (reticle_r + crosshair_len)
            y2 = cy + dy * (reticle_r + crosshair_len)
            cv2.line(frame, (x1, y1), (x2, y2), active_color, 1, cv2.LINE_AA)

        # 4. Dwell progress arc (if dwelling without pinch)
        if not self.is_pinching and 0.05 < self.dwell_progress < 1.0:
            dwell_r = reticle_r + 5
            arc_end_angle = int(self.dwell_progress * 360)
            cv2.ellipse(
                frame, (cx, cy), (dwell_r, dwell_r),
                -90, 0, arc_end_angle, (100, 255, 255), 2, cv2.LINE_AA
            )

        # 5. Energy flare on pinch click
        if self.is_pinching:
            cv2.circle(frame, (cx, cy), reticle_r + 6, (255, 255, 255), 1, cv2.LINE_AA)
