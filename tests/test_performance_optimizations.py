"""Tests for Performance Optimizations: Tracking downscaling, Local ROI compositing, and visual preservation."""

import math
import numpy as np
import pytest
import cv2

from src.app import HolographicVFXApp
from src.hand_tracker import HandTracker, HandData
from src.objects.cube import HolographicCube
from src.objects.planet import HolographicPlanet
from src.vfx.orb_renderer import OrbRenderer, Shockwave


def test_tracking_resolution_selection_and_aspect_ratio():
    """Verify that frames > max_tracking_dim are downscaled preserving aspect ratio, and smaller frames are untouched."""
    tracker = HandTracker(max_tracking_dim=640)

    # 1. High-resolution 1280x720 (16:9)
    frame_720p = np.zeros((720, 1280, 3), dtype=np.uint8)
    captured_shapes = []

    orig_process = tracker.hands.process
    def mock_process(image):
        captured_shapes.append(image.shape)
        return orig_process(image)

    tracker.hands.process = mock_process

    tracker.process_frame_multi(frame_720p)
    assert len(captured_shapes) == 1
    h_proc, w_proc = captured_shapes[0][:2]
    assert w_proc == 640
    assert h_proc == 360
    assert math.isclose(w_proc / h_proc, 1280 / 720, abs_tol=1e-3)

    # 2. 1920x1080 (16:9)
    captured_shapes.clear()
    frame_1080p = np.zeros((1080, 1920, 3), dtype=np.uint8)
    tracker.process_frame_multi(frame_1080p)
    assert len(captured_shapes) == 1
    h_proc, w_proc = captured_shapes[0][:2]
    assert w_proc == 640
    assert h_proc == 360

    # 3. 640x480 (4:3) - already <= max_tracking_dim, should NOT be resized
    captured_shapes.clear()
    frame_vga = np.zeros((480, 640, 3), dtype=np.uint8)
    tracker.process_frame_multi(frame_vga)
    assert len(captured_shapes) == 1
    h_proc, w_proc = captured_shapes[0][:2]
    assert w_proc == 640
    assert h_proc == 480

    # 4. Portrait mode / tall frames 720x1280
    captured_shapes.clear()
    frame_portrait = np.zeros((1280, 720, 3), dtype=np.uint8)
    tracker.process_frame_multi(frame_portrait)
    assert len(captured_shapes) == 1
    h_proc, w_proc = captured_shapes[0][:2]
    assert h_proc == 640
    assert w_proc == 360


def test_landmark_coordinate_mapping_accuracy(monkeypatch):
    """Verify that normalized landmarks are accurately projected to native full-resolution coordinates."""
    tracker = HandTracker(max_tracking_dim=640)

    class MockLandmark:
        def __init__(self, x, y, z=0.0):
            self.x = x
            self.y = y
            self.z = z

    class MockHandLms:
        landmark = [
            MockLandmark(0.25, 0.50, 0.0),  # 0: Wrist
            MockLandmark(0.30, 0.45), MockLandmark(0.35, 0.40), MockLandmark(0.40, 0.35),
            MockLandmark(0.45, 0.30),  # 4: Thumb tip
            MockLandmark(0.30, 0.30), MockLandmark(0.32, 0.25), MockLandmark(0.34, 0.20),
            MockLandmark(0.36, 0.15),  # 8: Index tip
            MockLandmark(0.28, 0.28), MockLandmark(0.29, 0.22), MockLandmark(0.30, 0.16),
            MockLandmark(0.31, 0.12),  # 12: Middle tip
            MockLandmark(0.26, 0.27), MockLandmark(0.27, 0.21), MockLandmark(0.28, 0.15),
            MockLandmark(0.29, 0.11),  # 16: Ring tip
            MockLandmark(0.24, 0.26), MockLandmark(0.24, 0.20), MockLandmark(0.24, 0.14),
            MockLandmark(0.24, 0.10),  # 20: Pinky tip
        ]

    class MockClassification:
        label = "Right"
        score = 0.95

    class MockClassificationEntry:
        classification = [MockClassification()]

    class MockResults:
        multi_hand_landmarks = [MockHandLms()]
        multi_handedness = [MockClassificationEntry()]

    monkeypatch.setattr(tracker.hands, "process", lambda rgb: MockResults())

    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    hands = tracker.process_frame_multi(frame)

    assert len(hands) == 1
    h = hands[0]

    assert math.isclose(h.landmarks_px[0][0], 320.0, abs_tol=1e-3)
    assert math.isclose(h.landmarks_px[0][1], 360.0, abs_tol=1e-3)
    assert math.isclose(h.landmarks_px[4][0], 576.0, abs_tol=1e-3)
    assert math.isclose(h.landmarks_px[4][1], 216.0, abs_tol=1e-3)

    assert 0 <= h.palm_center_px[0] <= 1280
    assert 0 <= h.palm_center_px[1] <= 720
    assert 0 <= h.pinch_point_px[0] <= 1280
    assert 0 <= h.pinch_point_px[1] <= 720


def test_native_resolution_rendering_preservation():
    """Verify that downstream application rendering maintains 100% of native camera resolution."""
    app = HolographicVFXApp(synthetic_mode=True, width=1280, height=720, headless=True)
    ret, rendered, telemetry = app.step_frame()

    assert ret
    assert rendered is not None
    assert rendered.shape == (720, 1280, 3)
    assert app.width == 1280
    assert app.height == 720


def test_planet_local_roi_rendering_and_boundary_clipping():
    """Verify that Planet renders without errors when centered or partially off-screen."""
    planet = HolographicPlanet(frame_width=640, frame_height=480, theme_name="cyan")

    # 1. Normal centered rendering
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    planet.x = 320.0
    planet.y = 240.0
    planet.render(frame, dt=0.033)
    assert np.any(frame > 0), "Planet should draw onto frame"

    # 2. Viewport boundary tests: Top-Left boundary
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    planet.x = 0.0
    planet.y = 0.0
    planet.render(frame, dt=0.033)
    assert np.any(frame > 0)

    # 3. Bottom-Right boundary
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    planet.x = 640.0
    planet.y = 480.0
    planet.render(frame, dt=0.033)
    assert np.any(frame > 0)

    # 4. Far off-screen
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    planet.x = -200.0
    planet.y = -200.0
    planet.render(frame, dt=0.033)


def test_cube_local_roi_rendering_and_boundary_clipping():
    """Verify that Cube renders depth-sorted faces and edges across frame boundaries."""
    cube = HolographicCube(frame_width=640, frame_height=480, theme_name="emerald")

    # 1. Centered
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cube.x = 320.0
    cube.y = 240.0
    cube.render(frame, dt=0.033)
    assert np.any(frame > 0)

    # 2. Partially off-screen Left
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cube.x = 10.0
    cube.y = 240.0
    cube.render(frame, dt=0.033)
    assert np.any(frame > 0)

    # 3. Partially off-screen Bottom
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cube.x = 320.0
    cube.y = 475.0
    cube.render(frame, dt=0.033)
    assert np.any(frame > 0)

    # 4. Completely outside viewport
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cube.x = 1000.0
    cube.y = 1000.0
    cube.render(frame, dt=0.033)


def test_shockwave_local_roi_and_boundary_clipping():
    """Verify that Shockwave correctly bounds local ROI and clips at viewport edges."""
    sw = Shockwave(cx=320.0, cy=240.0, start_radius=20.0, max_radius=100.0, duration=0.5)

    # Center
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    sw.update(0.1)
    sw.render(frame, (0, 255, 255))
    assert np.any(frame > 0)

    # At corner boundary
    sw_corner = Shockwave(cx=5.0, cy=5.0, start_radius=20.0, max_radius=100.0, duration=0.5)
    sw_corner.update(0.2)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    sw_corner.render(frame, (0, 255, 255))
    assert np.any(frame > 0)


def test_orb_radial_glow_saturation_and_visual_parity():
    """Verify that vectorized radial glow compositing produces saturated highlights."""
    renderer = OrbRenderer(theme_name="cyan")
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    renderer.render(frame, center=(320.0, 240.0), radius=60.0, dt=0.033)

    # Center core must be high intensity
    core_pixel = frame[240, 320]
    assert np.mean(core_pixel) > 200, "Orb center should have intense white/cyan core"

    # Radial falloff: pixels outside the glow box should have lower intensity than center
    outer_pixel = frame[240, 320 + 150]
    assert np.mean(outer_pixel) < np.mean(core_pixel), "Radial glow must fall off with distance"
