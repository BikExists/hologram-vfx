"""Tests for Holographic Interaction Mode Selector & Independent Dual-Hand Control.

Validates:
1. Mode enum/selection cycling (STANDARD vs INDEPENDENT)
2. Primary hand movement changes position only
3. Primary hand rotation changes object rotation only
4. Secondary hand openness changes scale only
5. Secondary hand rotation changes theme/color only
6. Strict independence between primary and secondary controls
7. Deterministic hand assignment (Left -> Primary, Right -> Secondary)
8. Detection order reversal invariance
9. Zero position jump on mode switch
10. Zero scale jump on mode switch
11. Zero rotation jump on mode switch
12. One-hand fallback in independent mode
13. Holographic Orb independent dual-hand control
14. Holographic Cube independent dual-hand control
15. Holographic Planet independent dual-hand control
16. Standard two-hand transform mode baseline preservationJ17. Object manager mode synchronization and persistence
"""

import math
from typing import List, Optional, Tuple
import numpy as np
import pytest

from src.gestures import (InteractionMode, compute_hand_orientation, unwrap_angle_delta)
from src.hand_tracker import HandData
from src.interaction import OrbController
from src.objects import (HolographicCube, HolographicObjectManager, HolographicOrb, HolographicPlanet)


def make_oriented_mock_hand(palm_center: Tuple[float, float], orientation_rad: float = -math.pi / 2.0, handedness: str = 'Left', openness: float = 0.5, is_pinching: bool = False, hand_scale: float = 60.0) -> HandData:
    dx = math.cos(orientation_rad) * 30.0
    dy = math.sin(orientation_rad) * 30.0
    wrist = (palm_center[0] - dx, palm_center[1] - dy)
    middle_mcp = (palm_center[0] + dx, palm_center[1] + dy)
    px_lms = [palm_center] * 21
    px_lms[0] = wrist
    px_lms[9] = middle_mcp
    norm_lms = [(p[0] / 640.0, p[1] / 480.0, 0.0) for p in px_lms]
    return HandData(landmarks_norm=norm_lms, landmarks_px=px_lms, palm_center_px=palm_center, pinch_point_px=palm_center, is_pinching=is_pinching, pinch_distance_px=15.0 if is_pinching else 45.0, norm_pinch_distance=0.2 if is_pinching else 0.6, openness=openness, hand_scale_px=hand_scale, handedness=handedness, confidence=0.95, is_grace_frame=False)


def test_mode_enum_and_cycling():
    assert InteractionMode.STANDARD == 'STANDARD'
    assert InteractionMode.INDEPENDENT == 'INDEPENDENT'
    ctrl = OrbController(frame_width=640, frame_height=480)
    assert ctrl.selected_mode == InteractionMode.STANDARD
    assert ctrl.get_mode_display_name() == 'STANDARD 2-HAND'
    mode = ctrl.cycle_interaction_mode()
    assert mode == InteractionMode.INDEPENDENT
    assert ctrl.selected_mode == InteractionMode.INDEPENDENT
    assert ctrl.get_mode_display_name() == 'INDEPENDENT DUAL-HAND'
    mode = ctrl.cycle_interaction_mode()
    assert mode == InteractionMode.STANDARD
    assert ctrl.selected_mode == InteractionMode.STANDARD


def test_primary_hand_movement_changes_position_only():
    theme_events = []
    ctrl = OrbController(frame_width=640, frame_height=480, initial_mode=InteractionMode.INDEPENDENT, on_theme_change=lambda t: theme_events.append(t))
    h_prim = make_oriented_mock_hand((200.0, 240.0), handedness='Left')
    h_sec = make_oriented_mock_hand((450.0, 240.0), handedness='Right', openness=0.5)
    ctrl.update([h_prim, h_sec], dt=0.033)
    init_radius = ctrl.current_radius
    init_rot = ctrl.rotation
    init_theme = ctrl.current_theme_key
    init_x, init_y = ctrl.x, ctrl.y
    for step in range(25):
        h_prim_moved = make_oriented_mock_hand((200.0 + 60.0, 240.0 + 40.0), handedness='Left')
        ctrl.update([h_prim_moved, h_sec], dt=0.033)
    assert math.isclose(ctrl.x, init_x + 60.0, abs_tol=5.0)
    assert math.isclose(ctrl.y, init_y + 40.0, abs_tol=5.0)
    assert math.isclose(ctrl.current_radius, init_radius, abs_tol=1.0)
    assert math.isclose(ctrl.rotation, init_rot, abs_tol=0.05)
    assert ctrl.current_theme_key == init_theme
    assert len(theme_events) == 0


def test_primary_hand_rotation_changes_rotation_only():
    theme_events = []
    ctrl = OrbController(frame_width=640, frame_height=480, initial_mode=InteractionMode.INDEPENDENT, on_theme_change=lambda t: theme_events.append(t))
    h_prim = make_oriented_mock_hand((200.0, 240.0), orientation_rad=-math.pi / 2.0, handedness='Left')
    h_sec = make_oriented_mock_hand((450.0, 240.0), handedness='Right', openness=0.5)
    ctrl.update([h_prim, h_sec], dt=0.033)
    init_radius = ctrl.current_radius
    init_x, init_y = ctrl.x, ctrl.y
    init_theme = ctrl.current_theme_key
    target_angle = -math.pi / 2.0 + 0.785
    for _ in range(25):
        h_prim_rot = make_oriented_mock_hand((200.0, 240.0), orientation_rad=target_angle, handedness='Left')
        ctrl.update([h_prim_rot, h_sec], dt=0.033)
    assert math.isclose(ctrl.rotation, 0.785, abs_tol=0.1)
    assert math.isclose(ctrl.x, init_x, abs_tol=2.0)
    assert math.isclose(ctrl.y, init_y, abs_tol=2.0)
    assert math.isclose(ctrl.current_radius, init_radius, abs_tol=1.0)
    assert ctrl.current_theme_key == init_theme
    assert len(theme_events) == 0


def test_secondary_hand_openness_changes_scale_only():
    ctrl = OrbController(frame_width=640, frame_height=480, initial_mode=InteractionMode.INDEPENDENT)
    h_prim = make_oriented_mock_hand((200.0, 240.0), handedness='Left')
    h_sec = make_oriented_mock_hand((450.0, 240.0), handedness='Right', openness=0.3)
    ctrl.update([h_prim, h_sec], dt=0.033)
    init_radius = ctrl.current_radius
    init_rot = ctrl.rotation
    init_x, init_y = ctrl.x, ctrl.y
    for _ in range(25):
        h_sec_open = make_oriented_mock_hand((450.0, 240.0), handedness='Right', openness=1.0)
        ctrl.update([h_prim, h_sec_open], dt=0.033)
    assert ctrl.current_radius > init_radius + 20.0
    assert ctrl.two_hand_scale > 1.0
    assert math.isclose(ctrl.x, init_x, abs_tol=2.0)
    assert math.isclose(ctrl.y, init_y, abs_tol=2.0)
    assert math.isclose(ctrl.rotation, init_rot, abs_tol=0.05)


def test_secondary_hand_rotation_changes_theme_only():
    theme_events = []
    ctrl = OrbController(frame_width=640, frame_height=480, initial_mode=InteractionMode.INDEPENDENT, initial_theme='cyan', on_theme_change=lambda t: theme_events.append(t))
    h_prim = make_oriented_mock_hand((200.0, 240.0), orientation_rad=-math.pi / 2.0, handedness='Left')
    h_sec = make_oriented_mock_hand((450.0, 240.0), orientation_rad=-math.pi / 2.0, handedness='Right')
    ctrl.update([h_prim, h_sec], dt=0.033)
    init_rot = ctrl.rotation
    init_radius = ctrl.current_radius
    init_x, init_y = ctrl.x, ctrl.y
    assert ctrl.current_theme_key == 'cyan'
    sec_angle_new = -math.pi / 2.0 + math.radians(95.0)
    for _ in range(25):
        h_sec_rot = make_oriented_mock_hand((450.0, 240.0), orientation_rad=sec_angle_new, handedness='Right')
        ctrl.update([h_prim, h_sec_rot], dt=0.033)
    assert ctrl.current_theme_key == 'solar'
    assert 'solar' in theme_events
    assert math.isclose(ctrl.rotation, init_rot, abs_tol=0.05)
    assert math.isclose(ctrl.x, init_x, abs_tol=2.0)
    assert math.isclose(ctrl.y, init_y, abs_tol=2.0)
    assert math.isclose(ctrl.current_radius, init_radius, abs_tol=1.0)


def test_primary_and_secondary_controls_do_not_interfere():
    ctrl = OrbController(frame_width=640, frame_height=480, initial_mode=InteractionMode.INDEPENDENT)
    h_prim = make_oriented_mock_hand((200.0, 240.0), handedness='Left')
    h_sec = make_oriented_mock_hand((400.0, 240.0), handedness='Right')
    ctrl.update([h_prim, h_sec], dt=0.033)
    obj_pos_before = (ctrl.x, ctrl.y)
    for _ in range(25):
        h_sec_far = make_oriented_mock_hand((600.0, 440.0), handedness='Right')
        ctrl.update([h_prim, h_sec_far], dt=0.033)
    assert math.isclose(ctrl.x, obj_pos_before[0], abs_tol=2.0)
    assert math.isclose(ctrl.y, obj_pos_before[1], abs_tol=2.0)


def test_hand_assignment_determinism_and_order_invariance():
    ctrl = OrbController(frame_width=640, frame_height=480)
    h_l = make_oriented_mock_hand((150.0, 240.0), handedness='Left')
    h_r = make_oriented_mock_hand((480.0, 240.0), handedness='Right')
    prim1, sec1 = ctrl._assign_hands([h_l, h_r])
    assert prim1.handedness == 'Left'
    assert sec1.handedness == 'Right'
    prim2, sec2 = ctrl._assign_hands([h_r, h_l])
    assert prim2.handedness == 'Left'
    assert sec2.handedness == 'Right'
    h1_same = make_oriented_mock_hand((100.0, 200.0), handedness='Right')
    h2_same = make_oriented_mock_hand((500.0, 200.0), handedness='Right')
    prim3, sec3 = ctrl._assign_hands([h2_same, h1_same])
    assert prim3.palm_center_px[0] == 100.0
    assert sec3.palm_center_px[0] == 500.0


def test_mode_transition_zero_jump():
    ctrl = OrbController(frame_width=640, frame_height=480)
    h_l = make_oriented_mock_hand((200.0, 240.0), handedness='Left')
    h_r = make_oriented_mock_hand((440.0, 240.0), handedness='Right')
    for _ in range(15):
        ctrl.update([h_l, h_r], dt=0.033)
    pos_before = (ctrl.x, ctrl.y)
    scale_before = ctrl.current_radius
    rot_before = ctrl.rotation
    ctrl.cycle_interaction_mode()
    assert ctrl.selected_mode == InteractionMode.INDEPENDENT
    ctrl.update([h_l, h_r], dt=0.033)
    assert math.isclose(ctrl.x, pos_before[0], abs_tol=2.0)
    assert math.isclose(ctrl.y, pos_before[1], abs_tol=2.0)
    assert math.isclose(ctrl.current_radius, scale_before, abs_tol=1.0)
    assert math.isclose(ctrl.rotation, rot_before, abs_tol=0.05)
    ctrl.cycle_interaction_mode()
    assert ctrl.selected_mode == InteractionMode.STANDARD
    ctrl.update([h_l, h_r], dt=0.033)
    assert math.isclose(ctrl.x, pos_before[0], abs_tol=2.0)
    assert math.isclose(ctrl.y, pos_before[1], abs_tol=2.0)
    assert math.isclose(ctrl.current_radius, scale_before, abs_tol=1.0)
    assert math.isclose(ctrl.rotation, rot_before, abs_tol=0.05)


def test_one_hand_fallback_in_independent_mode():
    ctrl = OrbController(frame_width=640, frame_height=480, initial_mode=InteractionMode.INDEPENDENT)
    h_l = make_oriented_mock_hand((200.0, 240.0), handedness='Left')
    h_r = make_oriented_mock_hand((440.0, 240.0), handedness='Right')
    for _ in range(15):
        ctrl.update([h_l, h_r], dt=0.033)
    r_at_exit = ctrl.current_radius
    rot_at_exit = ctrl.rotation
    ctrl.update([h_l], dt=0.033)
    assert ctrl.interaction_mode == 'SINGLE_HAND'
    assert math.isclose(ctrl.current_radius, r_at_exit, abs_tol=1.5)
    assert math.isclose(ctrl.rotation, rot_at_exit, abs_tol=0.05)


@pytest.mark.parametrize('obj_class', [HolographicOrb, HolographicCube, HolographicPlanet])
def test_all_objects_support_independent_dual_hand_control(obj_class):
    obj = obj_class(frame_width=640, frame_height=480)
    obj.selected_mode = InteractionMode.INDEPENDENT
    h_prim = make_oriented_mock_hand((200.0, 240.0), handedness='Left')
    h_sec = make_oriented_mock_hand((440.0, 240.0), handedness='Right')
    for _ in range(15):
        x, y, r = obj.update([h_prim, h_sec], dt=0.033)
    assert obj.interaction_mode == 'INDEPENDENT_DUAL_HAND'
    assert obj.selected_mode == InteractionMode.INDEPENDENT
    assert 'INDEP' in obj.get_state_label(hand_detected=True)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    obj.render(frame, dt=0.033)
    assert np.any(frame > 0)


def test_standard_two_hand_baseline_preserved():
    ctrl = OrbController(frame_width=640, frame_height=480)
    assert ctrl.selected_mode == InteractionMode.STANDARD
    h_l = make_oriented_mock_hand((200.0, 240.0), handedness='Left')
    h_r = make_oriented_mock_hand((400.0, 240.0), handedness='Right')
    ctrl.update([h_l, h_r], dt=0.033)
    init_radius = ctrl.current_radius
    h_r_far = make_oriented_mock_hand((550.0, 240.0), handedness='Right')
    for _ in range(25):
        ctrl.update([h_l, h_r_far], dt=0.033)
    assert ctrl.interaction_mode == 'TWO_HANDS'
    assert ctrl.current_radius > init_radius + 15.0


def test_object_manager_mode_synchronization_and_switching():
    mgr = HolographicObjectManager(frame_width=640, frame_height=480)
    assert mgr.get_active_object().selected_mode == InteractionMode.STANDARD
    new_mode, msg = mgr.cycle_interaction_mode()
    assert new_mode == InteractionMode.INDEPENDENT
    assert 'INDEPENDENT' in msg
    assert mgr.get_active_object().selected_mode == InteractionMode.INDEPENDENT
    success, msg2 = mgr.select_object(2)
    assert success
    cube = mgr.get_active_object()
    assert cube.name == 'Cube'
    assert cube.selected_mode == InteractionMode.INDEPENDENT
    success, msg3 = mgr.select_object(3)
    assert success
    planet = mgr.get_active_object()
    assert planet.name == 'Planet'
    assert planet.selected_mode == InteractionMode.INDEPENDENT
