"""Holographic Menu Trigger Zone Component.

Provides a persistent, aspect-ratio-aware corner trigger zone for entering and
exiting the Holographic Menu via deliberate open-palm dwell. Replaces global
open-palm activation with explicit spatial hit-testing and visual state feedback.
"""

import math
import time
from typing import List, Optional, Tuple
import cv2
import numpy as np

from src.hand_tracker import HandData
from src.vfx.color_themes import ColorTheme


class MenuTriggerZone:
    """Fixed-corner holographic button requiring open palm + dwell to toggle menu."""

    def __init__(
        self,
        dwell_time: float = 0.50,
        openness_thresh: float = 0.70,
        cooldown: float = 0.50,
    ):
        self.dwell_time = dwell_time
        self.openness_thresh = openness_thresh
        self.cooldown = cooldown

        # State tracking
        self.dwell_progress: float = 0.0  # 0.0 to 1.0
        self.state: str = "IDLE"          # "IDLE", "HOVERING", "CHARGING", "TRIGGERED"
        self.is_hovered: bool = False
        self.last_trigger_time: float = 0.0
        self.triggered_flash_time: float = 0.0

        # Geometry cache
        self.pixel_rect: Tuple[int, int, int, int] = (0, 0, 0, 0)      # (x1, y1, x2, y2)
        self.hit_rect: Tuple[int, int, int, int] = (0, 0, 0, 0)        # (hx1, hy1, hx2, hy2)
        self.norm_rect: Tuple[float, float, float, float] = (0, 0, 0, 0)  # (nx1, ny1, nx2, ny2)

    def update_geometry(self, frame_width: int, frame_height: int) -> None:
        """Calculates normalized and pixel bounds anchored to the top-right viewport corner."""
        scale = max(0.85, min(1.5, min(frame_width / 640.0, frame_height / 480.0)))
        margin = int(14 * scale)
        btn_w = int(105 * scale)
        btn_h = int(34 * scale)

        x1 = frame_width - btn_w - margin
        y1 = margin
        x2 = x1 + btn_w
        y2 = y1 + btn_h
        self.pixel_rect = (x1, y1, x2, y2)

        # Generous hit target padding for seamless touchless targeting
        hit_pad_x = int(16 * scale)
        hit_pad_y = int(10 * scale)
        hx1 = max(0, x1 - hit_pad_x)
        hy1 = max(0, y1 - hit_pad_y)
        hx2 = min(frame_width, x2 + hit_pad_x)
        hy2 = min(frame_height, y2 + hit_pad_y)
        self.hit_rect = (hx1, hy1, hx2, hy2)

        self.norm_rect = (
            hx1 / float(max(1, frame_width)),
            hy1 / float(max(1, frame_height)),
            hx2 / float(max(1, frame_width)),
            hy2 / float(max(1, frame_height)),
        )

    def is_point_inside(self, px: float, py: float) -> bool:
        """Checks if a point in pixel coordinates is within the trigger hit zone."""
        hx1, hy1, hx2, hy2 = self.hit_rect
        return hx1 <= px <= hx2 and hy1 <= py <= hy2

    def is_norm_point_inside(self, norm_x: float, norm_y: float) -> bool:
        """Checks if a point in normalized coordinates is within the trigger hit zone."""
        nx1, ny1, nx2, ny2 = self.norm_rect
        return nx1 <= norm_x <= nx2 and ny1 <= norm_y <= ny2

    def update(
        self,
        hands: List[HandData],
        frame_width: int,
        frame_height: int,
        dt: float = 0.033,
        now: Optional[float] = None,
    ) -> bool:
        """Evaluates hand positions against trigger zone. Returns True if dwell triggered."""
        current_time = time.perf_counter() if now is None else now
        self.update_geometry(frame_width, frame_height)

        # Check cooldown
        if (current_time - self.last_trigger_time) < self.cooldown:
            self.dwell_progress = 0.0
            self.state = "IDLE"
            self.is_hovered = False
            return False

        # Find any hand that overlaps the trigger zone
        matching_hand: Optional[HandData] = None
        hand_in_zone = False

        for hand in hands:
            if hand is None or not hand.landmarks_px:
                continue

            px, py = hand.palm_center_px
            pinch_x, pinch_y = hand.pinch_point_px

            if self.is_point_inside(px, py) or self.is_point_inside(pinch_x, pinch_y):
                hand_in_zone = True
                # Require open palm pose (no pinch, openness above threshold)
                if hand.openness >= self.openness_thresh and not hand.is_pinching:
                    matching_hand = hand
                    break

        if matching_hand is not None:
            self.is_hovered = True
            # Advance dwell charging
            self.dwell_progress += dt / max(0.01, self.dwell_time)
            self.dwell_progress = min(1.0, self.dwell_progress)

            if self.dwell_progress >= 1.0:
                self.dwell_progress = 0.0
                self.state = "TRIGGERED"
                self.last_trigger_time = current_time
                self.triggered_flash_time = current_time
                return True
            else:
                self.state = "CHARGING"
        elif hand_in_zone:
            # Hand inside zone but closed/pinching -> hovering without charging
            self.is_hovered = True
            self.state = "HOVERING"
            self.dwell_progress = max(0.0, self.dwell_progress - dt * 2.5)
        else:
            # Hand outside zone -> reset
            self.is_hovered = False
            self.state = "IDLE"
            self.dwell_progress = max(0.0, self.dwell_progress - dt * 4.0)

        return False

    def render(self, frame: np.ndarray, theme: ColorTheme, is_menu_open: bool = False) -> None:
        """Renders the persistent holographic trigger button with dynamic visual feedback."""
        x1, y1, x2, y2 = self.pixel_rect
        if x2 <= x1 or y2 <= y1:
            return

        h, w = frame.shape[:2]
        scale = max(0.85, min(1.5, min(w / 640.0, h / 480.0)))
        accent = theme.hud_accent
        label = "CLOSE" if is_menu_open else "MENU"

        # Determine visual style based on activation state
        now = time.perf_counter()
        is_flashing = (now - self.triggered_flash_time) < 0.25

        if is_flashing:
            border_color = (0, 255, 180)  # Bright emerald flash
            bg_alpha = 0.65
            icon_text = "OK"
        elif self.state == "CHARGING":
            border_color = (120, 245, 255)  # Glowing charging cyan
            bg_alpha = 0.50
            icon_text = f"{int(self.dwell_progress * 100)}%"
        elif self.state == "HOVERING":
            border_color = (255, 220, 100)  # Amber hover highlight
            bg_alpha = 0.40
            icon_text = "..."
        else:
            border_color = accent
            bg_alpha = 0.28
            icon_text = ">"

        # 1. Semi-transparent glass background
        sub_roi = frame[y1:y2, x1:x2]
        if sub_roi.size > 0:
            cv2.convertScaleAbs(sub_roi, alpha=(1.0 - bg_alpha), dst=sub_roi)

        # 2. Outer border and sci-fi brackets
        cv2.rectangle(frame, (x1, y1), (x2, y2), border_color, 1, cv2.LINE_AA)
        bracket_len = int(8 * scale)
        for (bx, by, dx, dy) in [
            (x1, y1, 1, 1),
            (x2 - 1, y1, -1, 1),
            (x1, y2 - 1, 1, -1),
            (x2 - 1, y2 - 1, -1, -1),
        ]:
            cv2.line(frame, (bx, by), (bx + dx * bracket_len, by), (255, 255, 255), 1, cv2.LINE_AA)
            cv2.line(frame, (bx, by), (bx, by + dy * bracket_len), (255, 255, 255), 1, cv2.LINE_AA)

        # 3. Label text
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.34 * scale
        text_str = f"[ {label} ]"
        text_y = y1 + int(21 * scale)
        cv2.putText(
            frame, text_str, (x1 + int(10 * scale), text_y),
            font, font_scale, (255, 255, 255), 1, cv2.LINE_AA
        )

        # 4. Circular Dwell Charging Ring / Indicator Icon
        cx = x2 - int(18 * scale)
        cy = y1 + (y2 - y1) // 2
        r_ring = int(7 * scale)

        if self.state == "CHARGING" and self.dwell_progress > 0.0:
            # Background dim circle
            cv2.circle(frame, (cx, cy), r_ring, (60, 80, 100), 1, cv2.LINE_AA)
            # Progress arc
            sweep = int(self.dwell_progress * 360)
            cv2.ellipse(
                frame, (cx, cy), (r_ring, r_ring),
                -90, 0, sweep, (0, 255, 220), 2, cv2.LINE_AA
            )
        elif is_flashing:
            cv2.circle(frame, (cx, cy), r_ring, (0, 255, 180), -1, cv2.LINE_AA)
        else:
            # Idle / Hover dot
            dot_color = (255, 220, 100) if self.state == "HOVERING" else (140, 170, 190)
            cv2.circle(frame, (cx, cy), max(2, int(3 * scale)), dot_color, -1, cv2.LINE_AA)
