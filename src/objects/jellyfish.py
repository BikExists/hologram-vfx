"""Holographic Bioluminescent Jellyfish Implementation.

An ethereal deep-sea medusa featuring a pulsating translucent bell dome,
scalloped marginal rhopalia nodes, undulating central oral arms, flowing
harmonic-wave trailing tentacles with glowing tip beads, drifting bioluminescent
plankton, and dynamic swimming propulsion when grabbed.
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
from src.vfx.orb_renderer import Shockwave
from src.vfx.particles import ParticleSystem


class HolographicJellyfish(BaseHolographicObject):
    """Bioluminescent Holographic Medusa with organic pulsating tentacles."""

    def __init__(
        self,
        frame_width: int = 640,
        frame_height: int = 480,
        theme_name: str = "cyan",
        on_grab: Optional[Callable[[float, float, float], None]] = None,
        on_release: Optional[Callable[[float, float, float], None]] = None,
    ):
        super().__init__(
            name="Jellyfish",
            frame_width=frame_width,
            frame_height=frame_height,
            theme_name=theme_name,
            min_radius=28.0,
            max_radius=125.0,
            default_radius=52.0,
            on_grab=on_grab,
            on_release=on_release,
        )

        # Medusa swimming dynamics
        self.pulse_phase: float = 0.0
        self.time_start = time.perf_counter()
        self.last_update = time.perf_counter()

        # Visual VFX components
        self.particles = ParticleSystem(num_orbit_particles=42)
        self.shockwaves: List[Shockwave] = []

    def trigger_shockwave(self, cx: float, cy: float, radius: float) -> None:
        """Triggers radial energy pulse on grab/release."""
        self.shockwaves.append(
            Shockwave(cx, cy, start_radius=radius * 0.85, max_radius=radius * 2.3, duration=0.45)
        )
        self.particles.spawn_burst(cx, cy, count=26, speed_range=(75.0, 210.0))

    def update(
        self,
        hands: Union[Optional[HandData], List[HandData]] = None,
        dt: Optional[float] = None,
    ) -> Tuple[float, float, float]:
        """Updates kinematics, bell contraction cycles, tentacle wave phases, and particles."""
        now = time.perf_counter()
        if dt is None:
            dt = max(0.001, min(0.1, now - self.last_update))
        self.last_update = now

        # Update position and size via common controller
        x, y, radius = self.controller.update(hands, dt=dt)

        # Pulsation frequency increases when swimming/grabbed
        swim_rate = 3.2 if self.is_grabbed else (2.0 if self.is_hovered else 1.2)
        self.pulse_phase = (self.pulse_phase + swim_rate * 2.0 * math.pi * dt) % (2.0 * math.pi)

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
        """Draws crackling electric plasma arcs from pinch point to jellyfish dome."""
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
        """Renders the bioluminescent jellyfish with pulsating bell dome and wave tentacles."""
        cx, cy = self.x, self.y
        r = self.current_radius
        h, w = frame.shape[:2]

        # 1. Render Shockwaves
        for sw in self.shockwaves:
            sw.render(frame, self.theme.shockwave)

        # 2. Local ROI Bounding Box (accommodates trailing tentacles below dome)
        pad_x = int(r * 1.8) + 12
        pad_top = int(r * 1.5) + 10
        pad_bottom = int(r * 2.8) + 12
        x1 = max(0, int(cx - pad_x))
        y1 = max(0, int(cy - pad_top))
        x2 = min(w, int(cx + pad_x + 1))
        y2 = min(h, int(cy + pad_bottom + 1))

        if x2 <= x1 or y2 <= y1:
            return

        local_cx = cx - x1
        local_cy = cy - y1
        roi = frame[y1:y2, x1:x2]

        # 3. Ambient Volumetric Glow Field (in-place saturated addition)
        glow_r = int(r * 1.6)
        if glow_r > 5:
            gx, gy = np.ogrid[y1 - cy:y2 - cy, x1 - cx:x2 - cx]
            dist = np.sqrt(gx * gx + gy * gy)
            aura = np.clip(1.0 - (dist / float(glow_r)), 0.0, 1.0) ** 2.2
            aura_w = np.array(self.theme.inner_glow, dtype=np.float32) * 0.42
            glow_bgr = aura[:, :, None] * aura_w
            glow_u8 = np.clip(glow_bgr, 0, 255).astype(np.uint8)
            cv2.add(roi, glow_u8, dst=roi)

        # 4. Procedural Medusa Geometry inside Local ROI
        overlay = roi.copy()
        rot = self.rotation  # Radians

        cos_r = math.cos(rot)
        sin_r = math.sin(rot)

        def transform_pt(px_rel: float, py_rel: float) -> Tuple[int, int]:
            rx = px_rel * cos_r - py_rel * sin_r
            ry = px_rel * sin_r + py_rel * cos_r
            return (int(round(local_cx + rx)), int(round(local_cy + ry)))

        rim_color = self.theme.ring_primary
        core_color = self.theme.ring_secondary
        accent_color = self.theme.hud_accent

        # Contraction factor for organic swimming pulse:
        # Sharp contraction, slow expansion
        contract = 0.5 + 0.5 * math.sin(self.pulse_phase)
        dome_w = r * (1.15 - 0.20 * contract)
        dome_h = r * (0.85 + 0.25 * contract)

        # --- A. Trailing Bioluminescent Tentacles (Drawn first so dome renders in front) ---
        num_tentacles = 7
        tentacle_len = r * 1.9
        tentacle_pts_count = 16

        for t_idx in range(num_tentacles):
            t_frac = (t_idx / float(num_tentacles - 1)) * 2.0 - 1.0  # -1.0 to 1.0
            tentacle_base_x = t_frac * (dome_w * 0.72)
            tentacle_base_y = dome_h * 0.15

            phase_offset = t_idx * 0.75 + self.pulse_phase * 1.3
            curve_pts = []

            for seg in range(tentacle_pts_count):
                st = seg / float(tentacle_pts_count - 1)
                # Traveling wave equation: amplitude grows toward tip
                amp = (r * 0.22) * st
                wave_x = tentacle_base_x + math.sin(phase_offset - st * 4.5) * amp
                wave_y = tentacle_base_y + tentacle_len * st
                curve_pts.append(transform_pt(wave_x, wave_y))

            c_arr = np.array(curve_pts, dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(overlay, [c_arr], False, core_color, 1, cv2.LINE_AA)

            # Glowing tip bead
            tip_pt = curve_pts[-1]
            cv2.circle(overlay, tip_pt, max(2, int(r * 0.05)), (255, 255, 255), -1, cv2.LINE_AA)
            cv2.circle(overlay, tip_pt, max(3, int(r * 0.08)), rim_color, 1, cv2.LINE_AA)

        # --- B. Wavy Central Oral Arms ---
        for side in (-1.0, 1.0):
            arm_pts = []
            for a_seg in range(12):
                at = a_seg / 11.0
                ax = side * (r * 0.15) + math.sin(self.pulse_phase * 1.5 + at * 3.5) * (r * 0.12 * at)
                ay = dome_h * 0.1 + (r * 1.1) * at
                arm_pts.append(transform_pt(ax, ay))
            a_arr = np.array(arm_pts, dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(overlay, [a_arr], False, accent_color, 2, cv2.LINE_AA)

        # --- C. Pulsating Translucent Bell Dome ---
        # Parametric parabolic arch for the jellyfish umbrella
        dome_pts = []
        num_dome_samples = 24
        for i in range(num_dome_samples):
            th = (i / float(num_dome_samples - 1)) * math.pi  # 0 to pi
            # Cosine for width, sine for height
            dx = -math.cos(th) * dome_w
            dy = -math.sin(th) * dome_h
            dome_pts.append(transform_pt(dx, dy))

        # Bottom rim margin with scalloped folds
        num_rim_folds = 12
        for j in range(num_rim_folds, -1, -1):
            rt = j / float(num_rim_folds)  # 1 to 0
            rx = (rt * 2.0 - 1.0) * dome_w
            # Scalloped wave along bottom edge
            scallop = math.sin(rt * math.pi * 6.0) * (r * 0.06)
            ry = scallop
            dome_pts.append(transform_pt(rx, ry))

        d_arr = np.array(dome_pts, dtype=np.int32)
        # Translucent bell body fill
        cv2.fillPoly(overlay, [d_arr], (rim_color[0] // 3, rim_color[1] // 3, rim_color[2] // 3), cv2.LINE_AA)
        # Neon contour lines
        cv2.polylines(overlay, [d_arr], True, rim_color, 2, cv2.LINE_AA)
        cv2.polylines(overlay, [d_arr], True, (255, 255, 255), 1, cv2.LINE_AA)

        # --- D. Scalloped Marginal Rhopalia (Glowing Sensory Nodes) ---
        for node_idx in range(6):
            nt = (node_idx / 5.0) * 2.0 - 1.0
            nx = nt * (dome_w * 0.88)
            ny = math.sin((nt + 1.0) * math.pi * 3.0) * (r * 0.05)
            n_pt = transform_pt(nx, ny)
            cv2.circle(overlay, n_pt, max(2, int(r * 0.04)), (255, 255, 255), -1, cv2.LINE_AA)
            cv2.circle(overlay, n_pt, max(3, int(r * 0.07)), accent_color, 1, cv2.LINE_AA)

        # Alpha composite overlay back into ROI
        cv2.addWeighted(overlay, 0.78, roi, 0.22, 0, roi)

        # 5. Render Bioluminescent Plankton Particles
        self.particles.render(frame, cx, cy, r * 1.2, self.theme.ring_primary)

        # 6. Render Electric Tether if Grabbed
        if pinch_pt is not None:
            self.draw_electric_tether(frame, pinch_pt, (cx, cy), self.theme.inner_glow)
