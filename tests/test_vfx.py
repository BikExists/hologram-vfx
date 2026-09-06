"""Unit tests for VFX subsystem, particle physics, color palettes, and orb rendering."""

import numpy as np
import pytest
from src.vfx.color_themes import THEME_KEYS, get_theme
from src.vfx.orb_renderer import OrbRenderer, Shockwave
from src.vfx.particles import ParticleSystem


def test_color_themes():
    for key in THEME_KEYS:
        theme = get_theme(key)
        assert theme.name
        for attr in ("core", "inner_glow", "outer_glow", "ring_primary", "particle", "tether", "shockwave"):
            val = getattr(theme, attr)
            assert isinstance(val, tuple)
            assert len(val) == 3
            assert all(0 <= c <= 255 for c in val)

    # Fallback for unknown theme
    fallback = get_theme("non_existent_key")
    assert fallback.name == "Cyber Cyan"


def test_particle_system():
    ps = ParticleSystem(num_orbit_particles=40)
    assert len(ps.orbit_particles) == 40
    assert len(ps.burst_particles) == 0

    # Trigger burst
    ps.spawn_burst(100.0, 100.0, count=15)
    assert len(ps.burst_particles) == 15

    # Update step
    ps.update(0.05)
    assert len(ps.burst_particles) == 15

    # Aging burst particles
    ps.update(1.0)
    assert len(ps.burst_particles) == 0  # Should expire

    # Render onto canvas
    canvas = np.zeros((200, 200, 3), dtype=np.uint8)
    ps.render(canvas, 100.0, 100.0, current_radius=40.0, color_bgr=(255, 200, 0))
    # Check that canvas received non-zero pixels
    assert np.any(canvas > 0)


def test_orb_renderer_bounds_and_rendering():
    renderer = OrbRenderer(theme_name="cyan")
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    # 1. Normal center render
    renderer.render(frame, center=(320.0, 240.0), radius=50.0, dt=0.033)
    assert np.any(frame > 0)

    # 2. Render near corner (clipping test: should not throw index errors)
    corner_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    renderer.render(corner_frame, center=(10.0, 10.0), radius=60.0, dt=0.033)
    assert np.any(corner_frame > 0)

    # 3. Render with negative coords (fully off-screen edge)
    off_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    renderer.render(off_frame, center=(-50.0, -50.0), radius=40.0, dt=0.033)

    # 4. Render with grab tether
    tether_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    renderer.render(
        tether_frame,
        center=(320.0, 240.0),
        radius=50.0,
        is_grabbed=True,
        pinch_pt=(250.0, 200.0),
        dt=0.033,
    )
    assert np.any(tether_frame > 0)


def test_shockwave_lifecycle():
    sw = Shockwave(cx=100, cy=100, start_radius=20, max_radius=80, duration=0.2)
    assert sw.update(0.1)  # Still alive
    assert not sw.update(0.15)  # Expired after 0.25s
