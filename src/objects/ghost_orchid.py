"""Holographic Ghost Orchid Implementation.

A delicate, rare botanical hologram (Dendrophylax lindenii) featuring ethereal
translucent petals, twin twisting lower tendrils, a glowing central labellum column,
blooming animation modulated by hand openness, floating pollen spores, and shockwaves.
"""

import math
import random
import time
from typing import Callable, List, Optional, Tuple, Union
import cv2
import numpy as np

from src.hand_tracker import HandData
from src.objects.base import BaseHolographicObject
from src.vfx.color_themes import ColorTheme
from src.vfx.aura import get_aura_cache
from src.vfx.orb_renderer import Shockwave
from src.vfx.particles import ParticleSystem


class HolographicGhostOrchid(BaseHolographicObject):
    """Ethereal Holographic Ghost Orchid with blooming petals and curling tendrils."""

    def __init__(
        self,
        frame_width: int = 640,
        frame_height: int = 480,
        theme_name: str = "cyan",
        on_grab: Optional[Callable[[float, float, float], None]] = None,
        on_release: Optional[Callable[[float, float, float], None]] = None,
    ):
        super().__init__(
            name="Ghost Orchid",
            frame_width=frame_width,
            frame_height=frame_height,
            theme_name=theme_name,
            min_radius=28.0,
            max_radius=125.0,
            default_radius=54.0,
            on_grab=on_grab,
            on_release=on_release,
        )

        # Botanical animation parameters
        self.bloom_factor: float = 0.5  # 0.0 (closed/resting) to 1.0 (fully blossomed)
        self.time_start = time.perf_counter()
        self.last_update = time.perf_counter()
        self.sway_angle: float = 0.0

        # Visual VFX components
        self.aura_cache = get_aura_cache()
        self.particles = ParticleSystem(num_orbit_particles=40)
        self.shockwaves: List[Shockwave] = []

    def trigger_shockwave(self, cx: float, cy: float, radius: float) -> None:
        """Triggers radial energy pulse on grab/release."""
        self.shockwaves.append(
            Shockwave(cx, cy, start_radius=radius * 0.8, max_radius=radius * 2.3, duration=0.45)
        )
        self.particles.spawn_burst(cx, cy, count=24, speed_range=(60.0, 190.0))

    def update(
        self,
        hands: Union[Optional[HandData], List[HandData]] = None,
        dt: Optional[float] = None,
    ) -> Tuple[float, float, float]:
        """Updates kinematics, blooming expansion, sway oscillation, and particles."""
        now = time.perf_counter()
        if dt is None:
            dt = max(0.001, min(0.1, now - self.last_update))
        self.last_update = now

        # Update position and size via common controller
        x, y, radius = self.controller.update(hands, dt=dt)

        # Extract openness to modulate flower blossoming
        target_bloom = 0.5
        if hands:
            hand_list = hands if isinstance(hands, list) else [hands]
            valid_hands = [h for h in hand_list if h is not None]
            if valid_hands:
                target_bloom = max(h.openness for h in valid_hands)

        # Smooth bloom transition
        self.bloom_factor += (target_bloom - self.bloom_factor) * min(1.0, 6.0 * dt)
        self.sway_angle = (self.sway_angle + 0.8 * dt) % (2.0 * math.pi)

        # Update particles and shockwaves
        self.particles.update(dt)
        self.shockwaves = [sw for sw in self.shockwaves if sw.update(dt)]

        return x, y, radius

    def draw_electric_tether(
        self,
        frame: np.ndarray,
        start_pt: Tuple[float, float],
        end_pt: Tuple[float, float],
        color_bgr: Tuple[int, int, int],
    ) -> None:
        """Draws crackling electric plasma arcs from pinch point to orchid center."""
        x1, y1 = start_pt
        x2, y2 = end_pt
        dx = x2 - x1
        dy = y2 - y1
        dist = math.hypot(dx, dy)
        if dist < 5.0:
            return

        nx = -dy / dist
        ny = dx / dist
        num_segments = max(6, min(16, int(dist / 14)))
        points = [(int(x1), int(y1))]

        for i in range(1, num_segments):
            t = i / float(num_segments)
            envelope = math.sin(t * math.pi)
            jitter = random.uniform(-10.0, 10.0) * envelope
            px = int(x1 + dx * t + nx * jitter)
            py = int(y1 + dy * t + ny * jitter)
            points.append((px, py))

        points.append((int(x2), int(y2)))
        pts_arr = np.array(points, dtype=np.int32).reshape((-1, 1, 2))
        cv2.polylines(frame, [pts_arr], False, color_bgr, 3, cv2.LINE_AA)
        cv2.polylines(frame, [pts_arr], False, (255, 255, 255), 1, cv2.LINE_AA)

    def render(
        self,
        frame: np.ndarray,
        pinch_pt: Optional[Tuple[float, float]] = None,
        dt: Optional[float] = None,
    ) -> None:
        """Renders the holographic Ghost Orchid with blooming petals and trailing tendrils."""
        cx, cy = self.x, self.y
        r = self.current_radius
        h, w = frame.shape[:2]

        # 1. Render Shockwaves
        for sw in self.shockwaves:
            sw.render(frame, self.theme.shockwave)

        # 2. Local ROI Bounding Box
        pad = int(r * 2.3) + 12
        x1 = max(0, int(cx - pad))
        y1 = max(0, int(cy - pad))
        x2 = min(w, int(cx + pad + 1))
        y2 = min(h, int(cy + pad + 1))

        if x2 <= x1 or y2 <= y1:
            return

        local_cx = cx - x1
        local_cy = cy - y1
        roi = frame[y1:y2, x1:x2]

        # 3. Ambient Volumetric Glow Field (cached)
        glow_r = int(r * 1.6)
        if glow_r > 5:
            self.aura_cache.render_standard_aura(
                roi, local_cx, local_cy, glow_r, self.theme.inner_glow, weight=0.40, power=2.2
            )

        # 4. Procedural Petal Geometry inside local ROI
        overlay = roi.copy()
        rot = self.rotation  # Radians

        # Bloom spread factor: petals curl open as bloom increases
        bloom_spread = 0.8 + 0.5 * self.bloom_factor

        # Helper to rotate local points around local_center
        cos_r = math.cos(rot)
        sin_r = math.sin(rot)

        def transform_pt(px_rel: float, py_rel: float) -> Tuple[int, int]:
            rx = px_rel * cos_r - py_rel * sin_r
            ry = px_rel * sin_r + py_rel * cos_r
            return (int(round(local_cx + rx)), int(round(local_cy + ry)))

        petal_color = self.theme.ring_primary
        core_color = self.theme.ring_secondary
        accent_color = self.theme.hud_accent

        # Petal 1: Dorsal Sepal (Apex Top Petal)
        top_h = r * 1.35 * bloom_spread
        top_w = r * 0.42
        top_pts = [
            transform_pt(0, 0),
            transform_pt(-top_w * 0.8, -top_h * 0.5),
            transform_pt(0, -top_h),
            transform_pt(top_w * 0.8, -top_h * 0.5),
        ]
        cv2.fillPoly(overlay, [np.array(top_pts, dtype=np.int32)], (petal_color[0] // 3, petal_color[1] // 3, petal_color[2] // 3), cv2.LINE_AA)
        cv2.polylines(overlay, [np.array(top_pts, dtype=np.int32)], True, petal_color, 1, cv2.LINE_AA)

        # Petals 2 & 3: Lateral Wing Petals (Left & Right)
        lat_len = r * 1.15 * bloom_spread
        lat_w = r * 0.35
        for side in (-1.0, 1.0):
            wing_pts = [
                transform_pt(0, 0),
                transform_pt(side * lat_len * 0.5, -lat_w * 0.7),
                transform_pt(side * lat_len, -lat_w * 0.2),
                transform_pt(side * lat_len * 0.6, lat_w * 0.6),
            ]
            cv2.fillPoly(overlay, [np.array(wing_pts, dtype=np.int32)], (petal_color[0] // 4, petal_color[1] // 4, petal_color[2] // 4), cv2.LINE_AA)
            cv2.polylines(overlay, [np.array(wing_pts, dtype=np.int32)], True, petal_color, 1, cv2.LINE_AA)

        # Petals 4 & 5: Signature Twin Twisting Lower Tendrils (Ghost Orchid Ribbon Tails)
        # Twisting wavy spline extending downward and out
        num_tendril_pts = 18
        sway = math.sin(self.sway_angle) * 4.0
        for side in (-1.0, 1.0):
            tendril_curve = []
            for i in range(num_tendril_pts):
                t = i / float(num_tendril_pts - 1)
                # Curve spirals outward and downward
                tx = side * (r * 0.2 + r * 1.1 * (t ** 1.3) * bloom_spread) + math.sin(t * 5.0 + self.sway_angle * 1.2) * (5.0 * t)
                ty = r * 0.15 + r * 1.85 * t + math.cos(t * 4.0) * (3.0 * t)
                tendril_curve.append(transform_pt(tx, ty))

            t_arr = np.array(tendril_curve, dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(overlay, [t_arr], False, core_color, 2, cv2.LINE_AA)
            cv2.polylines(overlay, [t_arr], False, (255, 255, 255), 1, cv2.LINE_AA)

        # 5. Central Labellum Column (Glowing Core)
        center_pt = transform_pt(0, 0)
        core_r = max(4, int(r * 0.28))
        cv2.circle(overlay, center_pt, core_r, accent_color, -1, cv2.LINE_AA)
        cv2.circle(overlay, center_pt, core_r, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.circle(overlay, center_pt, max(2, int(core_r * 0.45)), (255, 255, 255), -1, cv2.LINE_AA)

        # Alpha composite overlay back into ROI
        cv2.addWeighted(overlay, 0.75, roi, 0.25, 0, roi)

        # 6. Render Orbital Pollen Particles
        self.particles.render(frame, cx, cy, r * 1.1, self.theme.ring_primary)

        # 7. Render Electric Tether if Grabbed
        if pinch_pt is not None:
            self.draw_electric_tether(frame, pinch_pt, (cx, cy), self.theme.inner_glow)
