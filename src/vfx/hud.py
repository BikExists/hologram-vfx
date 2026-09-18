"""Sci-Fi Holographic Heads-Up Display (HUD).

Renders real-time performance diagnostics (FPS, latency),
tracking state badges, camera selector badge, openness gauge bar,
and keyboard shortcuts.
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
        camera_name: Optional[str] = None,
        camera_notification: Optional[str] = None,
        object_name: str = "Orb",
        object_notification: Optional[str] = None,
        interaction_mode: str = "SINGLE_HAND",
        two_hand_scale: Optional[float] = None,
        rotation_deg: Optional[float] = None,
    ) -> None:
        """Renders HUD overlay elements with performance diagnostics and interaction telemetry."""
        h, w = frame.shape[:2]
        accent = theme.hud_accent

        # Top-Left: Performance Telemetry, Active Object & Camera
        panel_w = 215
        panel_h = 86
        self.draw_glass_rect(frame, 14, 14, panel_w, panel_h, accent, bg_alpha=0.5)

        fps_text = f"FPS: {fps:5.1f} ({frame_time_ms:4.1f}ms)"
        cv2.putText(
            frame, fps_text, (24, 28),
            cv2.FONT_HERSHEY_SIMPLEX, 0.36, (255, 255, 255), 1, cv2.LINE_AA
        )

        # Mode indicator
        mode_text = f"MODE: {interaction_mode.replace('_', ' ')}"
        mode_color = (120, 240, 255) if interaction_mode == "TWO_HANDS" else (accent if hand_detected else (140, 140, 140))
        cv2.putText(
            frame, mode_text, (24, 42),
            cv2.FONT_HERSHEY_SIMPLEX, 0.34, mode_color, 1, cv2.LINE_AA
        )

        # Status badge
        status_color = (0, 255, 120) if is_grabbed else (accent if hand_detected else (100, 100, 100))
        cv2.putText(
            frame, f"STATUS: {state_label}", (24, 56),
            cv2.FONT_HERSHEY_SIMPLEX, 0.32, status_color, 1, cv2.LINE_AA
        )

        # Object indicator
        obj_display = (object_name or "Orb").upper()
        cv2.putText(
            frame, f"OBJ: {obj_display} [1-3]", (24, 70),
            cv2.FONT_HERSHEY_SIMPLEX, 0.34, (255, 230, 140), 1, cv2.LINE_AA
        )

        # Camera source indicator
        cam_display = camera_name or "Camera 0"
        cv2.putText(
            frame, f"CAM: {cam_display} [V]", (24, 84),
            cv2.FONT_HERSHEY_SIMPLEX, 0.32, (200, 230, 255), 1, cv2.LINE_AA
        )

        # Top-Center: Transient Notification (Object switch or Camera switch)
        active_notif = object_notification or camera_notification
        if active_notif:
            notif_w = min(w - 28, 320)
            notif_h = 28
            nx = (w - notif_w) // 2
            ny = 14
            self.draw_glass_rect(frame, nx, ny, notif_w, notif_h, accent, bg_alpha=0.7)
            cv2.putText(
                frame, active_notif, (nx + 12, ny + 19),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1, cv2.LINE_AA
            )

        # Top-Right: Two-Hand Metrics or Single-Hand Openness Gauge Bar
        if interaction_mode == "TWO_HANDS" and two_hand_scale is not None and rotation_deg is not None:
            gauge_w = 180
            gauge_h = 44
            gx = w - gauge_w - 14
            gy = 14
            self.draw_glass_rect(frame, gx, gy, gauge_w, gauge_h, accent, bg_alpha=0.5)

            cv2.putText(
                frame, f"SCALE: {two_hand_scale:.2f}x", (gx + 12, gy + 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.36, (255, 255, 255), 1, cv2.LINE_AA
            )
            cv2.putText(
                frame, f"ROTATION: {int(rotation_deg):+d} deg", (gx + 12, gy + 34),
                cv2.FONT_HERSHEY_SIMPLEX, 0.36, (120, 240, 255), 1, cv2.LINE_AA
            )
        elif hand_detected and openness is not None:
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
            help_w = min(w - 20, 620)
            help_h = 26
            hx = (w - help_w) // 2
            hy = h - help_h - 10
            self.draw_glass_rect(frame, hx, hy, help_w, help_h, accent, bg_alpha=0.6)

            controls_str = "OBJ: 1=ORB 2=CUBE 3=PLANET | 1-HAND: GRAB | 2-HAND: SCALE+ROT | THEME [C] | CAM [V]"
            cv2.putText(
                frame, controls_str, (hx + 10, hy + 17),
                cv2.FONT_HERSHEY_SIMPLEX, 0.33, (220, 240, 255), 1, cv2.LINE_AA
            )

