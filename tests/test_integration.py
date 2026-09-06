"""Integration tests for the full end-to-end Holographic VFX Application."""

import numpy as np
import pytest
from src.app import HolographicVFXApp


def test_app_headless_synthetic_pipeline():
    app = HolographicVFXApp(
        width=640,
        height=480,
        theme_name="cyan",
        synthetic_mode=True,
        headless=True,
    )

    try:
        # Step through 25 frames
        for frame_idx in range(25):
            ret, frame, telemetry = app.step_frame()
            assert ret is True
            assert frame is not None
            assert frame.shape == (480, 640, 3)
            assert frame.dtype == np.uint8

            # Check telemetry contract
            assert "fps" in telemetry
            assert "orb_x" in telemetry
            assert "orb_y" in telemetry
            assert "orb_radius" in telemetry
            assert "is_grabbed" in telemetry
            assert 0 <= telemetry["orb_x"] <= 640
            assert 0 <= telemetry["orb_y"] <= 480
            assert telemetry["orb_radius"] > 10.0

        # Test theme cycling
        initial_theme = app.renderer.theme.name
        new_theme_key = app.cycle_theme()
        assert app.renderer.theme.name != initial_theme

        # Test reset orb
        app.orb.x = 100.0
        app.orb.y = 100.0
        app.orb.reset_position()
        assert app.orb.x == 320.0
        assert app.orb.y == 240.0

    finally:
        app.close()


def test_app_clean_shutdown():
    app = HolographicVFXApp(
        synthetic_mode=True,
        headless=True,
    )
    # Immediate close without running
    app.close()
    assert not app.running
