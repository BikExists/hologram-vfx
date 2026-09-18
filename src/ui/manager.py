"""Holographic UI Coordinator and Input Dispatcher.

Orchestrates the UI state machine (WELCOME, RUNNING, MENU), the dedicated corner
menu trigger zone, touchless cursor targeting, dynamic menu selections, staged
pending changes, and strict interaction isolation.
"""

import math
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import cv2
import numpy as np

from src.camera import CameraDeviceInfo
from src.hand_tracker import HandData
from src.ui.cursor import HandCursor
from src.ui.menu import HolographicMenu
from src.ui.state import UIState, UIStateMachine
from src.ui.trigger_zone import MenuTriggerZone
from src.ui.welcome import WelcomeScreen
from src.vfx.color_themes import ColorTheme, THEMES, THEME_KEYS


class UIManager:
    """Coordinates UI state, trigger zone, cursor, welcome screen, and menu."""

    def __init__(
        self,
        on_select_object: Optional[Callable[[int], Tuple[bool, str]]] = None,
        on_cycle_mode: Optional[Callable[[], Tuple[object, str]]] = None,
        on_cycle_theme: Optional[Callable[[], str]] = None,
        on_set_theme: Optional[Callable[[Union[str, ColorTheme]], None]] = None,
        on_switch_camera: Optional[Callable[[], Tuple[bool, str]]] = None,
        on_switch_camera_idx: Optional[Callable[[int], Tuple[bool, str]]] = None,
        dwell_time: float = 0.50,
        openness_thresh: float = 0.70,
        trigger_cooldown: float = 0.50,
    ):
        self.state_machine = UIStateMachine(initial_state=UIState.WELCOME)
        self.cursor = HandCursor()
        self.welcome = WelcomeScreen()
        self.menu = HolographicMenu()

        # Callbacks to application
        self.on_select_object = on_select_object
        self.on_cycle_mode = on_cycle_mode
        self.on_cycle_theme = on_cycle_theme
        self.on_set_theme = on_set_theme
        self.on_switch_camera = on_switch_camera
        self.on_switch_camera_idx = on_switch_camera_idx

        # Dedicated Menu Trigger Zone (Corner Dwell Activation)
        self.trigger_zone = MenuTriggerZone(
            dwell_time=dwell_time,
            openness_thresh=openness_thresh,
            cooldown=trigger_cooldown,
        )

        # Staged pending changes during MENU state
        self.pending_object_id: Optional[int] = None
        self.pending_mode_name: Optional[str] = None
        self.pending_theme_name: Optional[str] = None
        self.pending_camera_idx: Optional[int] = None
        self.pending_camera_name: Optional[str] = None

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

    def open_menu(
        self,
        active_object_id: int = 1,
        active_mode_name: str = "STANDARD 2-HAND",
        active_theme_name: str = "CYAN",
        active_camera_name: str = "Default Camera",
        active_camera_idx: Optional[int] = None,
        force: bool = False,
    ) -> Tuple[bool, str]:
        """Opens menu and stages current active settings as pending changes."""
        self.cursor.reset()
        res, msg = self.state_machine.open_menu(force=force)
        if res:
            self.pending_object_id = active_object_id
            self.pending_mode_name = active_mode_name
            self.pending_theme_name = active_theme_name
            self.pending_camera_name = active_camera_name
            self.pending_camera_idx = active_camera_idx
        return res, msg

    def close_menu(
        self,
        active_object_id: Optional[int] = None,
        active_mode_name: Optional[str] = None,
        active_theme_name: Optional[str] = None,
        active_camera_idx: Optional[int] = None,
        force: bool = False,
    ) -> Tuple[bool, str]:
        """Closes menu and commits all staged pending changes."""
        self.cursor.reset()
        res, msg = self.state_machine.close_menu(force=force)
        if res:
            self.commit_pending_changes(
                active_object_id=active_object_id,
                active_mode_name=active_mode_name,
                active_theme_name=active_theme_name,
                active_camera_idx=active_camera_idx,
            )
        return res, msg

    def toggle_menu(
        self,
        force: bool = False,
        active_object_id: int = 1,
        active_mode_name: str = "STANDARD 2-HAND",
        active_theme_name: str = "CYAN",
        active_camera_name: str = "Default Camera",
        active_camera_idx: Optional[int] = None,
    ) -> Tuple[bool, str]:
        """Toggles menu state, committing changes on close."""
        if self.state_machine.state == UIState.MENU:
            return self.close_menu(
                active_object_id=active_object_id,
                active_mode_name=active_mode_name,
                active_theme_name=active_theme_name,
                active_camera_idx=active_camera_idx,
                force=force,
            )
        else:
            return self.open_menu(
                active_object_id=active_object_id,
                active_mode_name=active_mode_name,
                active_theme_name=active_theme_name,
                active_camera_name=active_camera_name,
                active_camera_idx=active_camera_idx,
                force=force,
            )

    def commit_pending_changes(
        self,
        active_object_id: Optional[int] = None,
        active_mode_name: Optional[str] = None,
        active_theme_name: Optional[str] = None,
        active_camera_idx: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Applies staged pending changes to underlying application callbacks."""
        committed: Dict[str, Any] = {}

        # 1. Object selection
        if self.pending_object_id is not None:
            if active_object_id is None or self.pending_object_id != active_object_id:
                if self.on_select_object:
                    self.on_select_object(self.pending_object_id)
                committed["object_id"] = self.pending_object_id

        # 2. Mode selection
        if self.pending_mode_name is not None:
            if active_mode_name is None or self.pending_mode_name != active_mode_name:
                if self.on_cycle_mode:
                    self.on_cycle_mode()
                committed["mode_name"] = self.pending_mode_name

        # 3. Theme selection
        if self.pending_theme_name is not None:
            if active_theme_name is None or self.pending_theme_name != active_theme_name:
                if self.on_set_theme:
                    self.on_set_theme(self.pending_theme_name)
                elif self.on_cycle_theme:
                    self.on_cycle_theme()
                committed["theme_name"] = self.pending_theme_name

        # 4. Camera selection
        if self.pending_camera_idx is not None:
            if active_camera_idx is None or self.pending_camera_idx != active_camera_idx:
                if self.on_switch_camera_idx:
                    self.on_switch_camera_idx(self.pending_camera_idx)
                elif self.on_switch_camera:
                    self.on_switch_camera()
                committed["camera_idx"] = self.pending_camera_idx

        # Reset pending variables
        self.pending_object_id = None
        self.pending_mode_name = None
        self.pending_theme_name = None
        self.pending_camera_idx = None
        self.pending_camera_name = None

        return committed

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
            # Check for deliberate corner menu trigger zone activation
            if self.trigger_zone.update(detected_hands, frame_width, frame_height, dt=dt, now=now):
                self.open_menu(
                    active_object_id=active_object_id,
                    active_mode_name=active_mode_name,
                    active_theme_name=active_theme_name,
                    active_camera_name=active_camera_name,
                    force=True,
                )
                events["opened_menu"] = True

        # ---------------------------------------------------------------------
        # 3. MENU STATE
        # ---------------------------------------------------------------------
        elif self.state_machine.state == UIState.MENU:
            # Initialize pending variables if not set
            if self.pending_object_id is None:
                self.pending_object_id = active_object_id
            if self.pending_mode_name is None:
                self.pending_mode_name = active_mode_name
            if self.pending_theme_name is None:
                self.pending_theme_name = active_theme_name
            if self.pending_camera_name is None:
                self.pending_camera_name = active_camera_name

            # Check if corner trigger zone is activated to close menu
            if self.trigger_zone.update(detected_hands, frame_width, frame_height, dt=dt, now=now):
                self.close_menu(
                    active_object_id=active_object_id,
                    active_mode_name=active_mode_name,
                    active_theme_name=active_theme_name,
                    force=True,
                )
                events["closed_menu"] = True
                return events

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
                pending_object_id=self.pending_object_id,
                pending_mode_name=self.pending_mode_name,
                pending_theme_name=self.pending_theme_name,
                pending_camera_idx=self.pending_camera_idx,
                pending_camera_name=self.pending_camera_name,
            )

            self.cursor.is_hovered = (self.menu.hovered_item is not None)

            # Check if menu action triggered
            if menu_action:
                action_type, action_val = menu_action
                if action_type == "OBJECT":
                    self.pending_object_id = action_val
                    events["staged_object"] = action_val
                elif action_type == "MODE":
                    cur_m = (self.pending_mode_name or active_mode_name).upper()
                    if "INDEPENDENT" in cur_m:
                        self.pending_mode_name = "STANDARD 2-HAND"
                    else:
                        self.pending_mode_name = "INDEPENDENT DUAL-HAND"
                    events["staged_mode"] = self.pending_mode_name
                elif action_type == "THEME":
                    cur_t = (self.pending_theme_name or active_theme_name).lower()
                    t_idx = 0
                    for i, k in enumerate(THEME_KEYS):
                        if k == cur_t or THEMES[k].name.lower() == cur_t:
                            t_idx = i
                            break
                    next_k = THEME_KEYS[(t_idx + 1) % len(THEME_KEYS)]
                    self.pending_theme_name = THEMES[next_k].name
                    events["staged_theme"] = self.pending_theme_name
                elif action_type == "CAMERA_SELECT":
                    self.pending_camera_idx = action_val
                    if available_cameras and 0 <= action_val < len(available_cameras):
                        self.pending_camera_name = available_cameras[action_val].name
                    events["staged_camera"] = action_val
                elif action_type == "CAMERA":
                    events["staged_camera"] = True
                elif action_type in ("CLOSE", "CLOSE_MENU"):
                    self.close_menu(
                        active_object_id=active_object_id,
                        active_mode_name=active_mode_name,
                        active_theme_name=active_theme_name,
                        force=True,
                    )
                    events["closed_menu"] = True

        return events

    def render(self, frame: np.ndarray, theme: ColorTheme) -> None:
        """Renders active UI overlay elements (Welcome, Menu, Cursor, Trigger Zone)."""
        # 1. Welcome Screen
        if self.state_machine.state == UIState.WELCOME:
            self.welcome.render(frame, theme)

        # 2. Holographic Menu
        elif self.state_machine.state == UIState.MENU:
            self.menu.render(frame, theme)
            # Render cursor on top of menu
            self.cursor.render(frame, theme)
            # Render persistent trigger zone in corner as [ CLOSE ]
            self.trigger_zone.render(frame, theme, is_menu_open=True)

        # 3. Running State
        elif self.state_machine.state == UIState.RUNNING:
            # Render persistent trigger zone in corner as [ MENU ]
            self.trigger_zone.render(frame, theme, is_menu_open=False)
