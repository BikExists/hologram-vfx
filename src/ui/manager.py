"""Holographic UI Coordinator and Input Dispatcher.

Orchestrates the UI state machine (WELCOME, RUNNING, MENU), the dedicated menu
activation gesture, touchless cursor targeting, dynamic menu selections, and
strict interaction isolation.
"""

import math
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
import cv2
import numpy as np

from src.camera import CameraDeviceInfo
from src.hand_tracker import HandData
from src.ui.cursor import HandCursor
from src.ui.menu import HolographicMenu
from src.ui.state import UIState, UIStateMachine
from src.ui.welcome import WelcomeScreen
from src.vfx.color_themes import ColorTheme


class UIManager:
    """Coordinates UI state, gestures, cursor, welcome screen, and menu."""

    def __init__(
        self,
        on_select_object: Optional[Callable[[int], Tuple[bool, str]]] = None,
        on_cycle_mode: Optional[Callable[[], Tuple[object, str]]] = None,
        on_cycle_theme: Optional[Callable[[], str]] = None,
        on_switch_camera: Optional[Callable[[], Tuple[bool, str]]] = None,
        on_switch_camera_idx: Optional[Callable[[int], Tuple[bool, str]]] = None,
    ):
        self.state_machine = UIStateMachine(initial_state=UIState.WELCOME)
        self.cursor = HandCursor()
        self.welcome = WelcomeScreen()
        self.menu = HolographicMenu()

        # Callbacks to application
        self.on_select_object = on_select_object
        self.on_cycle_mode = on_cycle_mode
        self.on_cycle_theme = on_cycle_theme
        self.on_switch_camera = on_switch_camera
        self.on_switch_camera_idx = on_switch_camera_idx

        # Menu gesture detection state (Open Palm Dwell / V-Pose)
        self.menu_gesture_charge: float = 0.0  # 0.0 to 1.0
        self.menu_gesture_charge_time: float = 0.60  # seconds to trigger
        self.menu_gesture_anchor_px: Tuple[float, float] = (0.0, 0.0)
        self.menu_gesture_cooldown: float = 0.50
        self.last_menu_toggle_time: float = 0.0

    @property
    def current_state(self) -> UIState:
        """Active UI State."""
        return self.state_machine.state

    @property
    def is_menu_open(self) -> bool:
        """True if the holographic menu is actively displayed."""
        return self.state_machine.state == UIState.MENU

    @property
    def is_welcome_active(self) -> bool:
        """True if the welcome screen is actively displayed."""
        return self.state_machine.state == UIState.WELCOME

    @property
    def owns_hand_input(self) -> bool:
        """True if UI exclusively consumes hand interaction (isolating object scene)."""
        return self.state_machine.state in (UIState.WELCOME, UIState.MENU)

    def dismiss_welcome(self) -> Tuple[bool, str]:
        """Dismisses the welcome screen."""
        self.cursor.reset()
        return self.state_machine.dismiss_welcome()

    def toggle_menu(self, force: bool = False) -> Tuple[bool, str]:
        """Toggles menu state."""
        self.cursor.reset()
        return self.state_machine.toggle_menu(force=force)

    def _detect_menu_gesture(
        self,
        hand: Optional[HandData],
        dt: float,
        now: float,
    ) -> bool:
        """Detects deliberate open-palm dwell or peace-sign menu activation gesture."""
        if hand is None or not hand.landmarks_px:
            self.menu_gesture_charge = 0.0
            return False

        if (now - self.last_menu_toggle_time) < self.menu_gesture_cooldown:
            self.menu_gesture_charge = 0.0
            return False

        px, py = hand.palm_center_px
        dist = math.hypot(px - self.menu_gesture_anchor_px[0], py - self.menu_gesture_anchor_px[1])

        # Check Gesture Pose:
        # Pose 1: Wide Open Palm held stationary (Iron Man / Stop sign)
        is_open_palm = (hand.openness > 0.80 and not hand.is_pinching)

        # Pose 2: Peace / V-sign (Index + Middle extended, Ring + Pinky curled)
        is_v_sign = False
        if len(hand.landmarks_px) >= 21 and not hand.is_pinching:
            pts = hand.landmarks_px
            wrist = pts[0]
            # Extension: distance from wrist to fingertip vs wrist to PIP joint
            d_index_tip = math.hypot(pts[8][0] - wrist[0], pts[8][1] - wrist[1])
            d_index_pip = math.hypot(pts[6][0] - wrist[0], pts[6][1] - wrist[1])
            d_mid_tip = math.hypot(pts[12][0] - wrist[0], pts[12][1] - wrist[1])
            d_mid_pip = math.hypot(pts[10][0] - wrist[0], pts[10][1] - wrist[1])
            d_ring_tip = math.hypot(pts[16][0] - wrist[0], pts[16][1] - wrist[1])
            d_ring_pip = math.hypot(pts[14][0] - wrist[0], pts[14][1] - wrist[1])
            d_pinky_tip = math.hypot(pts[20][0] - wrist[0], pts[20][1] - wrist[1])
            d_pinky_pip = math.hypot(pts[18][0] - wrist[0], pts[18][1] - wrist[1])

            idx_ext = d_index_tip > d_index_pip * 1.15
            mid_ext = d_mid_tip > d_mid_pip * 1.15
            ring_curled = d_ring_tip < d_ring_pip * 1.10
            pinky_curled = d_pinky_tip < d_pinky_pip * 1.10

            is_v_sign = (idx_ext and mid_ext and ring_curled and pinky_curled)

        is_valid_pose = is_open_palm or is_v_sign
        is_still = dist < 20.0  # Steady position

        if is_valid_pose and is_still:
            charge_rate = 1.6 if is_v_sign else 1.0
            self.menu_gesture_charge += (dt / self.menu_gesture_charge_time) * charge_rate
            self.menu_gesture_charge = min(1.0, self.menu_gesture_charge)

            if self.menu_gesture_charge >= 1.0:
                self.menu_gesture_charge = 0.0
                self.last_menu_toggle_time = now
                self.menu_gesture_anchor_px = (px, py)
                return True
        else:
            self.menu_gesture_anchor_px = (px, py)
            self.menu_gesture_charge = max(0.0, self.menu_gesture_charge - dt * 3.0)

        return False

    def update(
        self,
        detected_hands: List[HandData],
        active_object_id: int,
        active_mode_name: str,
        active_theme_name: str,
        active_camera_name: str,
        available_cameras: List[CameraDeviceInfo],
        frame_width: int,
        frame_height: int,
        dt: float = 0.033,
    ) -> Dict[str, Any]:
        """Processes hand input against active UI state, updates cursor, and dispatches actions."""
        now = time.perf_counter()
        primary_hand = detected_hands[0] if detected_hands else None
        secondary_hand = detected_hands[1] if len(detected_hands) > 1 else None

        events: Dict[str, Any] = {}

        # ---------------------------------------------------------------------
        # 1. WELCOME STATE
        # ---------------------------------------------------------------------
        if self.state_machine.state == UIState.WELCOME:
            self.welcome.update(dt)
            if primary_hand is not None and self.welcome.should_dismiss(primary_hand):
                self.dismiss_welcome()
                events["dismissed_welcome"] = True

        # ---------------------------------------------------------------------
        # 2. RUNNING STATE
        # ---------------------------------------------------------------------
        elif self.state_machine.state == UIState.RUNNING:
            # Check for dedicated menu open gesture
            if self._detect_menu_gesture(primary_hand, dt, now):
                self.toggle_menu(force=True)
                events["opened_menu"] = True

        # ---------------------------------------------------------------------
        # 3. MENU STATE
        # ---------------------------------------------------------------------
        elif self.state_machine.state == UIState.MENU:
            # Update cursor for primary hand
            self.cursor.update(
                primary_hand,
                frame_width=frame_width,
                frame_height=frame_height,
                dt=dt,
                timestamp=now,
            )

            # Secondary hand vertical position for smooth scrolling
            sec_y = secondary_hand.palm_center_px[1] if secondary_hand else None

            # Cursor position in pixels
            cursor_pos = (self.cursor.x_px, self.cursor.y_px) if self.cursor.is_active else None

            # Update menu hit-testing and secondary-hand scrolling
            menu_action = self.menu.update(
                cursor_pos_px=cursor_pos,
                is_pinching=self.cursor.is_pinching,
                click_event=self.cursor.click_event,
                secondary_hand_y=sec_y,
                active_object_id=active_object_id,
                active_mode_name=active_mode_name,
                active_theme_name=active_theme_name,
                active_camera_name=active_camera_name,
                available_cameras=available_cameras,
                frame_width=frame_width,
                frame_height=frame_height,
                dt=dt,
            )

            self.cursor.is_hovered = (self.menu.hovered_item is not None)

            # Check if menu action triggered
            if menu_action:
                action_type, action_val = menu_action
                if action_type == "OBJECT" and self.on_select_object:
                    self.on_select_object(action_val)
                    events["selected_object"] = action_val
                elif action_type == "MODE" and self.on_cycle_mode:
                    self.on_cycle_mode()
                    events["cycled_mode"] = True
                elif action_type == "THEME" and self.on_cycle_theme:
                    self.on_cycle_theme()
                    events["cycled_theme"] = True
                elif action_type == "CAMERA_SELECT":
                    if self.on_switch_camera_idx:
                        self.on_switch_camera_idx(action_val)
                        events["switched_camera"] = True
                    elif self.on_switch_camera:
                        self.on_switch_camera()
                        events["switched_camera"] = True
                elif action_type == "CAMERA" and self.on_switch_camera:
                    self.on_switch_camera()
                    events["switched_camera"] = True
                elif action_type in ("CLOSE", "CLOSE_MENU"):
                    self.state_machine.close_menu()
                    self.cursor.reset()
                    events["closed_menu"] = True

            # Also allow dedicated menu gesture to close menu
            if self._detect_menu_gesture(primary_hand, dt, now):
                self.state_machine.close_menu(force=True)
                self.cursor.reset()
                events["closed_menu"] = True

        return events

    def render(self, frame: np.ndarray, theme: ColorTheme) -> None:
        """Renders the active UI overlay elements (Welcome, Menu, Cursor, Gesture Reticle)."""
        # 1. Welcome Screen
        if self.state_machine.state == UIState.WELCOME:
            self.welcome.render(frame, theme)

        # 2. Holographic Menu
        elif self.state_machine.state == UIState.MENU:
            self.menu.render(frame, theme)
            # Render cursor on top of menu
            self.cursor.render(frame, theme)

        # 3. Gesture Charging Ring (when charging menu toggle in RUNNING state)
        if self.menu_gesture_charge > 0.05 and self.menu_gesture_anchor_px[0] > 0:
            cx, cy = int(self.menu_gesture_anchor_px[0]), int(self.menu_gesture_anchor_px[1])
            h_f, w_f = frame.shape[:2]
            if 0 <= cx < w_f and 0 <= cy < h_f:
                r_charge = 36
                arc_angle = int(self.menu_gesture_charge * 360)
                # Subtle background ring
                cv2.circle(frame, (cx, cy), r_charge, (60, 80, 100), 1, cv2.LINE_AA)
                # Active charging progress arc
                cv2.ellipse(
                    frame, (cx, cy), (r_charge, r_charge),
                    -90, 0, arc_angle, (100, 255, 230), 2, cv2.LINE_AA
                )
                cv2.putText(
                    frame, "MENU", (cx - 16, cy + 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.32, (200, 255, 255), 1, cv2.LINE_AA
                )
