"""Sci-Fi Holographic Heads-Up Display (HUD).

Renders real-time performance diagnostics (FPS, latency),
tracking state badges, camera selector badge, openness gauge bar,
and keyboard shortcuts with responsive, aspect-ratio-aware layout scaling.
"""

from typing import Dict, Optional, Tuple
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
        bracket_len = min(8, max(3, w // 8), max(3, h // 8))
        for (bx, by, dx, dy) in [
            (x, y, 1, 1),
            (x2 - 1, y, -1, 1),
            (x, y2 - 1, 1, -1),
            (x2 - 1, y2 - 1, -1, -1),
        ]:
            cv2.line(frame, (bx, by), (bx + dx * bracket_len, by), (255, 255, 255), 1, cv2.LINE_AA)
            cv2.line(frame, (bx, by), (bx, by + dy * bracket_len), (255, 255, 255), 1, cv2.LINE_AA)

    @staticmethod
    def get_layout_rects(
        w: int,
        h: int,
        interaction_mode: str = "SINGLE_HAND",
        has_notification: bool = True,
    ) -> Dict[str, Tuple[int, int, int, int]]:
        """Calculates bounding boxes (x1, y1, x2, y2) for HUD panels in (w, h)."""
        scale = max(0.85, min(1.5, min(w / 640.0, h / 480.0)))
        margin = int(14 * scale)
        panel_w = int(225 * scale)
        panel_h = int(96 * scale)

        tl_rect = (margin, margin, margin + panel_w, margin + panel_h)

        is_two_hand = interaction_mode in ("TWO_HANDS", "INDEPENDENT_DUAL_HAND")
        is_indep = (interaction_mode == "INDEPENDENT_DUAL_HAND")
        gauge_w = int(195 * scale) if is_two_hand else int(180 * scale)
        gauge_h = int(56 * scale) if is_indep else int(44 * scale)
        gx = w - gauge_w - margin
        gy = margin
        tr_rect = (gx, gy, gx + gauge_w, gy + gauge_h)

        notif_rect = (0, 0, 0, 0)
        if has_notification:
            avail_w = gx - (margin + panel_w) - int(20 * scale)
            notif_w = min(int(340 * scale), w - 2 * margin)
            notif_h = int(28 * scale)
            if avail_w >= int(260 * scale):
                nx = (w - notif_w) // 2
                ny = margin
            else:
                nx = (w - notif_w) // 2
                ny = margin + panel_h + int(8 * scale)
            notif_rect = (nx, ny, nx + notif_w, ny + notif_h)

        help_w = min(w - 2 * margin, int(600 * scale))
        help_h = int(26 * scale)
        hx = (w - help_w) // 2
        hy = h - help_h - margin
        bottom_rect = (hx, hy, hx + help_w, hy + help_h)

        return {
            "top_left": tl_rect,
            "top_right": tr_rect,
            "notification": notif_rect,
            "bottom_help": bottom_rect,
            "scale": scale,
        }

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
        selected_mode_name: str = "STANDARD 2-HAND",
    ) -> None:
        """Renders HUD overlay elements with responsive layout and aspect-ratio awareness."""
        h, w = frame.shape[:2]
        accent = theme.hud_accent

        active_notif = object_notification or camera_notification
        layout = self.get_layout_rects(
            w, h,
            interaction_mode=interaction_mode,
            has_notification=bool(active_notif),
        )
        scale = layout["scale"]
        margin = int(14 * scale)

        # ---------------------------------------------------------------------
        # 1. Top-Left: Performance Telemetry, Interaction Mode, Object & Camera
        # ---------------------------------------------------------------------
        tl_x1, tl_y1, tl_x2, tl_y2 = layout["top_left"]
        panel_w = tl_x2 - tl_x1
        panel_h = tl_y2 - tl_y1
        self.draw_glass_rect(frame, tl_x1, tl_y1, panel_w, panel_h, accent, bg_alpha=0.5)

        base_font_scale = 0.31 * scale
        line_step = int(14 * scale)
        tx = tl_x1 + int(10 * scale)
        ty = tl_y1 + int(15 * scale)

        fps_text = f"FPS: {fps:5.1f} ({frame_time_ms:4.1f}ms)"
        cv2.putText(
            frame, fps_text, (tx, ty),
            cv2.FONT_HERSHEY_SIMPLEX, base_font_scale * 1.08, (255, 255, 255), 1, cv2.LINE_AA,
        )

        mode_color = (120, 240, 255) if "INDEP" in selected_mode_name else (255, 220, 100)
        cv2.putText(
            frame, f"MODE: {selected_mode_name} [M]", (tx, ty + line_step),
            cv2.FONT_HERSHEY_SIMPLEX, base_font_scale * 1.02, mode_color, 1, cv2.LINE_AA,
        )

        if interaction_mode == "INDEPENDENT_DUAL_HAND":
            role_text = "ROLES: L=POS+ROT | R=SCL+CLR"
            role_color = (140, 255, 200)
        elif interaction_mode == "TWO_HANDS":
            role_text = "ROLES: 2-HAND SCALE+ROT"
            role_color = (120, 240, 255)
        elif hand_detected:
            role_text = "ROLES: 1-HAND (PRIMARY)"
            role_color = (200, 230, 255)
        else:
            role_text = "ROLES: SEARCHING HANDS"
            role_color = (130, 130, 130)

        cv2.putText(
            frame, role_text, (tx, ty + line_step * 2),
            cv2.FONT_HERSHEY_SIMPLEX, base_font_scale * 0.95, role_color, 1, cv2.LINE_AA,
        )

        status_color = (0, 255, 120) if is_grabbed else (accent if hand_detected else (100, 100, 100))
        cv2.putText(
            frame, f"STATE: {state_label}", (tx, ty + line_step * 3),
            cv2.FONT_HERSHEY_SIMPLEX, base_font_scale * 0.98, status_color, 1, cv2.LINE_AA,
        )

        obj_display = (object_name or "Orb").upper()
        cam_display = camera_name or "Camera 0"
        cv2.putText(
            frame, f"OBJ: {obj_display} [1-6] | CAM: {cam_display} [V]", (tx, ty + line_step * 4),
            cv2.FONT_HERSHEY_SIMPLEX, base_font_scale * 0.96, (220, 230, 255), 1, cv2.LINE_AA,
        )

        # ---------------------------------------------------------------------
        # 2. Top-Center: Transient Notification (Collision-Free Positioning)
        # ---------------------------------------------------------------------
        if active_notif:
            nx1, ny1, nx2, ny2 = layout["notification"]
            notif_w = nx2 - nx1
            notif_h = ny2 - ny1
            self.draw_glass_rect(frame, nx1, ny1, notif_w, notif_h, accent, bg_alpha=0.7)
            cv2.putText(
                frame, active_notif, (nx1 + int(10 * scale), ny1 + int(18 * scale)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35 * scale, (255, 255, 255), 1, cv2.LINE_AA,
            )

        # ---------------------------------------------------------------------
        # 3. Top-Right: Two-Hand Metrics or Single-Hand Openness Gauge Bar
        # ---------------------------------------------------------------------
        tr_x1, tr_y1, tr_x2, tr_y2 = layout["top_right"]
        gauge_w = tr_x2 - tr_x1
        gauge_h = tr_y2 - tr_y1
        gx = tr_x1
        gy = tr_y1

        if interaction_mode in ("TWO_HANDS", "INDEPENDENT_DUAL_HAND") and two_hand_scale is not None and rotation_deg is not None:
            is_indep = (interaction_mode == "INDEPENDENT_DUAL_HAND")
            self.draw_glass_rect(frame, gx, gy, gauge_w, gauge_h, accent, bg_alpha=0.5)

            cv2.putText(
                frame, f"SCALE: {two_hand_scale:.2f}x", (gx + int(10 * scale), gy + int(17 * scale)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35 * scale, (255, 255, 255), 1, cv2.LINE_AA,
            )
            cv2.putText(
                frame, f"ROTATION: {int(rotation_deg):+d} deg", (gx + int(10 * scale), gy + int(33 * scale)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35 * scale, (120, 240, 255), 1, cv2.LINE_AA,
            )
            if is_indep:
                cv2.putText(
                    frame, f"THEME: {theme.name.upper()}", (gx + int(10 * scale), gy + int(49 * scale)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.32 * scale, theme.inner_glow, 1, cv2.LINE_AA,
                )
        elif hand_detected and openness is not None:
            self.draw_glass_rect(frame, gx, gy, gauge_w, gauge_h, accent, bg_alpha=0.5)

            cv2.putText(
                frame, f"HAND OPEN: {int(openness * 100)}%", (gx + int(10 * scale), gy + int(17 * scale)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.36 * scale, (255, 255, 255), 1, cv2.LINE_AA,
            )

            # Bar track
            bar_x = gx + int(10 * scale)
            bar_y = gy + int(24 * scale)
            bar_total_w = gauge_w - int(20 * scale)
            bar_h = int(8 * scale)
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_total_w, bar_y + bar_h), (50, 50, 50), -1)

            # Filled bar
            filled_w = int(bar_total_w * max(0.0, min(1.0, openness)))
            if filled_w > 0:
                cv2.rectangle(
                    frame, (bar_x, bar_y), (bar_x + filled_w, bar_y + bar_h),
                    theme.inner_glow, -1,
                )
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_total_w, bar_y + bar_h), accent, 1)

        # ---------------------------------------------------------------------
        # 4. Bottom Bar: Controls Legend
        # ---------------------------------------------------------------------
        if self.show_help:
            bx1, by1, bx2, by2 = layout["bottom_help"]
            help_w = bx2 - bx1
            help_h = by2 - by1
            hx = bx1
            hy = by1
            self.draw_glass_rect(frame, hx, hy, help_w, help_h, accent, bg_alpha=0.6)

            if w < 560:
                controls_str = "[M] MENU | 1-6 OBJ | [C] THEME | [V] CAM"
            else:
                controls_str = "[M] MENU | 1-6 OBJ | 1-HAND: GRAB | 2-HAND: CTRL | [C] THEME | [V] CAM"

            cv2.putText(
                frame, controls_str, (hx + int(10 * scale), hy + int(17 * scale)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.31 * scale, (220, 240, 255), 1, cv2.LINE_AA,
            )
