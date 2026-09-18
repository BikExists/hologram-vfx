"""Tests for two-hand interaction: simultaneous distance-based scaling and orientation-based rotation."""

import math
from typing import List, Optional, Tuple
import numpy as np
import pytest

from src.gestures import (
    compute_two_hand_angle,
    compute_two_hand_distance,
    compute_two_hand_midpoint,
    unwrap_angle_delta,
)
from src.hand_tracker import HandData, HandTracker
from src.interaction import OrbController
from src.objects import (
    BaseHolographicObject,
    HolographicCube,
    HolographicObjectManager,
    HolographicOrb,
    HolographicPlanet,
)


def make_mock_hand(
    palm_center: Tuple[float, float],
    pinch_pt: Optional[Tuple[float, float]] = None,
    handedness: str = "Right",
    is_pinching: bool = False,
    openness: float = 0.5,
    hand_scale: float = 80.0,
) -> HandData:
    """Helper to generate mock HandData for testing."""
    if pinch_pt is None:
        pinch_pt = palm_center
    norm_lms = [(palm_center[0] / 640.0, palm_center[1] / 480.0, 0.0)] * 21
    px_lms = [palm_center] * 21
    return HandData(
        landmarks_norm=norm_lms,
        landmarks_px=px_lms,
        palm_center_px=palm_center,
        pinch_point_px=pinch_pt,
        is_pinching=is_pinching,
        pinch_distance_px=15.0 if is_pinching else 45.0,
        norm_pinch_distance=0.2 if is_pinching else 0.6,
        openness=openness,
        hand_scale_px=hand_scale,
        handedness=handedness,
        confidence=0.95,
        is_grace_frame=False,
    )


def test_two_hand_distance_calculation():
    """Verifies Euclidean distance between two hand points."""
    p1 = (100.0, 100.0)
    p2 = (400.0, 500.0)
    d = compute_two_hand_distance(p1, p2)
    assert math.isclose(d, 500.0, rel_tol=1e-5)

    p3 = (200.0, 200.0)
    p4 = (200.0, 200.0)
    assert compute_two_hand_distance(p3, p4) == 0.0


def test_two_hand_angle_calculation():
    """Verifies orientation angle calculation from pt_a to pt_b in [-pi, pi]."""
    p_center = (200.0, 200.0)

    # Directly to the right: 0 rad
    p_right = (300.0, 200.0)
    assert math.isclose(compute_two_hand_angle(p_center, p_right), 0.0, abs_tol=1e-5)

    # Directly downwards (screen +Y): +pi/2 rad (+90 deg)
    p_down = (200.0, 300.0)
    assert math.isclose(compute_two_hand_angle(p_center, p_down), math.pi * 0.5, abs_tol=1e-5)

    # Directly upwards (screen -Y): -pi/2 rad (-90 deg)
    p_up = (200.0, 100.0)
    assert math.isclose(compute_two_hand_angle(p_center, p_up), -math.pi * 0.5, abs_tol=1e-5)

    # Directly to the left: +pi or -pi rad (+/-180 deg)
    p_left = (100.0, 200.0)
    assert math.isclose(abs(compute_two_hand_angle(p_center, p_left)), math.pi, abs_tol=1e-5)


def test_two_hand_midpoint_calculation():
    """Verifies midpoint computation between two hands."""
    p1 = (100.0, 200.0)
    p2 = (300.0, 400.0)
    mid = compute_two_hand_midpoint(p1, p2)
    assert mid == (200.0, 300.0)


def test_angle_wraparound_handling():
    """Verifies that unwrap_angle_delta accurately unwraps crossing +/-180 deg boundary."""
    # 1. Normal small change
    d1 = unwrap_angle_delta(0.2, 0.1)
    assert math.isclose(d1, 0.1, abs_tol=1e-5)

    # 2. Crossing from +178 deg to -178 deg (+4 deg counter-clockwise rotation)
    ang_prev = math.radians(178.0)
    ang_curr = math.radians(-178.0)
    delta = unwrap_angle_delta(ang_curr, ang_prev)
    assert math.isclose(math.degrees(delta), 4.0, abs_tol=1e-4)

    # 3. Crossing from -178 deg to +178 deg (-4 deg clockwise rotation)
    ang_prev2 = math.radians(-178.0)
    ang_curr2 = math.radians(178.0)
    delta2 = unwrap_angle_delta(ang_curr2, ang_prev2)
    assert math.isclose(math.degrees(delta2), -4.0, abs_tol=1e-4)


def test_two_hand_scale_mapping_and_clamping():
    """Verifies distance ratio scales object radius and respects clamping bounds."""
    ctrl = OrbController(
        frame_width=640,
        frame_height=480,
        min_radius=30.0,
        max_radius=120.0,
        default_radius=60.0,
    )

    # Entry frame: hands at distance 200.0
    h_left = make_mock_hand((220.0, 240.0), handedness="Left")
    h_right = make_mock_hand((420.0, 240.0), handedness="Right")

    # Step into two-hand mode
    ctrl.update([h_left, h_right], dt=0.033)
    assert ctrl.interaction_mode == "TWO_HANDS"
    assert math.isclose(ctrl.ref_two_hand_distance, 200.0, abs_tol=1.0)
    initial_r = ctrl.current_radius

    # Expand distance to 400.0 (2x expansion) over several frames
    h_left_exp = make_mock_hand((120.0, 240.0), handedness="Left")
    h_right_exp = make_mock_hand((520.0, 240.0), handedness="Right")
    for _ in range(25):
        ctrl.update([h_left_exp, h_right_exp], dt=0.033)

    # Radius should have expanded towards 2x (approx 120.0, smoothed)
    assert ctrl.current_radius > initial_r * 1.5
    assert ctrl.two_hand_scale > 1.5

    # Extreme distance should be clamped, not explode
    h_left_huge = make_mock_hand((0.0, 240.0), handedness="Left")
    h_right_huge = make_mock_hand((5000.0, 240.0), handedness="Right")
    for _ in range(30):
        ctrl.update([h_left_huge, h_right_huge], dt=0.033)
    assert ctrl.current_radius <= ctrl.max_radius * 1.6 + 1e-3

    # Extreme tiny distance should be clamped, not collapse to 0
    h_left_tiny = make_mock_hand((319.0, 240.0), handedness="Left")
    h_right_tiny = make_mock_hand((321.0, 240.0), handedness="Right")
    for _ in range(30):
        ctrl.update([h_left_tiny, h_right_tiny], dt=0.033)
    assert ctrl.current_radius >= ctrl.min_radius * 0.6 - 1e-3


def test_two_hand_rotation_mapping():
    """Verifies that rotating hands rotates the object continuously."""
    ctrl = OrbController(frame_width=640, frame_height=480)

    # Start with hands aligned horizontally: angle 0.0
    h_l0 = make_mock_hand((220.0, 240.0), handedness="Left")
    h_r0 = make_mock_hand((420.0, 240.0), handedness="Right")
    ctrl.update([h_l0, h_r0], dt=0.033)
    assert ctrl.rotation == 0.0

    # Rotate hands by +45 deg (Left hand stays at (220, 240), Right hand rotates down-right)
    target_rad = math.radians(45.0)
    dist = 200.0
    rx = 220.0 + dist * math.cos(target_rad)
    ry = 240.0 + dist * math.sin(target_rad)

    h_l1 = make_mock_hand((220.0, 240.0), handedness="Left")
    h_r1 = make_mock_hand((rx, ry), handedness="Right")

    for _ in range(25):
        ctrl.update([h_l1, h_r1], dt=0.033)

    # Rotation should have tracked towards +45 deg (+0.785 rad)
    assert math.isclose(ctrl.rotation, target_rad, abs_tol=0.15)


def test_one_to_two_hand_transition_no_jump():
    """Verifies zero instantaneous jump in position, radius, or rotation when second hand appears."""
    ctrl = OrbController(frame_width=640, frame_height=480, default_radius=55.0)

    # Frame 1: Single hand hovering
    h_single = make_mock_hand((300.0, 240.0), openness=0.5)
    ctrl.update([h_single], dt=0.033)
    pos_before = (ctrl.x, ctrl.y)
    r_before = ctrl.current_radius
    rot_before = ctrl.rotation
    assert ctrl.interaction_mode == "SINGLE_HAND"

    # Frame 2: Second hand appears
    h_left = make_mock_hand((220.0, 240.0), handedness="Left")
    h_right = make_mock_hand((380.0, 240.0), handedness="Right")
    ctrl.update([h_left, h_right], dt=0.033)

    assert ctrl.interaction_mode == "TWO_HANDS"
    # Position should not pop
    assert math.isclose(ctrl.x, pos_before[0], abs_tol=2.0)
    assert math.isclose(ctrl.y, pos_before[1], abs_tol=2.0)
    # Radius should not pop
    assert math.isclose(ctrl.current_radius, r_before, abs_tol=1.0)
    # Rotation should be continuous
    assert math.isclose(ctrl.rotation, rot_before, abs_tol=0.05)


def test_two_to_one_hand_transition_preserves_transform():
    """Verifies that removing the second hand preserves current scale and rotation without snapping."""
    ctrl = OrbController(frame_width=640, frame_height=480, default_radius=55.0)

    # 1. Scale and rotate in two-hand mode
    h_l = make_mock_hand((180.0, 200.0), handedness="Left")
    h_r = make_mock_hand((460.0, 280.0), handedness="Right")
    ctrl.update([h_l, h_r], dt=0.033)

    # Expand distance and rotate
    h_r_exp = make_mock_hand((520.0, 310.0), handedness="Right")
    for _ in range(25):
        ctrl.update([h_l, h_r_exp], dt=0.033)

    assert ctrl.interaction_mode == "TWO_HANDS"
    r_scaled = ctrl.current_radius
    rot_achieved = ctrl.rotation

    # 2. Hand 2 disappears, only Hand 1 remains
    ctrl.update([h_l], dt=0.033)
    assert ctrl.interaction_mode == "SINGLE_HAND"

    # Transform must be preserved without instant pop
    assert math.isclose(ctrl.current_radius, r_scaled, abs_tol=2.0)
    assert math.isclose(ctrl.rotation, rot_achieved, abs_tol=0.05)


def test_two_to_zero_hand_transition_preserves_transform():
    """Verifies that losing all hands preserves object transform into floating state."""
    ctrl = OrbController(frame_width=640, frame_height=480)

    h_l = make_mock_hand((200.0, 240.0), handedness="Left")
    h_r = make_mock_hand((440.0, 240.0), handedness="Right")
    ctrl.update([h_l, h_r], dt=0.033)

    h_r_rot = make_mock_hand((440.0, 300.0), handedness="Right")
    for _ in range(25):
        ctrl.update([h_l, h_r_rot], dt=0.033)

    rot_achieved = ctrl.rotation
    assert ctrl.interaction_mode == "TWO_HANDS"

    # Both hands disappear
    ctrl.update([], dt=0.033)
    assert ctrl.interaction_mode == "NO_HANDS"
    # Rotation remains preserved
    assert math.isclose(ctrl.rotation, rot_achieved, abs_tol=0.05)


def test_shared_transform_behavior_across_objects():
    """Verifies that two-hand scaling and rotation work identically across Orb, Cube, and Planet."""
    objects = [
        HolographicOrb(frame_width=640, frame_height=480),
        HolographicCube(frame_width=640, frame_height=480),
        HolographicPlanet(frame_width=640, frame_height=480),
    ]

    h_l0 = make_mock_hand((200.0, 240.0), handedness="Left")
    h_r0 = make_mock_hand((400.0, 240.0), handedness="Right")
    # Rotated hands
    h_r_rot = make_mock_hand((400.0, 320.0), handedness="Right")

    for obj in objects:
        obj.reset_position()
        obj.update([h_l0, h_r0], dt=0.033)
        for _ in range(25):
            x, y, r = obj.update([h_l0, h_r_rot], dt=0.033)

        assert obj.interaction_mode == "TWO_HANDS"
        assert obj.current_radius > 0
        assert hasattr(obj, "rotation")
        assert obj.rotation != 0.0

        # Verify object specific visual connections
        if isinstance(obj, HolographicCube):
            # 3D rotation matrix incorporates two-hand rotation
            rot_mat = obj._get_rotation_matrix()
            assert rot_mat.shape == (3, 3)
        elif isinstance(obj, HolographicPlanet):
            # Effective tilt incorporates two-hand rotation
            assert obj.effective_tilt_deg != obj.axial_tilt_deg

        # Render test: verify buffer invariant and no crash with two-hand state
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        obj.render(frame, pinch_pt=None, dt=0.033)
        assert np.any(frame > 0)


def test_object_manager_preserves_two_hand_transforms_on_switch():
    """Verifies switching objects (1->2->3) preserves scale and rotation seamlessly."""
    mgr = HolographicObjectManager(frame_width=640, frame_height=480)

    # 1. Active object is Orb (1)
    orb = mgr.get_active_object()
    h_l = make_mock_hand((180.0, 200.0), handedness="Left")
    h_r = make_mock_hand((460.0, 280.0), handedness="Right")

    for _ in range(15):
        orb.update([h_l, h_r], dt=0.033)

    orb_r = orb.current_radius
    orb_rot = orb.rotation
    assert orb.interaction_mode == "TWO_HANDS"

    # 2. Switch to Cube (2)
    ok, msg = mgr.select_object(2)
    assert ok is True
    cube = mgr.get_active_object()
    assert cube.name == "Cube"
    assert math.isclose(cube.current_radius, orb_r, abs_tol=1e-4)
    assert math.isclose(cube.rotation, orb_rot, abs_tol=1e-4)
    assert cube.interaction_mode == "TWO_HANDS"

    # 3. Switch to Planet (3)
    ok3, msg3 = mgr.select_object(3)
    assert ok3 is True
    planet = mgr.get_active_object()
    assert planet.name == "Planet"
    assert math.isclose(planet.current_radius, orb_r, abs_tol=1e-4)
    assert math.isclose(planet.rotation, orb_rot, abs_tol=1e-4)
    assert planet.interaction_mode == "TWO_HANDS"
