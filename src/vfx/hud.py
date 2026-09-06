"""Sci-Fi Holographic Heads-Up Display (HUD).

Renders real-time performance diagnostics (FPS, latency),
tracking state badges, openness gauge bar, and keyboard shortcuts.
"""

from typing import Optional, Tuple
import cv2
import numpy as np

from src.vfx.color_themes import ColorTheme


class HUD:
    """Renders sci-fi HUD telemetry and interaction gauges onto the frame."""

    def __init__(self):
        self.show_help: bool = True
        self.show_landmarks: bool = False

    def toggle_help(self) -> None:
        self.show_help = not self.show_help

    def toggle_landmarks(self) -> None:
        self.show_landmarks = not self.show_landmarks

    @staticmethod
    def draw_glass_rect(
        frame: np.ndarray,
        x: int,
        y: int,
        w: int,
        h: int,
        border_color: Tuple[int, int, int],
        bg_alpha: float = 0.45,
    ) -> None:
        """Draws a semi-transparent glass panel with sci-fi angled corners."""
        h_frame, w_frame = frame.shape[:2]
        x2 = min(w_frame, x + w)
        y2 = min(h_frame, y + h)
        x = max(0, x)
        y = max(0, y)

        if x2 <= x or y2 <= y:
            return

        sub_roi = frame[y:y2, x:x2]
        dark_patch = (sub_roi * (1.0 - bg_alpha)).astype(np.uint8)
        frame[y:y2, x:x2] = dark_patch

        # Outer border
        cv2.rectangle(frame, (x, y), (x2, y2), border_color, 1, cv2.LINE_AA)

        # Sci-fi corner brackets
        bracket_len = min(8, w // 4, h // 4)
        for (bx, by, dx, dy) in [
            (x, y, 1, 1),
            (x2 - 1, y, -1, 1),
            (x, y2 - 1, 1, -1),
            (x2 - 1, y2 - 1, -1, -1),
        ]:
            cv2.line(frame, (bx, by), (bx + dx * bracket_len, by), (255, 255, 255), 1, cv2.LINE_AA)
            cv2.line(frame, (bx, by), (bx, by + dy * bracket_len), (255, 255, 255), 1, cv2.LINE_AA)

    def render(
        self,
        frame: np.ndarray,
        fps: float,
        frame_time_ms: float,
        theme: ColorTheme,
        state_label: str,
        openness: Optional[float] = None,
        is_pinching: bool = False,
        is_grabbed: bool = False,
        hand_detected: bool = False,
    ) -> None:
        """Renders HUD overlay elements."""
        h, w = frame.shape[:2]
        accent = theme.hud_accent

        # Top-Left: Performance Telemetry
        panel_w = 175
        panel_h = 44
        self.draw_glass_rect(frame, 14, 14, panel_w, panel_h, accent, bg_alpha=0.5)

        fps_text = f"FPS: {fps:5.1f} ({frame_time_ms:4.1f}ms)"
        cv2.putText(
            frame, fps_text, (24, 34),
            cv2.FONT_HERSHEY_SIMPLEX, 0.44, (255, 255, 255), 1, cv2.LINE_AA
        )

        # Status badge
        status_color = (0, 255, 120) if is_grabbed else (accent if hand_detected else (100, 100, 100))
        cv2.putText(
            frame, f"STATUS: {state_label}", (24, 50),
            cv2.FONT_HERSHEY_SIMPLEX, 0.40, status_color, 1, cv2.LINE_AA
        )

        # Top-Right: Openness Gauge Bar (if hand is detected)
        if hand_detected and openness is not None:
            gauge_w = 180
            gauge_h = 44
            gx = w - gauge_w - 14
            gy = 14
            self.draw_glass_rect(frame, gx, gy, gauge_w, gauge_h, accent, bg_alpha=0.5)

            # Openness label
            cv2.putText(
                frame, f"HAND OPEN: {int(openness * 100)}%", (gx + 10, gy + 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1, cv2.LINE_AA
            )

            # Bar track
            bar_x = gx + 10
            bar_y = gy + 26
            bar_total_w = gauge_w - 20
            bar_h = 8
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_total_w, bar_y + bar_h), (50, 50, 50), -1)

            # Filled bar
            filled_w = int(bar_total_w * max(0.0, min(1.0, openness)))
            if filled_w > 0:
                cv2.rectangle(
                    frame, (bar_x, bar_y), (bar_x + filled_w, bar_y + bar_h),
                    theme.inner_glow, -1
                )
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_total_w, bar_y + bar_h), accent, 1)

        # Bottom Bar: Controls Legend
        if self.show_help:
            help_w = min(w - 28, 540)
            help_h = 26
            hx = (w - help_w) // 2
            hy = h - help_h - 10
            self.draw_glass_rect(frame, hx, hy, help_w, help_h, accent, bg_alpha=0.6)

            controls_str = f"THEME: {theme.name} [C]  |  RESET [R]  |  SKELETON [H]  |  EXIT [Q/ESC]"
            cv2.putText(
                frame, controls_str, (hx + 14, hy + 17),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, (220, 240, 255), 1, cv2.LINE_AA
            )
