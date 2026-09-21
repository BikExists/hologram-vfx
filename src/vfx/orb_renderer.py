"""Holographic Orb Renderer and VFX Compositor.

Renders multi-layer radial exponential glow, 3D rotating gyroscopic rings,
electric plasma pinch tethers, shockwaves, and subtle scanline interference.
"""

import math
import random
import time
from typing import Dict, List, Optional, Tuple, Union
import cv2
import numpy as np

from src.vfx.color_themes import ColorTheme, get_theme
from src.vfx.particles import ParticleSystem


class Shockwave:
    """Expanding circular ripple effect."""

    def __init__(self, cx: float, cy: float, start_radius: float, max_radius: float, duration: float = 0.45):
        self.cx = cx
        self.cy = cy
        self.start_radius = start_radius
        self.max_radius = max_radius
        self.duration = duration
        self.age = 0.0

    def update(self, dt: float) -> bool:
        """Returns True if shockwave is still active."""
        self.age += dt
        return self.age < self.duration

    def render(self, frame: np.ndarray, color_bgr: Tuple[int, int, int]) -> None:
        progress = self.age / self.duration
        alpha = max(0.0, 1.0 - progress)
        current_r = int(self.start_radius + (self.max_radius - self.start_radius) * (progress ** 0.7))
        thickness = max(1, int(3 * alpha))

        h, w = frame.shape[:2]
        cx, cy = int(self.cx), int(self.cy)

        # Local ROI bounded around expanding shockwave
        pad = current_r + thickness + 3
        x1 = max(0, cx - pad)
        y1 = max(0, cy - pad)
        x2 = min(w, cx + pad + 1)
        y2 = min(h, cy + pad + 1)

        if x2 <= x1 or y2 <= y1:
            return

        roi = frame[y1:y2, x1:x2]
        overlay = roi.copy()
        cv2.circle(overlay, (cx - x1, cy - y1), current_r, color_bgr, thickness, cv2.LINE_AA)
        cv2.addWeighted(overlay, float(alpha * 0.75), roi, float(1.0 - alpha * 0.75), 0, roi)


class OrbRenderer:
    """Renders the holographic glowing orb and associated visual effects."""

    def __init__(self, theme_name: str = "cyan"):
        self.theme: ColorTheme = get_theme(theme_name)
        self.particles = ParticleSystem(num_orbit_particles=65)
        self.shockwaves: List[Shockwave] = []
        self.time_start = time.perf_counter()
        self.last_time = time.perf_counter()

        # Cached glow masks: key = rounded integer radius
        self._glow_cache: Dict[int, Tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
        # Cached pre-baked composite glow templates: (r_int, theme_tuple) -> (oi_u8, core_u8)
        self._composite_glow_cache: Dict[Tuple[int, Tuple[Any, ...]], Tuple[np.ndarray, np.ndarray]] = {}

    def set_theme(self, theme_or_name: Union[str, ColorTheme]) -> None:
        """Switch color theme."""
        if isinstance(theme_or_name, ColorTheme):
            self.theme = theme_or_name
        else:
            self.theme = get_theme(str(theme_or_name))

    def trigger_shockwave(self, cx: float, cy: float, radius: float) -> None:
        """Triggers a ripple shockwave at the given position."""
        self.shockwaves.append(
            Shockwave(cx, cy, start_radius=radius * 0.9, max_radius=radius * 2.3, duration=0.45)
        )
        self.particles.spawn_burst(cx, cy, count=28, speed_range=(70.0, 220.0))

    def _get_glow_maps(self, radius: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Generates or retrieves cached radial exponential glow intensity maps."""
        r_quantized = radius
        if r_quantized in self._glow_cache:
            return self._glow_cache[r_quantized]

        # Patch size is ~3.6x the orb radius to cover full soft falloff
        box_half = int(r_quantized * 1.8)
        size = box_half * 2 + 1

        y, x = np.ogrid[-box_half:box_half + 1, -box_half:box_half + 1]
        dist_sq = (x * x + y * y).astype(np.float32)
        dist = np.sqrt(dist_sq)

        r_f = float(r_quantized)

        # 1. Core map: high intensity white core
        core_sigma = r_f * 0.38
        core_map = np.exp(-0.5 * (dist / max(1.0, core_sigma)) ** 2)

        # 2. Inner glow: rich colored energy sphere
        inner_sigma = r_f * 0.85
        inner_map = np.exp(-1.5 * (dist / max(1.0, inner_sigma)) ** 1.6)

        # 3. Outer glow: wide soft atmospheric halo
        outer_sigma = r_f * 1.3
        outer_map = np.exp(-2.5 * (dist / max(1.0, outer_sigma)) ** 1.4)

        # Smooth boundary taper window ensuring intensity drops to 0 at box edge
        taper = np.clip(1.0 - (dist / float(box_half)) ** 2, 0.0, 1.0) ** 2
        core_map *= taper
        inner_map *= taper
        outer_map *= taper

        # Subtle scanline modulation on inner glow (hologram look)
        scanlines = 0.92 + 0.08 * np.sin(y * 1.8)
        inner_map *= scanlines.astype(np.float32)

        # Keep cache size reasonable
        if len(self._glow_cache) > 40:
            self._glow_cache.clear()

        self._glow_cache[r_quantized] = (core_map, inner_map, outer_map)
        return self._glow_cache[r_quantized]

    def _get_composite_glow(self, radius: int) -> Tuple[np.ndarray, np.ndarray]:
        """Returns pre-baked (outer_inner_template_u8, core_template_u8) for the orb."""
        theme_key = (self.theme.outer_glow, self.theme.inner_glow, self.theme.core)
        cache_key = (radius, theme_key)
        cached = self._composite_glow_cache.get(cache_key)
        if cached is not None:
            return cached

        core_map, inner_map, outer_map = self._get_glow_maps(radius)

        outer_w = np.array(self.theme.outer_glow, dtype=np.float32) * 0.75
        inner_w = np.array(self.theme.inner_glow, dtype=np.float32) * 1.1
        core_w = np.array(self.theme.core, dtype=np.float32) * 1.3

        oi_bgr = outer_map[:, :, None] * outer_w + inner_map[:, :, None] * inner_w
        oi_u8 = np.clip(oi_bgr, 0, 255).astype(np.uint8)
        core_u8 = np.clip(core_map[:, :, None] * core_w, 0, 255).astype(np.uint8)

        if len(self._composite_glow_cache) > 40:
            self._composite_glow_cache.clear()

        entry = (oi_u8, core_u8)
        self._composite_glow_cache[cache_key] = entry
        return entry

    def draw_electric_tether(
        self,
        frame: np.ndarray,
        start_pt: Tuple[float, float],
        end_pt: Tuple[float, float],
        color_bgr: Tuple[int, int, int],
    ) -> None:
        """Draws crackling fractal electric arcs from pinch point to orb center."""
        x1, y1 = start_pt
        x2, y2 = end_pt

        dx = x2 - x1
        dy = y2 - y1
        dist = math.hypot(dx, dy)
        if dist < 5.0:
            return

        # Normal vector for perpendicular jitter
        nx = -dy / dist
        ny = dx / dist

        # Generate jittered lightning segments
        num_segments = max(6, min(16, int(dist / 14)))
        points = [(int(x1), int(y1))]

        for i in range(1, num_segments):
            t = i / float(num_segments)
            # Maximum displacement in the middle
            envelope = math.sin(t * math.pi)
            jitter = random.uniform(-12.0, 12.0) * envelope

            px = int(x1 + dx * t + nx * jitter)
            py = int(y1 + dy * t + ny * jitter)
            points.append((px, py))

        points.append((int(x2), int(y2)))

        # Draw outer thick glow arc
        pts_arr = np.array(points, dtype=np.int32).reshape((-1, 1, 2))
        cv2.polylines(frame, [pts_arr], False, color_bgr, 3, cv2.LINE_AA)
        # Draw inner intense white arc
        cv2.polylines(frame, [pts_arr], False, (255, 255, 255), 1, cv2.LINE_AA)

    def draw_orbital_rings(
        self,
        frame: np.ndarray,
        cx: float,
        cy: float,
        radius: float,
        t: float,
        extra_rotation_deg: float = 0.0,
    ) -> None:
        """Draws rotating 3D gyroscopic holographic rings and dashed reticles."""
        center = (int(cx), int(cy))

        # Ring 1: Fast rotating equatorial ring
        angle1 = int((t * 45.0 + extra_rotation_deg) % 360)
        axes1 = (int(radius * 1.35), int(radius * 0.45))
        cv2.ellipse(frame, center, axes1, angle1, 0, 360, self.theme.ring_primary, 1, cv2.LINE_AA)

        # Segmented tick marks along Ring 1
        for deg in (0, 90, 180, 270):
            tick_angle = math.radians(angle1 + deg)
            tx = int(cx + axes1[0] * math.cos(tick_angle))
            ty = int(cy + axes1[1] * math.sin(tick_angle))
            cv2.circle(frame, (tx, ty), 2, (255, 255, 255), -1, cv2.LINE_AA)

        # Ring 2: Polar inclined ring rotating in opposite direction
        angle2 = int((-t * 30.0 + 60.0 - extra_rotation_deg * 0.7) % 360)
        axes2 = (int(radius * 1.55), int(radius * 0.55))
        cv2.ellipse(frame, center, axes2, angle2, 0, 360, self.theme.ring_secondary, 1, cv2.LINE_AA)

        # Ring 3: Segmented sci-fi reticle ring (dashed arcs)
        angle3 = int((t * 20.0 + 120.0 + extra_rotation_deg) % 360)
        axes3 = (int(radius * 1.15), int(radius * 1.15))
        # Draw 4 dashed arcs
        for arc_start in (0, 90, 180, 270):
            start_deg = (angle3 + arc_start) % 360
            cv2.ellipse(
                frame, center, axes3, 0,
                start_deg, start_deg + 50,
                self.theme.ring_primary, 2, cv2.LINE_AA
            )

    def render(
        self,
        frame: np.ndarray,
        center: Tuple[float, float],
        radius: float,
        is_grabbed: bool = False,
        pinch_pt: Optional[Tuple[float, float]] = None,
        dt: Optional[float] = None,
        rotation_deg: float = 0.0,
    ) -> None:
        """Composites the full holographic VFX stack onto the frame."""
        now = time.perf_counter()
        if dt is None:
            dt = max(0.001, min(0.1, now - self.last_time))
        self.last_time = now
        elapsed = now - self.time_start

        h, w = frame.shape[:2]
        cx, cy = center
        r_int = max(12, int(round(radius / 2.0) * 2))

        # Update shockwaves & particles
        self.shockwaves = [sw for sw in self.shockwaves if sw.update(dt)]
        self.particles.update(dt)

        # 1. Render shockwaves
        for sw in self.shockwaves:
            sw.render(frame, self.theme.shockwave)

        # 2. Render Electric Plasma Tether if grabbed
        if is_grabbed and pinch_pt is not None:
            self.draw_electric_tether(frame, pinch_pt, (cx, cy), self.theme.tether)

        # 3. Additive Radial Glow Field via Local ROI
        box_half = int(r_int * 1.8)
        x_min = int(cx - box_half)
        y_min = int(cy - box_half)
        x_max = x_min + box_half * 2 + 1
        y_max = y_min + box_half * 2 + 1

        # Bounds check ROI within frame
        roi_x1 = max(0, x_min)
        roi_y1 = max(0, y_min)
        roi_x2 = min(w, x_max)
        roi_y2 = min(h, y_max)

        if roi_x2 > roi_x1 and roi_y2 > roi_y1:
            oi_template, core_template = self._get_composite_glow(r_int)

            # Slice corresponding portion of glow maps if ROI was clipped
            map_x1 = roi_x1 - x_min
            map_y1 = roi_y1 - y_min
            map_x2 = map_x1 + (roi_x2 - roi_x1)
            map_y2 = map_y1 + (roi_y2 - roi_y1)

            oi_slice = oi_template[map_y1:map_y2, map_x1:map_x2]
            c_slice = core_template[map_y1:map_y2, map_x1:map_x2]

            # Subtle holographic breathing / oscillation
            breath = float(0.94 + 0.06 * math.sin(elapsed * 5.0))

            # Fast in-place SIMD integer scaling for outer/inner glow breathing modulation
            modulated = cv2.convertScaleAbs(oi_slice, alpha=breath)
            glow_u8 = cv2.add(modulated, c_slice)

            # In-place saturated additive composite using optimized OpenCV SIMD
            cv2.add(frame[roi_y1:roi_y2, roi_x1:roi_x2], glow_u8, dst=frame[roi_y1:roi_y2, roi_x1:roi_x2])

        # 4. Render Gyroscopic Orbital Rings
        self.draw_orbital_rings(frame, cx, cy, radius, elapsed, extra_rotation_deg=rotation_deg)

        # 5. Render Orbiting 3D Particles
        self.particles.render(frame, cx, cy, radius, self.theme.particle)

        # 6. Core Center Sparkle
        center_pt = (int(cx), int(cy))
        cv2.circle(frame, center_pt, max(2, int(radius * 0.14)), (255, 255, 255), -1, cv2.LINE_AA)
