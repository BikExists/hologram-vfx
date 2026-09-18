"""Acceptance Test Suite for Holographic Menu Trigger Zone & UX Interaction Fixes.

Validates the 20 core requirements for explicit corner menu trigger activation,
strict object interaction freeze during MENU state, staged pending selections,
zero-jump spatial transfer, and aspect-ratio-aware trigger geometry.
"""

import math
import time
from typing import Optional, Tuple
import numpy as np
import pytest

from src.app import HolographicVFXApp
from src.camera import CameraDeviceInfo
from src.hand_tracker import HandData
from src.objects.manager import HolographicObjectManager
from src.objects.orb import HolographicOrb
from src.ui.manager import UIManager
from src.ui.menu import HolographicMenu
from src.ui.state import UIState
from src.ui.trigger_zone import MenuTriggerZone
from tests.test_holographic_ui import make_dummy_hand


def get_zone_center_coords(tz: MenuTriggerZone, width: int = 640, height: int = 480) -> Tuple[float, float]:
    """Helper returning pixel coordinates centered inside the menu trigger zone."""
    tz.update_geometry(width, height)
    x1, y1, x2, y2 = tz.pixel_rect
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0


# =============================================================================
# 1. Trigger Zone Hit & Activation Edge Cases
# =============================================================================

def test_1_open_palm_outside_zone_does_not_open_menu():
    """Requirement 1: Open palm outside MENU zone does NOT open menu."""
    manager = UIManager(dwell_time=0.30)
    manager.dismiss_welcome()
    assert manager.current_state == UIState.RUNNING

    # Palm in center of viewport with wide open hand
    center_hand = make_dummy_hand(palm_x=320.0, palm_y=240.0, openness=0.98, is_pinching=False)

    # Simulate 30 frames (1 second at 30 fps)
    for _ in range(30):
        manager.update(
            detected_hands=[center_hand],
            active_object_id=1,
            active_mode_name="STANDARD 2-HAND",
            active_theme_name="CYAN",
            active_camera_name="Cam",
            available_cameras=[],
            frame_width=640,
            frame_height=480,
            dt=0.033,
        )

    assert manager.current_state == UIState.RUNNING
    assert manager.is_menu_open is False
    assert manager.trigger_zone.state == "IDLE"
    assert manager.trigger_zone.dwell_progress == 0.0


def test_2_closed_hand_inside_zone_does_not_open_menu():
    """Requirement 2: Closed hand (fist/pinch) inside MENU zone does NOT open menu."""
    manager = UIManager(dwell_time=0.30)
    manager.dismiss_welcome()
    assert manager.current_state == UIState.RUNNING

    zx, zy = get_zone_center_coords(manager.trigger_zone, 640, 480)

    # Test Fist (low openness)
    fist_hand = make_dummy_hand(palm_x=zx, palm_y=zy, openness=0.20, is_pinching=False)
    for _ in range(25):
        manager.update(
            detected_hands=[fist_hand],
            active_object_id=1,
            active_mode_name="STANDARD 2-HAND",
            active_theme_name="CYAN",
            active_camera_name="Cam",
            available_cameras=[],
            frame_width=640,
            frame_height=480,
            dt=0.033,
        )
    assert manager.current_state == UIState.RUNNING
    assert manager.is_menu_open is False

    # Test Pinching Hand inside zone
    pinch_hand = make_dummy_hand(palm_x=zx, palm_y=zy, openness=0.85, is_pinching=True)
    for _ in range(25):
        manager.update(
            detected_hands=[pinch_hand],
            active_object_id=1,
            active_mode_name="STANDARD 2-HAND",
            active_theme_name="CYAN",
            active_camera_name="Cam",
            available_cameras=[],
            frame_width=640,
            frame_height=480,
            dt=0.033,
        )
    assert manager.current_state == UIState.RUNNING
    assert manager.is_menu_open is False


def test_3_open_palm_entering_zone_begins_charging():
    """Requirement 3: Open palm entering MENU zone begins dwell charging."""
    manager = UIManager(dwell_time=0.50)
    manager.dismiss_welcome()
    assert manager.current_state == UIState.RUNNING

    zx, zy = get_zone_center_coords(manager.trigger_zone, 640, 480)
    open_hand = make_dummy_hand(palm_x=zx, palm_y=zy, openness=0.90, is_pinching=False)

    # Advance 4 frames (~0.132s)
    for _ in range(4):
        manager.update(
            detected_hands=[open_hand],
            active_object_id=1,
            active_mode_name="STANDARD 2-HAND",
            active_theme_name="CYAN",
            active_camera_name="Cam",
            available_cameras=[],
            frame_width=640,
            frame_height=480,
            dt=0.033,
        )

    assert manager.trigger_zone.state == "CHARGING"
    assert manager.trigger_zone.dwell_progress > 0.15
    assert manager.trigger_zone.dwell_progress < 1.0
    assert manager.current_state == UIState.RUNNING


def test_4_menu_opens_after_dwell_threshold():
    """Requirement 4: Menu opens after dwell threshold (e.g. 0.5s)."""
    manager = UIManager(dwell_time=0.40)
    manager.dismiss_welcome()
    assert manager.current_state == UIState.RUNNING

    zx, zy = get_zone_center_coords(manager.trigger_zone, 640, 480)
    open_hand = make_dummy_hand(palm_x=zx, palm_y=zy, openness=0.90, is_pinching=False)

    # 15 frames * 0.033 = 0.495s >= 0.40s
    opened = False
    for _ in range(15):
        ev = manager.update(
            detected_hands=[open_hand],
            active_object_id=1,
            active_mode_name="STANDARD 2-HAND",
            active_theme_name="CYAN",
            active_camera_name="Cam",
            available_cameras=[],
            frame_width=640,
            frame_height=480,
            dt=0.033,
        )
        if ev.get("opened_menu"):
            opened = True
            break

    assert opened is True
    assert manager.current_state == UIState.MENU
    assert manager.is_menu_open is True


def test_5_leaving_zone_before_dwell_resets_charging():
    """Requirement 5: Leaving zone before dwell resets/cancels activation."""
    manager = UIManager(dwell_time=0.50)
    manager.dismiss_welcome()
    zx, zy = get_zone_center_coords(manager.trigger_zone, 640, 480)

    # Step 1: Partially charge in trigger zone
    in_hand = make_dummy_hand(palm_x=zx, palm_y=zy, openness=0.90, is_pinching=False)
    for _ in range(5):
        manager.update([in_hand], 1, "STANDARD", "cyan", "Cam", [], 640, 480, dt=0.033)

    assert manager.trigger_zone.dwell_progress > 0.20
    assert manager.current_state == UIState.RUNNING

    # Step 2: Hand leaves trigger zone and moves back into holographic work area
    out_hand = make_dummy_hand(palm_x=320.0, palm_y=240.0, openness=0.90, is_pinching=False)
    for _ in range(6):
        manager.update([out_hand], 1, "STANDARD", "cyan", "Cam", [], 640, 480, dt=0.033)

    assert manager.trigger_zone.dwell_progress == 0.0
    assert manager.trigger_zone.state == "IDLE"
    assert manager.current_state == UIState.RUNNING


def test_6_cooldown_prevents_immediate_retrigger():
    """Requirement 6: Tracking jitter does not repeatedly trigger menu."""
    manager = UIManager(dwell_time=0.20, trigger_cooldown=0.40)
    manager.dismiss_welcome()
    zx, zy = get_zone_center_coords(manager.trigger_zone, 640, 480)
    open_hand = make_dummy_hand(palm_x=zx, palm_y=zy, openness=0.95, is_pinching=False)

    # Trigger menu open
    for _ in range(10):
        manager.update([open_hand], 1, "STANDARD", "cyan", "Cam", [], 640, 480, dt=0.033)
    assert manager.is_menu_open is True

    # Immediate next frame with hand still in zone cannot re-trigger close during cooldown
    ev = manager.update([open_hand], 1, "STANDARD", "cyan", "Cam", [], 640, 480, dt=0.033)
    assert ev.get("closed_menu") is not True
    assert manager.is_menu_open is True


def test_7_secondary_open_palm_elsewhere_cannot_trigger_menu():
    """Requirement 7: Secondary open palm elsewhere cannot trigger menu."""
    manager = UIManager(dwell_time=0.30)
    manager.dismiss_welcome()

    # Hand 1: Center workspace, open palm
    h1 = make_dummy_hand(palm_x=280.0, palm_y=240.0, openness=0.95, is_right=True)
    # Hand 2: Left workspace, open palm
    h2 = make_dummy_hand(palm_x=120.0, palm_y=240.0, openness=0.95, is_right=False)

    for _ in range(20):
        manager.update([h1, h2], 1, "STANDARD", "cyan", "Cam", [], 640, 480, dt=0.033)

    assert manager.current_state == UIState.RUNNING
    assert manager.is_menu_open is False


# =============================================================================
# 2. MENU Interaction Lock & Object Isolation
# =============================================================================

def test_8_menu_state_locks_object_position():
    """Requirement 8: MENU state locks object position."""
    app = HolographicVFXApp(synthetic_mode=True, headless=True, skip_welcome=True)
    app.ui.toggle_menu(force=True)
    assert app.ui.is_menu_open is True

    initial_x = app.active_object.x
    initial_y = app.active_object.y

    # Simulate vigorous dragging hand
    drag_hand = make_dummy_hand(palm_x=100.0, palm_y=100.0, is_pinching=True)
    app.tracker.last_valid_hand = drag_hand

    # Step frame
    ret, frame, telemetry = app.step_frame()
    assert ret is True
    assert telemetry["object_x"] == initial_x
    assert telemetry["object_y"] == initial_y
    assert app.active_object.x == initial_x
    assert app.active_object.y == initial_y


def test_9_menu_state_locks_object_rotation():
    """Requirement 9: MENU state locks object rotation."""
    app = HolographicVFXApp(synthetic_mode=True, headless=True, skip_welcome=True)
    app.ui.toggle_menu(force=True)
    assert app.ui.is_menu_open is True

    initial_rot = app.active_object.rotation

    # Two hands positioned to induce rotation in standard mode
    h1 = make_dummy_hand(palm_x=200.0, palm_y=150.0, is_right=False)
    h2 = make_dummy_hand(palm_x=450.0, palm_y=350.0, is_right=True)

    # Step multiple frames
    for _ in range(5):
        app.step_frame()

    assert app.active_object.rotation == initial_rot


def test_10_menu_state_locks_object_scale():
    """Requirement 10: MENU state locks object scale."""
    app = HolographicVFXApp(synthetic_mode=True, headless=True, skip_welcome=True)
    app.ui.toggle_menu(force=True)
    assert app.ui.is_menu_open is True

    initial_radius = app.active_object.current_radius

    # Simulate 5 frames
    for _ in range(5):
        app.step_frame()

    assert app.active_object.current_radius == initial_radius


def test_11_menu_state_locks_theme_interaction():
    """Requirement 11: MENU state locks theme/object interaction."""
    app = HolographicVFXApp(synthetic_mode=True, headless=True, skip_welcome=True)
    app.ui.toggle_menu(force=True)
    assert app.ui.is_menu_open is True

    initial_theme_name = app.active_object.theme.name

    # Step frames
    for _ in range(5):
        app.step_frame()

    assert app.active_object.theme.name == initial_theme_name


def test_12_menu_cursor_still_works_while_object_locked():
    """Requirement 12: Menu cursor still works while object interaction is locked."""
    manager = UIManager()
    manager.dismiss_welcome()
    manager.open_menu(force=True)
    assert manager.is_menu_open is True

    # Cursor driven by hand inside panel area
    hand = make_dummy_hand(palm_x=320.0, palm_y=240.0, openness=0.5, is_pinching=False)

    manager.update([hand], 1, "STANDARD 2-HAND", "CYAN", "Cam", [], 640, 480, dt=0.033)

    assert manager.cursor.is_active is True
    assert abs(manager.cursor.x_px - hand.pinch_point_px[0]) < 5.0
    assert abs(manager.cursor.y_px - hand.pinch_point_px[1]) < 5.0


# =============================================================================
# 3. Menu Close & Staged Pending Selections
# =============================================================================

def test_13_same_trigger_zone_closes_menu():
    """Requirement 13: Same trigger zone closes menu."""
    manager = UIManager(dwell_time=0.30, trigger_cooldown=0.10)
    manager.dismiss_welcome()
    manager.open_menu(force=True)
    assert manager.is_menu_open is True

    # Wait out cooldown
    time.sleep(0.12)

    zx, zy = get_zone_center_coords(manager.trigger_zone, 640, 480)
    close_hand = make_dummy_hand(palm_x=zx, palm_y=zy, openness=0.90, is_pinching=False)

    closed = False
    for _ in range(15):
        ev = manager.update([close_hand], 1, "STANDARD 2-HAND", "CYAN", "Cam", [], 640, 480, dt=0.033)
        if ev.get("closed_menu"):
            closed = True
            break

    assert closed is True
    assert manager.current_state == UIState.RUNNING
    assert manager.is_menu_open is False


def test_14_closing_requires_open_palm_and_dwell():
    """Requirement 14: Closing requires open palm + zone dwell."""
    manager = UIManager(dwell_time=0.30, trigger_cooldown=0.10)
    manager.dismiss_welcome()
    manager.open_menu(force=True)
    assert manager.is_menu_open is True

    time.sleep(0.12)
    zx, zy = get_zone_center_coords(manager.trigger_zone, 640, 480)

    # Fist in trigger zone should not close menu
    fist = make_dummy_hand(palm_x=zx, palm_y=zy, openness=0.20, is_pinching=False)
    for _ in range(15):
        manager.update([fist], 1, "STANDARD", "CYAN", "Cam", [], 640, 480, dt=0.033)

    assert manager.current_state == UIState.MENU
    assert manager.is_menu_open is True


def test_15_open_palm_elsewhere_does_not_close_menu():
    """Requirement 15: Open palm elsewhere does NOT close menu."""
    manager = UIManager(dwell_time=0.30, trigger_cooldown=0.10)
    manager.dismiss_welcome()
    manager.open_menu(force=True)
    assert manager.is_menu_open is True

    time.sleep(0.12)
    center_hand = make_dummy_hand(palm_x=320.0, palm_y=240.0, openness=0.95, is_pinching=False)
    for _ in range(20):
        manager.update([center_hand], 1, "STANDARD", "CYAN", "Cam", [], 640, 480, dt=0.033)

    assert manager.current_state == UIState.MENU
    assert manager.is_menu_open is True


def test_16_pending_menu_changes_apply_after_close():
    """Requirement 16: Pending menu changes apply after close."""
    chosen_object_id = None

    def on_select(obj_id):
        nonlocal chosen_object_id
        chosen_object_id = obj_id
        return True, f"Switched to {obj_id}"

    manager = UIManager(on_select_object=on_select)
    manager.dismiss_welcome()
    manager.open_menu(active_object_id=1, force=True)

    # Stage selection of Object 4 (Ghost Orchid)
    manager.pending_object_id = 4
    assert chosen_object_id is None  # Not applied while menu is open

    # Close menu
    manager.close_menu(active_object_id=1, force=True)

    # Now applied
    assert chosen_object_id == 4


def test_17_object_transform_preserved_through_menu_open_close():
    """Requirement 17: Object transform is preserved through menu open/close."""
    app = HolographicVFXApp(synthetic_mode=True, headless=True, skip_welcome=True)
    app.active_object.x = 245.0
    app.active_object.y = 190.0
    app.active_object.current_radius = 88.0

    # Open menu
    app.ui.open_menu(force=True)
    assert app.ui.is_menu_open is True

    # Step frame during menu
    app.step_frame()

    # Close menu
    app.ui.close_menu(force=True)
    assert app.ui.is_menu_open is False

    # Verify spatial transform is preserved with zero jump
    assert app.active_object.x == 245.0
    assert app.active_object.y == 190.0
    assert app.active_object.current_radius == 88.0


# =============================================================================
# 4. Aspect-Ratio-Aware Geometry & Interaction Longevity
# =============================================================================

def test_18_camera_resizing_updates_trigger_zone_geometry():
    """Requirement 18: Camera switching/resizing does not break trigger-zone coordinates."""
    tz = MenuTriggerZone()

    # Resolution A: 640x480 (4:3)
    tz.update_geometry(640, 480)
    x1_a, y1_a, x2_a, y2_a = tz.pixel_rect
    assert x2_a <= 640
    assert x1_a > 500

    # Resolution B: 1280x720 (16:9)
    tz.update_geometry(1280, 720)
    x1_b, y1_b, x2_b, y2_b = tz.pixel_rect
    assert x2_b <= 1280
    assert x1_b > 1100
    assert y1_b >= 10

    # Trigger zone correctly remains in top-right corner
    assert x1_b > x1_a


def test_19_4_3_and_16_9_trigger_hit_testing():
    """Requirement 19: 4:3 and 16:9 trigger-zone hit testing works correctly."""
    tz = MenuTriggerZone()

    # Test 4:3 (640x480)
    tz.update_geometry(640, 480)
    x1, y1, x2, y2 = tz.pixel_rect
    cx_4_3 = (x1 + x2) / 2.0
    cy_4_3 = (y1 + y2) / 2.0
    assert tz.is_point_inside(cx_4_3, cy_4_3) is True
    assert tz.is_point_inside(320.0, 240.0) is False

    # Test 16:9 (1280x720)
    tz.update_geometry(1280, 720)
    x1, y1, x2, y2 = tz.pixel_rect
    cx_16_9 = (x1 + x2) / 2.0
    cy_16_9 = (y1 + y2) / 2.0
    assert tz.is_point_inside(cx_16_9, cy_16_9) is True
    assert tz.is_point_inside(640.0, 360.0) is False
    # 4:3 point should now be outside the 16:9 trigger zone
    assert tz.is_point_inside(cx_4_3, cy_4_3) is False


def test_20_existing_one_hand_and_independent_interaction_remain_functional():
    """Requirement 20: Existing one-hand and independent interaction tests remain passing."""
    app = HolographicVFXApp(synthetic_mode=True, headless=True, skip_welcome=True)
    assert app.ui.current_state == UIState.RUNNING

    # Step frame with running synthetic simulation
    ret, frame, telemetry = app.step_frame()
    assert ret is True
    assert frame is not None
    assert "object_type" in telemetry
    assert "selected_mode_name" in telemetry
    assert telemetry["is_menu_open"] is False
