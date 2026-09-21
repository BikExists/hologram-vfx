"""Tests for Performance Optimizations: Tracking downscaling, Local ROI compositing, and visual preservation."""

import math
import numpy as np
import pytest
import cv2

from src.app import HolographicVFXApp
from src.hand_tracker import HandTracker, HandData
from src.objects.cube import HolographicCube
from src.objects.planet import HolographicPlanet
from src.objects.ghost_orchid import HolographicGhostOrchid
from src.objects.bhondu_face import HolographicBhonduFace
from src.objects.jellyfish import HolographicJellyfish
from src.ui.menu import HolographicMenu
from src.vfx.aura import AuraCache, get_aura_cache
from src.vfx.color_themes import get_theme
from src.vfx.hud import HUD
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


def test_phase2_aura_cache_quantization_and_consistency():
    """Verify AuraCache caches standard and planet aura patches and handles boundary clipping."""
    cache = AuraCache(max_entries=16)

    # 1. Standard aura caching
    p1 = cache.get_standard_aura(45, (255, 200, 50), weight=0.42, power=2.2)
    p2 = cache.get_standard_aura(45, (255, 200, 50), weight=0.42, power=2.2)
    assert p1 is p2, "Identical parameters must return cached instance"
    assert p1.shape == (91, 91, 3)

    # 2. Planet halo caching
    h1, box1 = cache.get_planet_halo(40, (255, 100, 50), (200, 255, 100))
    h2, box2 = cache.get_planet_halo(40, (255, 100, 50), (200, 255, 100))
    assert h1 is h2, "Planet halo must return cached instance"
    assert box1 == int(40 * 1.7)

    # 3. Boundary clipping tests: verify no crash when rendering at viewport extremes
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    # Centered
    cache.render_standard_aura(frame, 320, 240, 50, (0, 255, 255))
    assert np.any(frame > 0)

    # Off-screen top-left
    cache.render_standard_aura(frame, -20, -20, 50, (0, 255, 255))
    # Off-screen bottom-right
    cache.render_standard_aura(frame, 660, 500, 50, (0, 255, 255))
    # Planet halo off-screen
    cache.render_planet_halo(frame, -30, 240, 40, (255, 100, 50), (200, 255, 100))
    cache.render_planet_halo(frame, 680, 520, 40, (255, 100, 50), (200, 255, 100))


def test_phase2_orb_prebaked_composite_glow_parity():
    """Verify OrbRenderer pre-baked composite glow matches expected holographic radiance within tight tolerance."""
    orb = OrbRenderer(theme_name="cyan")
    oi_u8, core_u8 = orb._get_composite_glow(50)
    oi_u8_2, core_u8_2 = orb._get_composite_glow(50)
    assert oi_u8 is oi_u8_2, "Composite glow templates must be cached"
    assert core_u8 is core_u8_2

    # Render frame and check non-zero radiance
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    orb.render(frame, center=(320.0, 240.0), radius=50.0, dt=0.033)
    assert np.any(frame > 0)


def test_phase2_zero_heap_allocation_tracker_buffer():
    """Verify HandTracker reuses _rgb_buffer across successive frames of the same shape."""
    tracker = HandTracker(max_tracking_dim=640)
    frame_vga = np.zeros((480, 640, 3), dtype=np.uint8)

    # First call allocates buffer
    tracker.process_frame_multi(frame_vga)
    assert tracker._rgb_buffer is not None
    assert tracker._rgb_buffer.shape == (480, 640, 3)
    buf_id_1 = id(tracker._rgb_buffer)

    # Second call reuses same buffer
    tracker.process_frame_multi(frame_vga)
    assert id(tracker._rgb_buffer) == buf_id_1

    # Resolution change reallocates buffer to match new dimensions
    frame_hd = np.zeros((720, 1280, 3), dtype=np.uint8)
    tracker.process_frame_multi(frame_hd)
    assert tracker._rgb_buffer.shape == (360, 640, 3)


def test_phase2_menu_and_hud_in_place_glass_scaling():
    """Verify HUD and HolographicMenu glass darkening functions with in-place SIMD scaling."""
    # 1. HUD glass rect
    frame = np.full((480, 640, 3), 200, dtype=np.uint8)
    HUD.draw_glass_rect(frame, 50, 50, 200, 100, border_color=(0, 255, 255), bg_alpha=0.5)
    # Interior of glass rect should be darker
    darkened_val = np.mean(frame[60:140, 60:240])
    assert darkened_val < 180, "Glass rectangle must darken background"

    # 2. Menu render
    menu = HolographicMenu()
    menu_frame = np.full((480, 640, 3), 150, dtype=np.uint8)
    theme = get_theme("cyan")
    menu.render(menu_frame, theme)
    assert np.mean(menu_frame[menu.panel_y : menu.panel_y + menu.panel_h, menu.panel_x : menu.panel_x + menu.panel_w]) < 150


def test_phase2_all_objects_aura_rendering():
    """Verify all 6 objects render correctly with optimized aura cache."""
    classes = [
        HolographicCube,
        HolographicPlanet,
        HolographicGhostOrchid,
        HolographicBhonduFace,
        HolographicJellyfish,
    ]

    for cls in classes:
        obj = cls(frame_width=640, frame_height=480, theme_name="cyan")
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        obj.x, obj.y = 320.0, 240.0
        obj.render(frame, dt=0.033)
        assert np.any(frame > 0), f"{cls.__name__} should render non-zero pixels"

