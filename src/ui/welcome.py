"""Holographic Welcome Screen Overlay.

Displays a futuristic, lightweight welcome panel when the application starts,
visually guiding the user to show their hand and pinch to begin. Non-blocking
and aspect-ratio aware.
"""

import math
import time
from typing import Optional
import cv2
import numpy as np

from src.hand_tracker import HandData
from src.vfx.color_themes import ColorTheme


class WelcomeScreen:
    """Renders the introductory holographic welcome overlay."""

    def __init__(self):
        self.time_start = time.perf_counter()
        self.pulse_timer: float = 0.0

    def update(self, dt: float) -> None:
        """Updates animation timers."""
        self.pulse_timer += dt

    def should_dismiss(self, hand: Optional[HandData]) -> bool:
        """Checks if user performed hand gesture to enter the experience."""
        if hand is not None and hand.landmarks_px:
            # Dismiss if user pinches, or holds hand open in view for a moment
            if hand.is_pinching or hand.openness > 0.65:
                return True
        return False

    def render(self, frame: np.ndarray, theme: ColorTheme) -> None:
        """Renders the sleek holographic welcome overlay onto the camera frame."""
        h, w = frame.shape[:2]
        scale = max(0.85, min(1.5, min(w / 640.0, h / 480.0)))
        accent = theme.hud_accent
        primary = theme.ring_primary

        panel_w = int(min(w - 30, 480 * scale))
        panel_h = int(min(h - 40, 220 * scale))
        x = (w - panel_w) // 2
        y = (h - panel_h) // 2

        # 1. Dark frosted glass background patch
        sub_roi = frame[y : y + panel_h, x : x + panel_w]
        if sub_roi.size > 0:
            dark_patch = (sub_roi * 0.35).astype(np.uint8)
            frame[y : y + panel_h, x : x + panel_w] = dark_patch

        # 2. Outer border and sci-fi brackets
        cv2.rectangle(frame, (x, y), (x + panel_w, y + panel_h), accent, 1, cv2.LINE_AA)
        bracket_len = int(14 * scale)
        for (bx, by, dx, dy) in [
            (x, y, 1, 1),
            (x + panel_w - 1, y, -1, 1),
            (x, y + panel_h - 1, 1, -1),
            (x + panel_w - 1, y + panel_h - 1, -1, -1),
        ]:
            cv2.line(frame, (bx, by), (bx + dx * bracket_len, by), (255, 255, 255), 2, cv2.LINE_AA)
            cv2.line(frame, (bx, by), (bx, by + dy * bracket_len), (255, 255, 255), 2, cv2.LINE_AA)

        # 3. Holographic Header Text
        title_text = "HOLOGRAPHIC VFX"
        font = cv2.FONT_HERSHEY_SIMPLEX
        title_scale = 0.65 * scale
        (tw, th), _ = cv2.getTextSize(title_text, font, title_scale, 2)
        tx = x + (panel_w - tw) // 2
        ty = y + int(48 * scale)
        # Glow shadow
        cv2.putText(frame, title_text, (tx, ty), font, title_scale, primary, 3, cv2.LINE_AA)
        cv2.putText(frame, title_text, (tx, ty), font, title_scale, (255, 255, 255), 1, cv2.LINE_AA)

        # 4. Subtitle
        sub_text = "TOUCHLESS HOLOGRAPHIC INTERFACE"
        sub_scale = 0.36 * scale
        (sw, sh), _ = cv2.getTextSize(sub_text, font, sub_scale, 1)
        sx = x + (panel_w - sw) // 2
        sy = ty + int(24 * scale)
        cv2.putText(frame, sub_text, (sx, sy), font, sub_scale, (200, 235, 255), 1, cv2.LINE_AA)

        # Decorative divider line
        div_y = sy + int(16 * scale)
        div_pad = int(40 * scale)
        cv2.line(frame, (x + div_pad, div_y), (x + panel_w - div_pad, div_y), accent, 1, cv2.LINE_AA)
        cv2.circle(frame, (w // 2, div_y), int(3 * scale), (255, 255, 255), -1, cv2.LINE_AA)

        # 5. Pulsating Prompt
        pulse = 0.5 + 0.5 * math.sin(self.pulse_timer * 3.5)
        pulse_color = (
            int(100 + 155 * pulse),
            int(220 + 35 * pulse),
            int(120 + 135 * pulse),
        )

        prompt_text = "[ SHOW HAND & PINCH TO START ]"
        prompt_scale = 0.42 * scale
        (pw, ph), _ = cv2.getTextSize(prompt_text, font, prompt_scale, 1)
        px = x + (panel_w - pw) // 2
        py = div_y + int(36 * scale)
        cv2.putText(frame, prompt_text, (px, py), font, prompt_scale, pulse_color, 1, cv2.LINE_AA)

        # 6. Secondary instruction
        info_text = "or press SPACE / any key to skip"
        info_scale = 0.30 * scale
        (iw, ih), _ = cv2.getTextSize(info_text, font, info_scale, 1)
        ix = x + (panel_w - iw) // 2
        iy = py + int(26 * scale)
        cv2.putText(frame, info_text, (ix, iy), font, info_scale, (140, 150, 165), 1, cv2.LINE_AA)
