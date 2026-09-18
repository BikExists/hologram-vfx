"""Holographic Menu System with Dual-Hand Control and Smooth Scrolling.

Provides an interactive sci-fi control panel allowing touchless hand-cursor
selection of holographic objects (1-6), interaction modes, color themes,
dynamic camera sources, and smooth secondary-hand scrolling.
"""

from dataclasses import dataclass
import math
from typing import Any, Callable, Dict, List, Optional, Tuple
import cv2
import numpy as np

from src.camera import CameraDeviceInfo
from src.vfx.color_themes import ColorTheme


@dataclass
class MenuItem:
    """An interactive button inside the holographic menu."""

    id: str
    label: str
    action_type: str  # 'OBJECT', 'MODE', 'THEME', 'CAMERA', 'CLOSE'
    action_value: Any
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0
    is_active: bool = False
    is_hovered: bool = False


class HolographicMenu:
    """Touchless holographic menu panel with dual-hand interaction."""

    def __init__(self):
        self.scroll_y: float = 0.0
        self.target_scroll_y: float = 0.0
        self.max_scroll: float = 120.0
        self.prev_secondary_y: Optional[float] = None
        self.scroll_deadband: float = 4.0

        # Cached menu items
        self.items: List[MenuItem] = []
        self.hovered_item: Optional[MenuItem] = None

        # Visual layout geometry cache
        self.panel_x: int = 0
        self.panel_y: int = 0
        self.panel_w: int = 0
        self.panel_h: int = 0

    def handle_secondary_hand_scroll(self, secondary_hand_y_px: Optional[float], dt: float = 0.033) -> None:
        """Applies smooth scrolling based on relative secondary-hand vertical movement."""
        if secondary_hand_y_px is None:
            self.prev_secondary_y = None
            return

        if self.prev_secondary_y is not None:
            dy = secondary_hand_y_px - self.prev_secondary_y
            if abs(dy) > self.scroll_deadband:
                # Upward hand movement (dy < 0) scrolls down, downward (dy > 0) scrolls up
                self.target_scroll_y -= dy * 1.3
                self.target_scroll_y = max(0.0, min(self.max_scroll, self.target_scroll_y))

        self.prev_secondary_y = secondary_hand_y_px

    def update(
        self,
        cursor_pos_px: Optional[Tuple[float, float]],
        is_pinching: bool,
        click_event: bool,
        secondary_hand_y: Optional[float],
        active_object_id: int,
        active_mode_name: str,
        active_theme_name: str,
        active_camera_name: str,
        available_cameras: List[CameraDeviceInfo],
        frame_width: int,
        frame_height: int,
        dt: float = 0.033,
        pending_object_id: Optional[int] = None,
        pending_mode_name: Optional[str] = None,
        pending_theme_name: Optional[str] = None,
        pending_camera_idx: Optional[int] = None,
        pending_camera_name: Optional[str] = None,
    ) -> Optional[Tuple[str, Any]]:
        """Updates menu layout, hit tests cursor, applies scroll, and handles button selection."""
        # Determine effective selection for visual feedback (prefer staged pending changes)
        display_obj_id = pending_object_id if pending_object_id is not None else active_object_id
        display_mode = pending_mode_name if pending_mode_name is not None else active_mode_name
        display_theme = pending_theme_name if pending_theme_name is not None else active_theme_name
        display_cam_name = pending_camera_name if pending_camera_name is not None else active_camera_name

        # 1. Update smooth scroll with exponential decay
        self.handle_secondary_hand_scroll(secondary_hand_y, dt=dt)
        alpha = min(1.0, 14.0 * dt)
        self.scroll_y += (self.target_scroll_y - self.scroll_y) * alpha

        # 2. Build or refresh dynamic layout
        scale = max(0.85, min(1.5, min(frame_width / 640.0, frame_height / 480.0)))
        self.panel_w = int(min(frame_width - 32, 420 * scale))
        self.panel_h = int(min(frame_height - 36, 360 * scale))
        self.panel_x = (frame_width - self.panel_w) // 2
        self.panel_y = (frame_height - self.panel_h) // 2

        # Content area geometry
        item_h = int(28 * scale)
        item_gap = int(6 * scale)
        item_w = self.panel_w - int(36 * scale)
        start_x = self.panel_x + int(18 * scale)
        base_y = self.panel_y + int(48 * scale) - int(self.scroll_y)

        # Build list of items
        objects_def = [
            (1, "1: ORB"),
            (2, "2: CUBE"),
            (3, "3: PLANET"),
            (4, "4: GHOST ORCHID"),
            (5, "5: BHONDU FACE"),
            (6, "6: JELLYFISH"),
        ]

        items_list: List[MenuItem] = []
        curr_y = base_y

        # Section: OBJECTS
        for obj_id, obj_label in objects_def:
            is_act = (obj_id == display_obj_id)
            items_list.append(
                MenuItem(
                    id=f"obj_{obj_id}",
                    label=obj_label,
                    action_type="OBJECT",
                    action_value=obj_id,
                    x=start_x,
                    y=curr_y,
                    w=item_w,
                    h=item_h,
                    is_active=is_act,
                )
            )
            curr_y += item_h + item_gap

        # Section: INTERACTION MODE
        curr_y += int(4 * scale)
        items_list.append(
            MenuItem(
                id="mode_toggle",
                label=f"MODE: {display_mode.upper()}",
                action_type="MODE",
                action_value=None,
                x=start_x,
                y=curr_y,
                w=item_w,
                h=item_h,
                is_active=False,
            )
        )
        curr_y += item_h + item_gap

        # Section: THEME
        items_list.append(
            MenuItem(
                id="theme_cycle",
                label=f"THEME: {display_theme.upper()}",
                action_type="THEME",
                action_value=None,
                x=start_x,
                y=curr_y,
                w=item_w,
                h=item_h,
                is_active=False,
            )
        )
        curr_y += item_h + item_gap

        # Section: DYNAMIC CAMERAS (Dynamically generated from CameraSelector devices)
        if available_cameras:
            for cam_idx, cam in enumerate(available_cameras):
                if pending_camera_idx is not None:
                    is_active_cam = (cam_idx == pending_camera_idx)
                else:
                    is_active_cam = (cam.name == display_cam_name)
                items_list.append(
                    MenuItem(
                        id=f"cam_{cam_idx}",
                        label=f"CAM: {cam.name}",
                        action_type="CAMERA_SELECT",
                        action_value=cam_idx,
                        x=start_x,
                        y=curr_y,
                        w=item_w,
                        h=item_h,
                        is_active=is_active_cam,
                    )
                )
                curr_y += item_h + item_gap
        else:
            items_list.append(
                MenuItem(
                    id="cam_cycle",
                    label=f"CAM: {display_cam_name}",
                    action_type="CAMERA",
                    action_value=None,
                    x=start_x,
                    y=curr_y,
                    w=item_w,
                    h=item_h,
                    is_active=False,
                )
            )
            curr_y += item_h + item_gap

        # Section: [ CLOSE MENU ]
        close_btn_y = self.panel_y + self.panel_h - int(38 * scale)
        close_item = MenuItem(
            id="close_btn",
            label="[ CLOSE MENU ]",
            action_type="CLOSE",
            action_value=None,
            x=start_x,
            y=close_btn_y,
            w=item_w,
            h=int(30 * scale),
            is_active=False,
        )

        # Update maximum scrollable content height
        total_content_h = (curr_y + int(self.scroll_y)) - (self.panel_y + int(48 * scale))
        visible_content_h = (close_btn_y - (self.panel_y + int(48 * scale)))
        self.max_scroll = max(0.0, float(total_content_h - visible_content_h + int(10 * scale)))

        self.items = items_list
        self.close_item = close_item

        # 3. Hit-test cursor
        selected_action: Optional[Tuple[str, Any]] = None
        self.hovered_item = None

        if cursor_pos_px is not None:
            cx, cy = cursor_pos_px

            # Check close button first (pinned at bottom of panel)
            if (close_item.x <= cx <= close_item.x + close_item.w and
                close_item.y <= cy <= close_item.y + close_item.h):
                close_item.is_hovered = True
                self.hovered_item = close_item
                if click_event:
                    return ("CLOSE", None)

            # Check scrollable menu items
            # Must be within the visible scrolling area of the panel
            clip_top = self.panel_y + int(44 * scale)
            clip_bottom = close_btn_y - int(6 * scale)

            for item in self.items:
                if clip_top <= item.y <= clip_bottom:
                    if (item.x <= cx <= item.x + item.w and
                        item.y <= cy <= item.y + item.h):
                        item.is_hovered = True
                        self.hovered_item = item
                        if click_event:
                            selected_action = (item.action_type, item.action_value)
                            break

        return selected_action

    def render(self, frame: np.ndarray, theme: ColorTheme) -> None:
        """Renders the sci-fi holographic menu with glass backdrop, buttons, and scrollbar."""
        h, w = frame.shape[:2]
        scale = max(0.85, min(1.5, min(w / 640.0, h / 480.0)))
        accent = theme.hud_accent
        primary = theme.ring_primary

        px = self.panel_x
        py = self.panel_y
        pw = self.panel_w
        ph = self.panel_h

        # 1. Semi-transparent glass panel background
        sub_roi = frame[py : py + ph, px : px + pw]
        if sub_roi.size > 0:
            dark_patch = (sub_roi * 0.28).astype(np.uint8)
            frame[py : py + ph, px : px + pw] = dark_patch

        # 2. Outer border and sci-fi corner brackets
        cv2.rectangle(frame, (px, py), (px + pw, py + ph), accent, 1, cv2.LINE_AA)
        bracket_len = int(12 * scale)
        for (bx, by, dx, dy) in [
            (px, py, 1, 1),
            (px + pw - 1, py, -1, 1),
            (px, py + ph - 1, 1, -1),
            (px + pw - 1, py + ph - 1, -1, -1),
        ]:
            cv2.line(frame, (bx, by), (bx + dx * bracket_len, by), (255, 255, 255), 2, cv2.LINE_AA)
            cv2.line(frame, (bx, by), (bx, by + dy * bracket_len), (255, 255, 255), 2, cv2.LINE_AA)

        # 3. Header title
        title_text = "HOLOGRAPHIC CONTROL PANEL"
        font = cv2.FONT_HERSHEY_SIMPLEX
        title_scale = 0.38 * scale
        cv2.putText(
            frame, title_text, (px + int(16 * scale), py + int(24 * scale)),
            font, title_scale, (255, 255, 255), 1, cv2.LINE_AA
        )

        sub_title = "PINCH TO SELECT  |  2ND HAND SCROLLS"
        cv2.putText(
            frame, sub_title, (px + int(16 * scale), py + int(38 * scale)),
            font, 0.28 * scale, (160, 200, 220), 1, cv2.LINE_AA
        )

        # Header divider
        div_y = py + int(44 * scale)
        cv2.line(frame, (px + int(12 * scale), div_y), (px + pw - int(12 * scale), div_y), accent, 1)

        # 4. Scrollable Items (Clipped within visible list bounds)
        clip_top = div_y + 2
        close_btn_y = self.close_item.y
        clip_bottom = close_btn_y - int(6 * scale)

        for item in self.items:
            # Check if within visible viewport
            if item.y + item.h < clip_top or item.y > clip_bottom:
                continue

            ix = item.x
            iy = item.y
            iw = item.w
            ih = item.h

            # Button background
            if item.is_active:
                btn_border = (0, 255, 180)
                btn_bg_alpha = 0.55
                text_color = (255, 255, 255)
            elif item.is_hovered:
                btn_border = (255, 230, 100)
                btn_bg_alpha = 0.45
                text_color = (255, 255, 255)
            else:
                btn_border = (80, 110, 140)
                btn_bg_alpha = 0.20
                text_color = (200, 220, 240)

            # Draw button box
            btn_roi = frame[iy : iy + ih, ix : ix + iw]
            if btn_roi.size > 0:
                overlay = np.full_like(btn_roi, (40, 50, 65)) if item.is_hovered else np.full_like(btn_roi, (20, 25, 35))
                cv2.addWeighted(overlay, btn_bg_alpha, btn_roi, 1.0 - btn_bg_alpha, 0, btn_roi)

            cv2.rectangle(frame, (ix, iy), (ix + iw, iy + ih), btn_border, 1, cv2.LINE_AA)

            # Active indicator pip
            if item.is_active:
                cv2.circle(frame, (ix + int(10 * scale), iy + ih // 2), int(3 * scale), (0, 255, 180), -1, cv2.LINE_AA)

            # Label text
            text_x = ix + int(18 * scale)
            text_y = iy + int(ih * 0.68)
            cv2.putText(frame, item.label, (text_x, text_y), font, 0.33 * scale, text_color, 1, cv2.LINE_AA)

        # 5. Holographic Scrollbar (Right side of scrollable list)
        if self.max_scroll > 0:
            track_x = px + pw - int(10 * scale)
            track_y1 = clip_top + 4
            track_y2 = clip_bottom - 4
            track_h = track_y2 - track_y1

            # Track line
            cv2.line(frame, (track_x, track_y1), (track_x, track_y2), (40, 55, 70), 1)

            # Thumb position
            thumb_h = max(16, int(track_h * 0.35))
            scroll_pct = self.scroll_y / max(0.01, self.max_scroll)
            thumb_y = track_y1 + int(scroll_pct * (track_h - thumb_h))
            cv2.rectangle(
                frame,
                (track_x - 1, thumb_y),
                (track_x + 1, thumb_y + thumb_h),
                accent,
                -1,
            )

        # 6. Pinned [ CLOSE MENU ] Button
        ci = self.close_item
        close_bg = (60, 40, 40) if ci.is_hovered else (30, 20, 20)
        close_border = (120, 200, 255) if ci.is_hovered else accent

        c_roi = frame[ci.y : ci.y + ci.h, ci.x : ci.x + ci.w]
        if c_roi.size > 0:
            c_overlay = np.full_like(c_roi, close_bg)
            cv2.addWeighted(c_overlay, 0.45, c_roi, 0.55, 0, c_roi)

        cv2.rectangle(frame, (ci.x, ci.y), (ci.x + ci.w, ci.y + ci.h), close_border, 1, cv2.LINE_AA)
        c_font_scale = 0.34 * scale
        (cw, ch), _ = cv2.getTextSize(ci.label, font, c_font_scale, 1)
        cx_pos = ci.x + (ci.w - cw) // 2
        cy_pos = ci.y + int(ci.h * 0.65)
        cv2.putText(frame, ci.label, (cx_pos, cy_pos), font, c_font_scale, (255, 255, 255), 1, cv2.LINE_AA)
