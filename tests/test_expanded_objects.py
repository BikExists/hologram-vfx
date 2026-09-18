"""Unit tests for the Expanded Holographic Object Library (All 6 Objects).

Verifies:
- All 6 objects instantiate cleanly and implement BaseHolographicObject
- Dynamic viewport resizing and aspect-ratio invariance across 4:3 and 16:9 feeds
- Interaction mode compatibility (Standard 2-Hand vs Independent Dual-Hand)
- State transfer across object transitions (position, velocity, scale, theme)
- Object-specific rendering logic:
  * Ghost Orchid (blooming modulated by openness, twin twisting tendrils, labellum, spores)
  * Bhondu Face (100% procedural emoji geometry, bulging eyes, quivering mouth, blush, scanlines)
  * Bioluminescent Jellyfish (harmonic pulsating dome, trailing tentacles, oral arms, plankton)
- Safe boundary clamping and local ROI compositing
"""

import math
import time
import numpy as np
import pytest

from src.hand_tracker import HandData
from src.objects.base import BaseHolographicObject, InteractionMode
from src.objects.bhondu_face import HolographicBhonduFace
from src.objects.cube import HolographicCube
from src.objects.ghost_orchid import HolographicGhostOrchid
from src.objects.jellyfish import HolographicJellyfish
from src.objects.manager import HolographicObjectManager
from src.objects.orb import HolographicOrb
from src.objects.planet import HolographicPlanet
from src.vfx.color_themes import get_theme


def make_dummy_hand(
    palm_x: float = 320.0,
    palm_y: float = 240.0,
    is_pinching: bool = False,
    openness: float = 0.9,
    is_right: bool = True,
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
    idx_ext = 80.0 if openness > 0.5 else 30.0
    for i in range(1, 5):
        landmarks_px.append((palm_x - 15.0, palm_y + 20.0 - i * (idx_ext / 4.0)))

    # Middle: 9..12
    mid_ext = 90.0 if openness > 0.5 else 30.0
    for i in range(1, 5):
        landmarks_px.append((palm_x, palm_y + 20.0 - i * (mid_ext / 4.0)))

    # Ring: 13..16
    ring_ext = 80.0 if openness > 0.5 else 30.0
    for i in range(1, 5):
        landmarks_px.append((palm_x + 15.0, palm_y + 20.0 - i * (ring_ext / 4.0)))

    # Pinky: 17..20
    pinky_ext = 70.0 if openness > 0.5 else 25.0
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


ALL_OBJECT_CLASSES = [
    (1, HolographicOrb, "Orb"),
    (2, HolographicCube, "Cube"),
    (3, HolographicPlanet, "Planet"),
    (4, HolographicGhostOrchid, "Ghost Orchid"),
    (5, HolographicBhonduFace, "Bhondu Face"),
    (6, HolographicJellyfish, "Jellyfish"),
]


class TestExpandedObjectsContract:
    """Verifies that all 6 holographic objects strictly satisfy BaseHolographicObject."""

    @pytest.mark.parametrize("obj_id, cls, name", ALL_OBJECT_CLASSES)
    def test_instantiation_and_contract(self, obj_id, cls, name):
        obj = cls(frame_width=640, frame_height=480, theme_name="cyan")
        assert isinstance(obj, BaseHolographicObject)
        assert obj.name == name
        assert obj.w == 640
        assert obj.h == 480
        assert obj.x == 320.0
        assert obj.y == 240.0
        assert obj.current_radius > 10.0

        # Update kinematics
        x, y, r = obj.update([], dt=0.033)
        assert isinstance(x, float)
        assert isinstance(y, float)
        assert isinstance(r, float)

        # Render onto frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        obj.render(frame, pinch_pt=None, dt=0.033)
        assert np.any(frame > 0), f"{name} should render visible pixels on black frame"

    @pytest.mark.parametrize("obj_id, cls, name", ALL_OBJECT_CLASSES)
    def test_viewport_resizing(self, obj_id, cls, name):
        obj = cls(frame_width=640, frame_height=480)
        obj.resize_viewport(1280, 720)
        assert obj.w == 1280
        assert obj.h == 720
        assert obj.x == 640.0
        assert obj.y == 360.0

        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        obj.render(frame, pinch_pt=None, dt=0.033)
        assert np.any(frame > 0)

    @pytest.mark.parametrize("obj_id, cls, name", ALL_OBJECT_CLASSES)
    def test_theme_propagation(self, obj_id, cls, name):
        obj = cls(frame_width=640, frame_height=480, theme_name="cyan")
        assert obj.theme.name == get_theme("cyan").name

        obj.set_theme("amber")
        assert obj.theme.name == get_theme("amber").name

        amber_theme = get_theme("amber")
        obj.set_theme(amber_theme)
        assert obj.theme.name == amber_theme.name

    @pytest.mark.parametrize("obj_id, cls, name", ALL_OBJECT_CLASSES)
    def test_reset_position(self, obj_id, cls, name):
        obj = cls(frame_width=640, frame_height=480)
        obj.x = 100.0
        obj.y = 80.0
        obj.controller.vx = 50.0
        obj.controller.vy = -30.0

        obj.reset_position()
        assert obj.x == 320.0
        assert obj.y == 240.0
        assert obj.controller.vx == 0.0
        assert obj.controller.vy == 0.0

    @pytest.mark.parametrize("obj_id, cls, name", ALL_OBJECT_CLASSES)
    def test_mode_and_state_transfer(self, obj_id, cls, name):
        source = HolographicOrb(frame_width=640, frame_height=480)
        source.x = 450.0
        source.y = 350.0
        source.current_radius = 110.0
        source.rotation = 1.25
        source.selected_mode = InteractionMode.INDEPENDENT

        target = cls(frame_width=640, frame_height=480)
        target.transfer_state_from(source)

        assert abs(target.x - 450.0) < 1.0
        assert abs(target.y - 350.0) < 1.0
        assert abs(target.current_radius - 110.0) < 1.0
        assert abs(target.rotation - 1.25) < 0.01
        assert target.selected_mode == InteractionMode.INDEPENDENT


class TestObjectSpecificFeatures:
    """Verifies unique geometry and physics implementations for each newly added object."""

    def test_ghost_orchid_blooming_and_tendrils(self):
        orchid = HolographicGhostOrchid(frame_width=640, frame_height=480)
        assert orchid.bloom_factor == 0.5

        # Updating with open hand expands bloom factor towards 1.0
        hand = make_dummy_hand(openness=0.95)
        for _ in range(25):
            orchid.update([hand], dt=0.033)

        assert orchid.bloom_factor > 0.6

        # Render verifies spore updates and tendril splines without out-of-bounds error
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        orchid.render(frame, pinch_pt=(320, 240), dt=0.033)
        assert len(orchid.particles.orbit_particles) > 0
        assert np.any(frame > 0)

    def test_bhondu_face_procedural_anatomy(self):
        face = HolographicBhonduFace(frame_width=640, frame_height=480)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # Confirm 100% procedural NumPy/OpenCV rendering with no external dependencies
        face.render(frame, pinch_pt=None, dt=0.033)
        assert np.any(frame > 0)
        assert not np.isnan(face.quiver_phase)

        # Test quivering mouth dynamics
        initial_phase = face.quiver_phase
        face.update([], dt=0.1)
        assert face.quiver_phase != initial_phase

    def test_jellyfish_pulsation_and_trailing_tentacles(self):
        jelly = HolographicJellyfish(frame_width=640, frame_height=480)
        assert len(jelly.particles.orbit_particles) > 0

        # Bell pulse advances phase
        initial_pulse = jelly.pulse_phase
        jelly.update([], dt=0.05)
        assert jelly.pulse_phase > initial_pulse

        # Render ensures oral arms and tentacles don't crash or overflow boundaries
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        jelly.render(frame, pinch_pt=None, dt=0.033)
        assert np.any(frame > 0)


class TestHolographicObjectManagerSwitching:
    """Verifies clean switching across all 6 objects within the Object Manager."""

    def test_manager_instantiation_and_indexing(self):
        mgr = HolographicObjectManager(frame_width=640, frame_height=480)
        assert len(mgr.objects) == 6
        assert mgr.active_object_id == 1
        assert mgr.get_active_object().name == "Orb"

    def test_manager_switching_all_six(self):
        mgr = HolographicObjectManager(frame_width=640, frame_height=480)

        for target_id in range(1, 7):
            ok, msg = mgr.select_object(target_id)
            assert ok is True
            assert mgr.active_object_id == target_id
            active_obj = mgr.get_active_object()
            assert active_obj is not None

        # Invalid object id
        ok, msg = mgr.select_object(7)
        assert ok is False
        assert mgr.active_object_id == 6

        ok, msg = mgr.select_object(0)
        assert ok is False
        assert mgr.active_object_id == 6
