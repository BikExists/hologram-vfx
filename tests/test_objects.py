"""Comprehensive unit and integration tests for Universal Holographic Object System."""

import numpy as np
import pytest

from src.hand_tracker import HandData
from src.objects import (
    BaseHolographicObject,
    HolographicCube,
    HolographicObjectManager,
    HolographicOrb,
    HolographicPlanet,
)
from src.vfx.color_themes import get_theme


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


@pytest.mark.parametrize("obj_class,expected_name", [
    (HolographicOrb, "Orb"),
    (HolographicCube, "Cube"),
    (HolographicPlanet, "Planet"),
])
def test_object_contract_compliance(obj_class, expected_name):
    """Verifies that all holographic objects strictly satisfy the BaseHolographicObject contract."""
    obj = obj_class(frame_width=640, frame_height=480, theme_name="cyan")
    assert isinstance(obj, BaseHolographicObject)
    assert obj.name == expected_name

    # Pixel coordinate properties
    assert isinstance(obj.x, float)
    assert isinstance(obj.y, float)
    assert isinstance(obj.current_radius, float)
    assert isinstance(obj.is_grabbed, bool)
    assert isinstance(obj.is_hovered, bool)
    assert obj.theme.name == "Cyber Cyan"

    # Default centering at (w*0.5, h*0.5)
    assert obj.x == 320.0
    assert obj.y == 240.0

    # Viewport resizing
    obj.resize_viewport(1280, 720)
    assert obj.w == 1280
    assert obj.h == 720

    # Reset position
    obj.x = 100.0
    obj.y = 100.0
    obj.reset_position()
    assert obj.x == 640.0
    assert obj.y == 360.0

    # Theme setting
    obj.set_theme("solar")
    assert obj.theme.name == "Solar Flare"


@pytest.mark.parametrize("obj_class", [HolographicOrb, HolographicCube, HolographicPlanet])
def test_object_interaction_and_openness(obj_class):
    """Verifies that pinch-to-grab, movement, and openness scaling work across all 3 objects."""
    obj = obj_class(frame_width=640, frame_height=480)

    # 1. Hover when hand is near center
    hand_hover = _mock_hand_data(pinch_x=320.0, pinch_y=240.0, is_pinching=False)
    obj.update(hand_hover, dt=0.033)
    assert obj.is_hovered
    assert not obj.is_grabbed

    # 2. Grab on pinch
    hand_grab = _mock_hand_data(pinch_x=320.0, pinch_y=240.0, is_pinching=True)
    obj.update(hand_grab, dt=0.033)
    assert obj.is_grabbed

    # 3. Movement follows hand
    hand_move = _mock_hand_data(pinch_x=420.0, pinch_y=280.0, is_pinching=True)
    for _ in range(5):
        obj.update(hand_move, dt=0.033)
    assert obj.x > 350.0

    # 4. Release grab
    hand_rel = _mock_hand_data(pinch_x=420.0, pinch_y=280.0, is_pinching=False)
    obj.update(hand_rel, dt=0.033)
    assert not obj.is_grabbed

    # 5. Openness scaling (fist shrinks, open expands)
    hand_closed = _mock_hand_data(pinch_x=100.0, pinch_y=100.0, is_pinching=False, openness=0.0)
    for _ in range(25):
        obj.update(hand_closed, dt=0.033)
    r_closed = obj.current_radius

    hand_open = _mock_hand_data(pinch_x=100.0, pinch_y=100.0, is_pinching=False, openness=1.0)
    for _ in range(50):
        obj.update(hand_open, dt=0.033)
    r_open = obj.current_radius

    assert r_open > r_closed


@pytest.mark.parametrize("obj_class", [HolographicOrb, HolographicCube, HolographicPlanet])
def test_object_rendering_robustness(obj_class):
    """Verifies rendering execution across normal, clipped, and tethered states."""
    obj = obj_class(frame_width=640, frame_height=480, theme_name="violet")
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    # Normal rendering
    obj.render(frame, pinch_pt=None, dt=0.033)
    assert np.any(frame > 0)

    # Edge clipping rendering (near border)
    obj.x = 10.0
    obj.y = 10.0
    frame.fill(0)
    obj.render(frame, pinch_pt=None, dt=0.033)
    assert np.any(frame > 0)

    # Tether rendering
    obj.is_grabbed = True
    frame.fill(0)
    obj.render(frame, pinch_pt=(150.0, 150.0), dt=0.033)
    assert np.any(frame > 0)


def test_object_manager_switching():
    """Verifies object manager initialization, 1-3 switching, and error handling."""
    mgr = HolographicObjectManager(frame_width=640, frame_height=480, theme_name="cyan")

    # Default is Orb (1)
    assert mgr.current_id == 1
    assert mgr.get_active_object().name == "Orb"

    # Switch to Cube (2)
    ok, msg = mgr.select_object(2)
    assert ok is True
    assert "Cube" in msg
    assert mgr.current_id == 2
    assert mgr.get_active_object().name == "Cube"

    # Switch to Planet (3)
    ok, msg = mgr.select_object(3)
    assert ok is True
    assert "Planet" in msg
    assert mgr.current_id == 3
    assert mgr.get_active_object().name == "Planet"

    # Switch back to Orb (1)
    ok, msg = mgr.select_object(1)
    assert ok is True
    assert "Orb" in msg
    assert mgr.current_id == 1
    assert mgr.get_active_object().name == "Orb"

    # Already active returns True
    ok, msg = mgr.select_object(1)
    assert ok is True
    assert "already active" in msg

    # Invalid ID returns False
    ok, msg = mgr.select_object(99)
    assert ok is False
    assert "Invalid object ID" in msg
    assert mgr.current_id == 1


def test_object_manager_state_transfer():
    """Verifies that spatial coordinates, scale, and theme are preserved seamlessly across switches."""
    mgr = HolographicObjectManager(frame_width=640, frame_height=480, theme_name="matrix")

    orb = mgr.get_active_object()
    orb.x = 425.0
    orb.y = 310.0
    orb.current_radius = 85.0

    # Switch to Cube -> Cube inherits position and scale
    mgr.select_object(2)
    cube = mgr.get_active_object()
    assert cube.name == "Cube"
    assert cube.x == 425.0
    assert cube.y == 310.0
    assert cube.current_radius == 85.0
    assert cube.theme.name == "Emerald Matrix"

    # Switch to Planet -> Planet inherits position and scale
    mgr.select_object(3)
    planet = mgr.get_active_object()
    assert planet.name == "Planet"
    assert planet.x == 425.0
    assert planet.y == 310.0
    assert planet.current_radius == 85.0
    assert planet.theme.name == "Emerald Matrix"


def test_object_manager_theme_and_viewport_propagation():
    """Verifies that set_theme and resize_viewport propagate to all managed objects."""
    mgr = HolographicObjectManager(frame_width=640, frame_height=480, theme_name="cyan")

    # Propagate theme
    mgr.set_theme("solar")
    for obj in mgr.objects.values():
        assert obj.theme.name == "Solar Flare"

    # Propagate viewport resizing
    mgr.resize_viewport(1280, 720)
    for obj in mgr.objects.values():
        assert obj.w == 1280
        assert obj.h == 720
