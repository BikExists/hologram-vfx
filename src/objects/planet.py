"""Holographic Planet Implementation.

A celestial holographic planet featuring spherical atmospheric limb glow,
rotating latitude bands and wireframe meridians, depth-sorted concentric Saturn-like
rings (back/front layered around the planetary disk), an orbiting moon with a dust trail,
cosmic dust particles, electric pinch tethers, and shockwaves.
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


class HolographicPlanet(BaseHolographicObject):
    """Celestial Holographic Planet with Rings and Orbiting Moon."""

    def __init__(
        self,
        frame_width: int = 640,
        frame_height: int = 480,
        theme_name: str = "cyan",
        on_grab: Optional[Callable[[float, float, float], None]] = None,
        on_release: Optional[Callable[[float, float, float], None]] = None,
    ):
        super().__init__(
            name="Planet",
            frame_width=frame_width,
            frame_height=frame_height,
            theme_name=theme_name,
            min_radius=28.0,
            max_radius=125.0,
            default_radius=52.0,
            on_grab=on_grab,
            on_release=on_release,
        )

        # Celestial orbital and spin parameters
        self.axial_tilt_deg: float = 24.0
        self.spin_angle: float = 0.0
        self.moon_angle: float = 0.0
        self.moon_trail: List[Tuple[float, float, float]] = []  # (x, y, age)

        # Visual VFX components
        self.aura_cache = get_aura_cache()
        self.particles = ParticleSystem(num_orbit_particles=40)
        self.shockwaves: List[Shockwave] = []
        self.time_start = time.perf_counter()
        self.last_update = time.perf_counter()

    def trigger_shockwave(self, cx: float, cy: float, radius: float) -> None:
        """Triggers radial burst and shockwave on grab/release."""
        self.shockwaves.append(
            Shockwave(cx, cy, start_radius=radius * 0.9, max_radius=radius * 2.4, duration=0.45)
        )
        self.particles.spawn_burst(cx, cy, count=26, speed_range=(75.0, 210.0))

    def update(
        self,
        hands: Union[Optional[HandData], List[HandData]] = None,
        dt: Optional[float] = None,
    ) -> Tuple[float, float, float]:
        """Updates kinematics, planetary axial rotation, two-hand transform, moon orbit, and particles."""
        now = time.perf_counter()
        if dt is None:
            dt = max(0.001, min(0.1, now - self.last_update))
        self.last_update = now

        # Update position and size via common controller
        x, y, radius = self.controller.update(hands, dt=dt)

        # Planetary rotation and moon orbit
        speed_mult = 1.7 if self.is_grabbed else (0.6 if self.interaction_mode == "TWO_HANDS" else 1.0)
        self.spin_angle = (self.spin_angle + 0.65 * speed_mult * dt) % (2.0 * math.pi)
        self.moon_angle = (self.moon_angle + 1.25 * speed_mult * dt) % (2.0 * math.pi)

        # Update VFX particles and shockwaves
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
        """Draws crackling electric plasma arcs from pinch point to planet."""
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
            jitter = random.uniform(-11.0, 11.0) * envelope
            px = int(x1 + dx * t + nx * jitter)
            py = int(y1 + dy * t + ny * jitter)
            points.append((px, py))

        points.append((int(x2), int(y2)))
        pts_arr = np.array(points, dtype=np.int32).reshape((-1, 1, 2))
        cv2.polylines(frame, [pts_arr], False, color_bgr, 3, cv2.LINE_AA)
        cv2.polylines(frame, [pts_arr], False, (255, 255, 255), 1, cv2.LINE_AA)

    @property
    def effective_tilt_deg(self) -> float:
        """Composite axial tilt in degrees including two-hand rotation."""
        return (self.axial_tilt_deg + math.degrees(self.rotation)) % 360.0

    def _draw_rings_half(
        self,
        frame: np.ndarray,
        cx: float,
        cy: float,
        r: float,
        is_front: bool,
    ) -> None:
        """Draws depth-sorted halves of Saturn-like planetary rings.

        If is_front is False, renders the back half (angles 180..360) behind planet.
        If is_front is True, renders the front half (angles 0..180) in front of planet.
        """
        center = (int(cx), int(cy))
        tilt = self.effective_tilt_deg

        start_angle = 0 if is_front else 180
        end_angle = 180 if is_front else 360

        # Ring radii (Major, Minor)
        # Main inner ring
        axes_inner = (int(r * 1.55), int(r * 0.46))
        # Main outer ring
        axes_outer = (int(r * 2.15), int(r * 0.65))
        # Cassini division / middle band
        axes_mid = (int(r * 1.85), int(r * 0.55))

        # Local ROI bounding box for ring geometry
        pad = int(axes_outer[0]) + 8
        h_frame, w_frame = frame.shape[:2]
        x1 = max(0, int(cx - pad))
        y1 = max(0, int(cy - pad))
        x2 = min(w_frame, int(cx + pad + 1))
        y2 = min(h_frame, int(cy + pad + 1))

        if x2 <= x1 or y2 <= y1:
            return

        local_center = (int(cx - x1), int(cy - y1))
        roi = frame[y1:y2, x1:x2]
        overlay = roi.copy()

        # Broad translucent ring backdrop on local overlay
        cv2.ellipse(overlay, local_center, axes_outer, tilt, start_angle, end_angle, self.theme.ring_primary, 4, cv2.LINE_AA)
        cv2.ellipse(overlay, local_center, axes_mid, tilt, start_angle, end_angle, self.theme.ring_secondary, 2, cv2.LINE_AA)
        cv2.ellipse(overlay, local_center, axes_inner, tilt, start_angle, end_angle, self.theme.ring_primary, 1, cv2.LINE_AA)
        cv2.addWeighted(overlay, 0.40, roi, 0.60, 0, roi)

        # Crisp glowing ring lines directly onto local roi
        cv2.ellipse(roi, local_center, axes_outer, tilt, start_angle, end_angle, self.theme.ring_primary, 2, cv2.LINE_AA)
        cv2.ellipse(roi, local_center, axes_mid, tilt, start_angle, end_angle, self.theme.ring_secondary, 1, cv2.LINE_AA)
        cv2.ellipse(roi, local_center, axes_inner, tilt, start_angle, end_angle, (255, 255, 255), 1, cv2.LINE_AA)

    def render(
        self,
        frame: np.ndarray,
        pinch_pt: Optional[Tuple[float, float]] = None,
        dt: Optional[float] = None,
    ) -> None:
        """Renders the celestial holographic planet with depth-sorted rings and moon."""
        cx, cy = self.x, self.y
        r = max(14.0, self.current_radius * 0.85)
        r_int = int(r)
        h, w = frame.shape[:2]

        # 1. Render Shockwaves
        for sw in self.shockwaves:
            sw.render(frame, self.theme.shockwave)

        # 2. Render Back Half of Planetary Rings (behind planet sphere)
        self._draw_rings_half(frame, cx, cy, r, is_front=False)

        # 3. Render Atmospheric Glow Halo (cached)
        self.aura_cache.render_planet_halo(
            frame, cx, cy, r, self.theme.outer_glow, self.theme.inner_glow
        )

        # 4. Planetary Disk & Wireframe Latitude Bands
        center = (int(cx), int(cy))
        # Solid subtle disk fill via local ROI
        pad_disk = r_int + 2
        dx1 = max(0, int(cx - pad_disk))
        dy1 = max(0, int(cy - pad_disk))
        dx2 = min(w, int(cx + pad_disk + 1))
        dy2 = min(h, int(cy + pad_disk + 1))
        if dx2 > dx1 and dy2 > dy1:
            disk_roi = frame[dy1:dy2, dx1:dx2]
            disk_overlay = disk_roi.copy()
            cv2.circle(disk_overlay, (int(cx - dx1), int(cy - dy1)), r_int, self.theme.inner_glow, -1, cv2.LINE_AA)
            cv2.addWeighted(disk_overlay, 0.25, disk_roi, 0.75, 0, disk_roi)

        # Planet perimeter boundary ring
        cv2.circle(frame, center, r_int, self.theme.ring_primary, 2, cv2.LINE_AA)

        # Rotating surface meridians and latitude bands
        tilt = self.effective_tilt_deg
        # 3 latitude bands
        for lat_ratio in (-0.55, -0.25, 0.0, 0.25, 0.55):
            band_y = int(r * lat_ratio)
            band_r = math.sqrt(max(1.0, r * r - band_y * band_y))
            # Elliptical latitude line
            axes = (int(band_r), max(2, int(band_r * 0.32)))
            # Offset along tilted axis
            rad_tilt = math.radians(tilt)
            bx = int(cx - band_y * math.sin(rad_tilt))
            by = int(cy + band_y * math.cos(rad_tilt))
            cv2.ellipse(frame, (bx, by), axes, tilt, 0, 360, self.theme.ring_secondary, 1, cv2.LINE_AA)

        # Rotating longitude meridian (elliptical arc swinging from -1 to 1)
        long_phase = math.sin(self.spin_angle)
        long_w = max(1, int(r * abs(long_phase)))
        cv2.ellipse(frame, center, (long_w, r_int), tilt, 0, 360, (255, 255, 255), 1, cv2.LINE_AA)

        # 5. Render Front Half of Planetary Rings (in front of planet sphere)
        self._draw_rings_half(frame, cx, cy, r, is_front=True)

        # 6. Orbiting Moon / Satellite
        moon_dist = r * 2.7
        tilt_rad = math.radians(self.effective_tilt_deg - 15.0)
        # 3D inclined orbit coordinates
        mx_local = moon_dist * math.cos(self.moon_angle)
        my_local = (moon_dist * 0.42) * math.sin(self.moon_angle)
        moon_x = int(cx + mx_local * math.cos(tilt_rad) - my_local * math.sin(tilt_rad))
        moon_y = int(cy + mx_local * math.sin(tilt_rad) + my_local * math.cos(tilt_rad))
        moon_r = max(3, int(r * 0.16))

        # Moon trail
        self.moon_trail.append((moon_x, moon_y, time.perf_counter()))
        now = time.perf_counter()
        self.moon_trail = [pt for pt in self.moon_trail if now - pt[2] < 0.45]
        for tx, ty, t_time in self.moon_trail:
            alpha = max(0.1, 1.0 - (now - t_time) / 0.45)
            cv2.circle(frame, (int(tx), int(ty)), max(1, int(moon_r * alpha * 0.6)), self.theme.ring_secondary, -1, cv2.LINE_AA)

        # Moon body and core
        cv2.circle(frame, (moon_x, moon_y), moon_r + 2, self.theme.ring_primary, 1, cv2.LINE_AA)
        cv2.circle(frame, (moon_x, moon_y), moon_r, self.theme.ring_secondary, -1, cv2.LINE_AA)
        cv2.circle(frame, (moon_x, moon_y), max(1, moon_r - 2), (255, 255, 255), -1, cv2.LINE_AA)

        # 7. Render Electric Plasma Tether if grabbed
        if self.is_grabbed and pinch_pt is not None:
            self.draw_electric_tether(frame, pinch_pt, (cx, cy), self.theme.tether)

        # 8. Render Orbiting 3D Cosmic Particles
        self.particles.render(frame, cx, cy, r * 1.35, self.theme.particle)

        # 9. Planet Core Sparkle
        cv2.circle(frame, center, max(2, int(r * 0.12)), (255, 255, 255), -1, cv2.LINE_AA)
