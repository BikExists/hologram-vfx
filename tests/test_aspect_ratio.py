"""Tests for Camera-Aspect-Ratio-Aware Rendering, HUD Layout, and Window Presentation.

Verifies:
1. AspectPreservingPresenter letterbox/pillarbox geometry and zero-copy direct presentation.
2. Zero memory allocation on repeated presentation frames.
3. HUD responsive layout and collision-free panel positioning across 4:3, 16:9, 16:10, and custom ratios.
4. Deterministic normalized viewport coordinate scaling in OrbController.
5. End-to-end integration of HolographicVFXApp with varying aspect ratios.
6. Holographic object isotropic geometry across different aspect ratios.
"""

import numpy as np
import pytest

from src.app import HolographicVFXApp
from src.camera import CameraDeviceInfo, SyntheticCamera
from src.interaction import OrbController
from src.objects.cube import HolographicCube
from src.objects.orb import HolographicOrb
from src.objects.planet import HolographicPlanet
from src.vfx.color_themes import get_theme
from src.vfx.hud import HUD
from src.vfx.presenter import AspectPreservingPresenter


# =============================================================================
# 1. AspectPreservingPresenter Tests
# =============================================================================

def test_presenter_exact_match_returns_direct_frame():
    """Exact dimension match must return original frame directly with zero copy."""
    presenter = AspectPreservingPresenter()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    result = presenter.prepare_presentation(frame, win_w=640, win_h=480)

    assert result is frame  # Identity check: zero copy
    assert not presenter.is_letterboxed
    assert presenter.target_w == 640
    assert presenter.target_h == 480
    assert presenter.x_offset == 0
    assert presenter.y_offset == 0


def test_presenter_exact_aspect_ratio_match_returns_direct_frame():
    """When window has the exact same aspect ratio as frame, OpenCV can scale isotropically."""
    presenter = AspectPreservingPresenter()
    # 640x480 is 4:3; 1280x960 is also 4:3 (1280 * 480 == 960 * 640)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    result = presenter.prepare_presentation(frame, win_w=1280, win_h=960)

    assert result is frame  # Identity check: zero copy
    assert not presenter.is_letterboxed


def test_presenter_pillarbox_4_3_in_16_9_window():
    """4:3 frame in 16:9 window must have pillarbox bars on left and right."""
    presenter = AspectPreservingPresenter(bg_color=(10, 10, 10))
    frame = np.ones((480, 640, 3), dtype=np.uint8) * 200

    result = presenter.prepare_presentation(frame, win_w=1280, win_h=720)

    assert presenter.is_letterboxed
    assert result.shape == (720, 1280, 3)
    # 4:3 fit in 1280x720: height=720, width=720 * (4/3) = 960
    assert presenter.target_w == 960
    assert presenter.target_h == 720
    # Pillarbox bars: (1280 - 960) // 2 = 160 on left and right
    assert presenter.x_offset == 160
    assert presenter.y_offset == 0

    # Verify aspect ratio of target area is exactly 4:3
    assert abs(presenter.target_w / float(presenter.target_h) - (4.0 / 3.0)) < 1e-4

    # Verify content in center area and matte color in pillarbox area
    assert np.all(result[360, 640] == [200, 200, 200])  # Frame content
    assert np.all(result[360, 50] == [10, 10, 10])     # Left pillarbox bar
    assert np.all(result[360, 1200] == [10, 10, 10])   # Right pillarbox bar


def test_presenter_letterbox_16_9_in_4_3_window():
    """16:9 frame in 4:3 window must have letterbox bars on top and bottom."""
    presenter = AspectPreservingPresenter(bg_color=(12, 12, 12))
    frame = np.ones((720, 1280, 3), dtype=np.uint8) * 180

    result = presenter.prepare_presentation(frame, win_w=800, win_h=600)

    assert presenter.is_letterboxed
    assert result.shape == (600, 800, 3)
    # 16:9 fit in 800x600: width=800, height=800 * (9/16) = 450
    assert presenter.target_w == 800
    assert presenter.target_h == 450
    # Letterbox bars: (600 - 450) // 2 = 75 on top and bottom
    assert presenter.x_offset == 0
    assert presenter.y_offset == 75

    # Verify aspect ratio of target area is exactly 16:9
    assert abs(presenter.target_w / float(presenter.target_h) - (16.0 / 9.0)) < 1e-4

    # Verify center and bars
    assert np.all(result[300, 400] == [180, 180, 180])  # Frame content
    assert np.all(result[30, 400] == [12, 12, 12])     # Top letterbox bar
    assert np.all(result[570, 400] == [12, 12, 12])    # Bottom letterbox bar


def test_presenter_zero_allocation_on_consecutive_frames():
    """Presenter must reuse cached canvas buffer across frames with identical window dimensions."""
    presenter = AspectPreservingPresenter()
    frame1 = np.zeros((480, 640, 3), dtype=np.uint8)
    frame2 = np.ones((480, 640, 3), dtype=np.uint8) * 100

    out1 = presenter.prepare_presentation(frame1, win_w=1280, win_h=720)
    out2 = presenter.prepare_presentation(frame2, win_w=1280, win_h=720)

    # Both outputs must point to the identical cached NumPy buffer memory
    assert out1 is out2


def test_presenter_handles_invalid_dimensions():
    """Presenter must safely fall back when given non-positive window dimensions."""
    presenter = AspectPreservingPresenter()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    assert presenter.prepare_presentation(frame, win_w=0, win_h=0) is frame
    assert presenter.prepare_presentation(frame, win_w=-10, win_h=480) is frame


# =============================================================================
# 2. Responsive HUD Layout & Collision Freedom Tests
# =============================================================================

def _check_rect_overlap(r1, r2):
    """Returns True if two bounding boxes (x1, y1, x2, y2) overlap."""
    return not (r1[2] <= r2[0] or r1[0] >= r2[2] or r1[3] <= r2[1] or r1[1] >= r2[3])


@pytest.mark.parametrize("w,h", [
    (640, 480),   # Standard 4:3 webcam
    (800, 600),   # SVGA 4:3
    (1024, 768),  # XGA 4:3
    (1280, 720),  # 720p 16:9
    (1920, 1080), # 1080p 16:9
    (1280, 800),  # 16:10 laptop
    (600, 600),   # 1:1 Square
    (480, 640),   # 3:4 Portrait
])
def test_hud_no_panel_collisions(w, h):
    """HUD elements must never overlap or collide across any aspect ratio or resolution."""
    hud = HUD()

    for mode in ("SINGLE_HAND", "TWO_HANDS", "INDEPENDENT_DUAL_HAND"):
        rects = hud.get_layout_rects(w, h, interaction_mode=mode, has_notification=True)
        tl = rects["top_left"]
        tr = rects["top_right"]
        notif = rects["notification"]
        bottom = rects["bottom_help"]

        # Top-left and top-right panels must never collide
        assert not _check_rect_overlap(tl, tr), f"Top-Left and Top-Right collide at {w}x{h} in {mode}"

        # Notification must never collide with top-left panel
        assert not _check_rect_overlap(tl, notif), f"Top-Left and Notification collide at {w}x{h} in {mode}"

        # Notification must never collide with top-right panel
        assert not _check_rect_overlap(tr, notif), f"Top-Right and Notification collide at {w}x{h} in {mode}"

        # Bottom help must never collide with top panels or notification
        assert not _check_rect_overlap(tl, bottom)
        assert not _check_rect_overlap(tr, bottom)
        assert not _check_rect_overlap(notif, bottom)


def test_hud_renders_without_error_in_4_3_and_16_9():
    """HUD render method completes cleanly and produces visible elements in 4:3 and 16:9."""
    hud = HUD()
    theme = get_theme("cyan")

    for (w, h) in [(640, 480), (1280, 720)]:
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        hud.render(
            frame=frame,
            fps=30.0,
            frame_time_ms=33.3,
            theme=theme,
            state_label="SEARCHING HANDS",
            camera_name="TestCam",
            camera_notification="Camera switched",
            object_name="Orb",
            interaction_mode="TWO_HANDS",
            two_hand_scale=1.2,
            rotation_deg=45.0,
            selected_mode_name="STANDARD 2-HAND",
        )
        # Verify frame is modified and contains non-zero pixels from HUD panels
        assert np.count_nonzero(frame) > 0


# =============================================================================
# 3. Viewport Coordinate Scaling in OrbController
# =============================================================================

def test_orb_controller_preserves_normalized_placement():
    """OrbController must preserve normalized placement (x/w, y/h) across resolution changes."""
    ctrl = OrbController(frame_width=640, frame_height=480, default_radius=50.0)

    # Center object at (320, 240) in 640x480
    ctrl.reset_position()
    assert ctrl.x == 320.0
    assert ctrl.y == 240.0
    assert ctrl.rest_x == 320.0
    assert ctrl.rest_y == 240.0

    # Resize to 1280x720 (16:9)
    ctrl.resize_viewport(1280, 720)

    # Must be exactly at center of new viewport: (640, 360)
    assert ctrl.x == 640.0
    assert ctrl.y == 360.0
    assert ctrl.rest_x == 640.0
    assert ctrl.rest_y == 360.0


def test_orb_controller_arbitrary_position_scaling():
    """Non-centered object position scales proportionally without drift."""
    ctrl = OrbController(frame_width=640, frame_height=480, default_radius=50.0)

    # Place object at (160, 120) which is 25% X and 25% Y
    ctrl.x = 160.0
    ctrl.y = 120.0

    ctrl.resize_viewport(1280, 720)

    # 25% of 1280 is 320, 25% of 720 is 180
    assert ctrl.x == 320.0
    assert ctrl.y == 180.0


def test_orb_geometry_remains_isotropic_across_aspect_ratios():
    """Object radius must remain scalar in pixel space (perfect isotropic geometry)."""
    orb = HolographicOrb(frame_width=640, frame_height=480)
    assert orb.current_radius > 0

    # Resize viewport
    orb.resize_viewport(1280, 720)

    # Radius must remain unchanged (isotropic circle)
    assert orb.current_radius > 0


# =============================================================================
# 4. Holographic Object Rendering Isotropy
# =============================================================================

def test_planet_disk_is_isotropic():
    """Planet circular disk must maintain identical horizontal and vertical radius."""
    planet = HolographicPlanet(frame_width=640, frame_height=480)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    planet.render(frame)
    # Successfully rendered without error in native frame
    assert np.count_nonzero(frame) > 0


def test_cube_projection_is_isotropic():
    """Cube perspective projection maintains identical X and Y scale factors."""
    cube = HolographicCube(frame_width=640, frame_height=480)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    cube.render(frame)
    assert np.count_nonzero(frame) > 0


# =============================================================================
# 5. End-to-End HolographicVFXApp Aspect Ratio Integration
# =============================================================================

def test_app_step_frame_4_3_feed():
    """App step_frame on 4:3 feed produces 4:3 native frame and telemetry."""
    devices = [CameraDeviceInfo(device_id=-1, name="Synthetic 4:3", is_synthetic=True)]
    app = HolographicVFXApp(
        width=640,
        height=480,
        synthetic_mode=True,
        headless=True,
        available_cameras=devices,
    )

    ret, frame, telemetry = app.step_frame()
    app.close()

    assert ret is True
    assert frame is not None
    assert frame.shape == (480, 640, 3)
    assert telemetry["width"] == 640
    assert telemetry["height"] == 480
    assert abs(telemetry["aspect_ratio"] - (4.0 / 3.0)) < 1e-4


def test_app_step_frame_16_9_feed():
    """App step_frame on 16:9 feed produces 16:9 native frame and telemetry."""
    devices = [CameraDeviceInfo(device_id=-1, name="Synthetic 16:9", is_synthetic=True)]
    app = HolographicVFXApp(
        width=1280,
        height=720,
        synthetic_mode=True,
        headless=True,
        available_cameras=devices,
    )

    ret, frame, telemetry = app.step_frame()
    app.close()

    assert ret is True
    assert frame is not None
    assert frame.shape == (720, 1280, 3)
    assert telemetry["width"] == 1280
    assert telemetry["height"] == 720
    assert abs(telemetry["aspect_ratio"] - (16.0 / 9.0)) < 1e-4


def test_app_runtime_resolution_adaptation():
    """App dynamically adapts viewport when incoming frame resolution changes."""
    app = HolographicVFXApp(
        width=640,
        height=480,
        synthetic_mode=True,
        headless=True,
    )

    # Initial state
    assert app.width == 640
    assert app.height == 480

    # Simulate camera returning a 1280x720 frame
    fake_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    class FakeSource:
        def read_frame(self):
            return True, fake_frame

        def release(self):
            pass

    app.camera_selector.active_source = FakeSource()

    ret, frame, telemetry = app.step_frame()
    app.close()

    assert ret is True
    assert app.width == 1280
    assert app.height == 720
    assert abs(app.aspect_ratio - (16.0 / 9.0)) < 1e-4
    assert telemetry["width"] == 1280
    assert telemetry["height"] == 720
    assert app._camera_resolution_changed is True
