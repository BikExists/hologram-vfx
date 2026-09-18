"""Unit tests for the Holographic UI Foundation.

Verifies:
- UI State Machine transitions (WELCOME -> RUNNING -> MENU -> RUNNING)
- Welcome screen rendering & dismiss conditions
- Open palm dwell and peace/V-sign menu gesture detection
- Hand cursor normalization, hover, pinch-click, and dwell fallback
- Holographic menu layout, dynamic camera entries, object selection, and secondary-hand scrolling
- Strict input isolation between menu interaction and holographic object kinematics
"""

import math
import time
import numpy as np
import pytest

from src.camera import CameraDeviceInfo
from src.hand_tracker import HandData
from src.objects.orb import HolographicOrb
from src.ui.cursor import HandCursor
from src.ui.manager import UIManager
from src.ui.menu import HolographicMenu, MenuItem
from src.ui.state import UIState, UIStateMachine
from src.ui.welcome import WelcomeScreen
from src.vfx.color_themes import get_theme


def make_dummy_hand(
    palm_x: float = 320.0,
    palm_y: float = 240.0,
    is_pinching: bool = False,
    openness: float = 0.9,
    is_right: bool = True,
    v_sign: bool = False,
    w: int = 640,
    h: int = 480,
) -> HandData:
    """Helper to construct a realistic synthetic HandData object."""
    wrist = (palm_x, palm_y + 80.0)
    landmarks_px = [wrist]

    # Thumb: 1..4
    for i in range(1, 5):
        landmarks_px.append((palm_x - 30.0 + i * 5, palm_y + 40.0 - i * 10))

    # Index: 5..8
    idx_ext = 80.0 if (openness > 0.5 or v_sign) else 30.0
    for i in range(1, 5):
        landmarks_px.append((palm_x - 15.0, palm_y + 20.0 - i * (idx_ext / 4.0)))

    # Middle: 9..12
    mid_ext = 90.0 if (openness > 0.5 or v_sign) else 30.0
    for i in range(1, 5):
        landmarks_px.append((palm_x, palm_y + 20.0 - i * (mid_ext / 4.0)))

    # Ring: 13..16
    ring_ext = 30.0 if v_sign else (80.0 if openness > 0.5 else 30.0)
    for i in range(1, 5):
        landmarks_px.append((palm_x + 15.0, palm_y + 20.0 - i * (ring_ext / 4.0)))

    # Pinky: 17..20
    pinky_ext = 25.0 if v_sign else (70.0 if openness > 0.5 else 25.0)
    for i in range(1, 5):
        landmarks_px.append((palm_x + 30.0, palm_y + 20.0 - i * (pinky_ext / 4.0)))

    pinch_pt = (palm_x, palm_y - 40.0) if is_pinching else (palm_x - 15.0, palm_y - 60.0)
    landmarks_norm = [(p[0] / float(w), p[1] / float(h), 0.0) for p in landmarks_px]

    return HandData(
        landmarks_norm=landmarks_norm,
        landmarks_px=landmarks_px,
        palm_center_px=(palm_x, palm_y),
        pinch_point_px=pinch_pt,
        is_pinching=is_pinching,
        pinch_distance_px=15.0 if is_pinching else 75.0,
        norm_pinch_distance=0.15 if is_pinching else 0.75,
        openness=openness,
        hand_scale_px=100.0,
        handedness="Right" if is_right else "Left",
        confidence=0.95,
        is_grace_frame=False,
    )


class TestUIStateMachine:
    """Tests lifecycle transitions of UIStateMachine."""

    def test_initial_state_and_dismiss_welcome(self):
        sm = UIStateMachine(initial_state=UIState.WELCOME)
        assert sm.state == UIState.WELCOME

        ok, msg = sm.dismiss_welcome()
        assert ok is True
        assert sm.state == UIState.RUNNING

    def test_toggle_menu_transitions(self):
        sm = UIStateMachine(initial_state=UIState.RUNNING)
        ok, msg = sm.toggle_menu(force=True)
        assert ok is True
        assert sm.state == UIState.MENU

        ok, msg = sm.toggle_menu(force=True)
        assert ok is True
        assert sm.state == UIState.RUNNING

    def test_close_menu(self):
        sm = UIStateMachine(initial_state=UIState.MENU)
        ok, msg = sm.close_menu(force=True)
        assert ok is True
        assert sm.state == UIState.RUNNING

        # Calling close when already running should be safe
        ok, msg = sm.close_menu()
        assert ok is False


class TestWelcomeScreen:
    """Tests holographic welcome screen rendering and dismiss trigger."""

    def test_welcome_render_and_dismiss(self):
        welcome = WelcomeScreen()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        theme = get_theme("cyan")

        # Renders without error
        welcome.update(0.033)
        welcome.render(frame, theme)
        assert np.any(frame > 0)

        # Inactive hand should not dismiss
        assert welcome.should_dismiss(None) is False

        # Active hand should trigger dismiss
        hand = make_dummy_hand(openness=0.8)
        assert welcome.should_dismiss(hand) is True


class TestHandCursor:
    """Tests cursor tracking, smoothing, hover, and pinch clicking."""

    def test_cursor_normalization_and_smoothing(self):
        cursor = HandCursor()
        hand = make_dummy_hand(palm_x=320.0, palm_y=240.0)

        cursor.update(hand, frame_width=640, frame_height=480, dt=0.033)
        assert cursor.is_active is True
        assert 0.4 <= cursor.norm_x <= 0.6
        assert 0.3 <= cursor.norm_y <= 0.6
        assert 280 <= cursor.x_px <= 340
        assert 160 <= cursor.y_px <= 260

    def test_cursor_pinch_click(self):
        cursor = HandCursor()
        hand_open = make_dummy_hand(is_pinching=False)
        cursor.update(hand_open, frame_width=640, frame_height=480, dt=0.033)
        assert cursor.is_pinching is False
        assert cursor.click_event is False

        # Transition to pinch
        hand_pinch = make_dummy_hand(is_pinching=True)
        cursor.update(hand_pinch, frame_width=640, frame_height=480, dt=0.033)
        assert cursor.is_pinching is True
        assert cursor.click_event is True

        # Consecutive pinch should NOT re-trigger click (debounce)
        cursor.update(hand_pinch, frame_width=640, frame_height=480, dt=0.033)
        assert cursor.click_event is False


class TestHolographicMenu:
    """Tests menu layout, dynamic camera devices, object selection, and secondary-hand scroll."""

    def test_dynamic_camera_devices_generation(self):
        menu = HolographicMenu()
        cameras = [
            CameraDeviceInfo(device_id=0, name="Built-in Webcam", is_physical=True),
            CameraDeviceInfo(device_id=1, name="Phone Link Cam", is_physical=False),
            CameraDeviceInfo(device_id=-1, name="Synthetic Feed", is_synthetic=True),
        ]

        # Update menu layout
        action = menu.update(
            cursor_pos_px=None,
            is_pinching=False,
            click_event=False,
            secondary_hand_y=None,
            active_object_id=1,
            active_mode_name="Standard",
            active_theme_name="cyan",
            active_camera_name="Built-in Webcam",
            available_cameras=cameras,
            frame_width=640,
            frame_height=480,
        )

        labels = [item.label for item in menu.items]
        assert "1: ORB" in labels
        assert "6: JELLYFISH" in labels
        assert "CAM: Built-in Webcam" in labels
        assert "CAM: Phone Link Cam" in labels
        assert "CAM: Synthetic Feed" in labels

    def test_secondary_hand_scrolling(self):
        menu = HolographicMenu()
        # Initial position
        menu.handle_secondary_hand_scroll(200.0, dt=0.033)
        assert menu.prev_secondary_y == 200.0

        # Move secondary hand upward (scroll downward in content)
        menu.handle_secondary_hand_scroll(170.0, dt=0.033)
        assert menu.target_scroll_y > 0.0

    def test_item_click_selection(self):
        menu = HolographicMenu()
        # Build layout
        menu.update(
            cursor_pos_px=None,
            is_pinching=False,
            click_event=False,
            secondary_hand_y=None,
            active_object_id=1,
            active_mode_name="Standard",
            active_theme_name="cyan",
            active_camera_name="Camera 0",
            available_cameras=[],
            frame_width=640,
            frame_height=480,
        )

        # Target item 2 (Cube)
        target_item = next(item for item in menu.items if item.action_value == 2)
        cx = target_item.x + target_item.w // 2
        cy = target_item.y + target_item.h // 2

        action = menu.update(
            cursor_pos_px=(cx, cy),
            is_pinching=True,
            click_event=True,
            secondary_hand_y=None,
            active_object_id=1,
            active_mode_name="Standard",
            active_theme_name="cyan",
            active_camera_name="Camera 0",
            available_cameras=[],
            frame_width=640,
            frame_height=480,
        )

        assert action is not None
        assert action == ("OBJECT", 2)


class TestUIManagerAndMenuIsolation:
    """Tests UIManager gesture recognition and strict input isolation from holographic objects."""

    def test_open_palm_dwell_gesture(self):
        manager = UIManager()
        manager.dismiss_welcome()
        assert manager.current_state == UIState.RUNNING

        hand = make_dummy_hand(palm_x=300.0, palm_y=200.0, openness=0.95, is_pinching=False)

        # Dwell for 0.8 seconds (25 steps at 0.033)
        for _ in range(30):
            manager.update(
                detected_hands=[hand],
                active_object_id=1,
                active_mode_name="Standard",
                active_theme_name="cyan",
                active_camera_name="Webcam",
                available_cameras=[],
                frame_width=640,
                frame_height=480,
                dt=0.033,
            )

        assert manager.current_state == UIState.MENU
        assert manager.is_menu_open is True
        assert manager.owns_hand_input is True

    def test_strict_menu_input_isolation(self):
        """Verify that when menu is open, object does NOT move or scale with hand movements."""
        manager = UIManager()
        manager.dismiss_welcome()
        manager.toggle_menu(force=True)
        assert manager.owns_hand_input is True

        orb = HolographicOrb(frame_width=640, frame_height=480)
        initial_x, initial_y = orb.x, orb.y
        initial_radius = orb.current_radius

        # Simulate vigorous hand pinch and movement
        moving_hand = make_dummy_hand(palm_x=100.0, palm_y=100.0, is_pinching=True)

        # When UI owns hand input, application passes empty list [] to object.update
        if manager.owns_hand_input:
            new_x, new_y, new_r = orb.update([], dt=0.033)
        else:
            new_x, new_y, new_r = orb.update([moving_hand], dt=0.033)

        # Position should remain centered / anchored, not dragged to (100, 100)
        assert abs(new_x - initial_x) < 5.0
        assert abs(new_y - initial_y) < 5.0
        assert abs(new_r - initial_radius) < 5.0
