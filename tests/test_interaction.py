"""Unit tests for OrbController interaction state machine and kinematics."""

import pytest
from src.hand_tracker import HandData
from src.interaction import OrbController


def _mock_hand_data(
    pinch_x: float,
    pinch_y: float,
    is_pinching: bool,
    openness: float = 0.5,
) -> HandData:
    return HandData(
        landmarks_norm=[(0.5, 0.5, 0.0)] * 21,
        landmarks_px=[(pinch_x, pinch_y)] * 21,
        palm_center_px=(pinch_x, pinch_y),
        pinch_point_px=(pinch_x, pinch_y),
        is_pinching=is_pinching,
        pinch_distance_px=20.0 if is_pinching else 60.0,
        norm_pinch_distance=0.2 if is_pinching else 0.7,
        openness=openness,
        hand_scale_px=100.0,
        handedness="Right",
        confidence=0.9,
    )


def test_orb_initialization_and_centering():
    orb = OrbController(frame_width=640, frame_height=480)
    assert orb.x == 320.0
    assert orb.y == 240.0
    assert not orb.is_grabbed
    assert not orb.is_hovered


def test_orb_grab_and_release_callbacks():
    grabbed_events = []
    released_events = []

    def on_grab(x, y, r):
        grabbed_events.append((x, y, r))

    def on_release(x, y, r):
        released_events.append((x, y, r))

    orb = OrbController(
        frame_width=640,
        frame_height=480,
        on_grab=on_grab,
        on_release=on_release,
    )

    # Hand approaches orb center without pinching -> Hover
    hand_hover = _mock_hand_data(pinch_x=320.0, pinch_y=240.0, is_pinching=False)
    orb.update(hand_hover, dt=0.033)
    assert orb.is_hovered
    assert not orb.is_grabbed
    assert len(grabbed_events) == 0

    # Hand pinches while at orb center -> Grab!
    hand_grab = _mock_hand_data(pinch_x=320.0, pinch_y=240.0, is_pinching=True)
    orb.update(hand_grab, dt=0.033)
    assert orb.is_grabbed
    assert len(grabbed_events) == 1

    # Hand moves while pinching -> Orb moves
    hand_move = _mock_hand_data(pinch_x=400.0, pinch_y=300.0, is_pinching=True)
    for _ in range(5):
        orb.update(hand_move, dt=0.033)
    assert orb.is_grabbed
    assert orb.x > 350.0  # Following hand

    # Hand releases pinch -> Release!
    hand_release = _mock_hand_data(pinch_x=400.0, pinch_y=300.0, is_pinching=False)
    orb.update(hand_release, dt=0.033)
    assert not orb.is_grabbed
    assert len(released_events) == 1


def test_orb_radius_openness_scaling():
    orb = OrbController(
        frame_width=640,
        frame_height=480,
        min_radius=30.0,
        max_radius=120.0,
        default_radius=50.0,
    )

    # 1. Closed hand (openness = 0.0) -> radius shrinks towards min_radius
    hand_closed = _mock_hand_data(pinch_x=100.0, pinch_y=100.0, is_pinching=False, openness=0.0)
    for _ in range(25):
        orb.update(hand_closed, dt=0.033)
    assert orb.current_radius < 45.0

    # 2. Open hand (openness = 1.0) -> radius grows towards max_radius
    hand_open = _mock_hand_data(pinch_x=100.0, pinch_y=100.0, is_pinching=False, openness=1.0)
    for _ in range(35):
        orb.update(hand_open, dt=0.033)
    assert orb.current_radius > 90.0


def test_orb_viewport_confinement():
    orb = OrbController(frame_width=640, frame_height=480)

    # Try dragging way off-screen to (-500, -500)
    extreme_hand = _mock_hand_data(pinch_x=-500.0, pinch_y=-500.0, is_pinching=True)
    orb.is_grabbed = True
    for _ in range(20):
        orb.update(extreme_hand, dt=0.033)

    # Must stay within viewport margins
    margin = orb.current_radius * 1.1
    assert orb.x >= margin
    assert orb.y >= margin
    assert orb.x <= 640 - margin
    assert orb.y <= 480 - margin
