"""Holographic Bhondu Face Implementation.

A stylized, expressive procedural holographic emoji face inspired by the legendary
Distorted Face (U+1FAEA). Features a warped double-rim head, huge bulging upward-gazing
eyes with specular sparks, expressive arched eyebrows, a squiggly quivering mouth,
glowing rosy cheeks, cybernetic scanlines, and reactive animations.
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


class HolographicBhonduFace(BaseHolographicObject):
    """Procedural Stylized Holographic Bhondu Face (Distorted Emoji)."""

    def __init__(
        self,
        frame_width: int = 640,
        frame_height: int = 480,
        theme_name: str = "cyan",
        on_grab: Optional[Callable[[float, float, float], None]] = None,
        on_release: Optional[Callable[[float, float, float], None]] = None,
    ):
        super().__init__(
            name="Bhondu Face",
            frame_width=frame_width,
            frame_height=frame_height,
            theme_name=theme_name,
            min_radius=28.0,
            max_radius=125.0,
            default_radius=55.0,
            on_grab=on_grab,
            on_release=on_release,
        )

        # Expressive animation states
        self.time_start = time.perf_counter()
        self.last_update = time.perf_counter()
        self.quiver_phase: float = 0.0
        self.blink_timer: float = 0.0
        self.wobble_angle: float = 0.0

        # Visual VFX components
        self.particles = ParticleSystem(num_orbit_particles=36)
        self.shockwaves: List[Shockwave] = []

    def trigger_shockwave(self, cx: float, cy: float, radius: float) -> None:
        """Triggers comical shockwave burst on grab/release."""
        self.shockwaves.append(
            Shockwave(cx, cy, start_radius=radius * 0.85, max_radius=radius * 2.2, duration=0.42)
        )
        self.particles.spawn_burst(cx, cy, count=22, speed_range=(70.0, 200.0))

    def update(
        self,
        hands: Union[Optional[HandData], List[HandData]] = None,
        dt: Optional[float] = None,
    ) -> Tuple[float, float, float]:
        """Updates kinematics, quiver oscillation, eye blinking, and particles."""
        now = time.perf_counter()
        if dt is None:
            dt = max(0.001, min(0.1, now - self.last_update))
        self.last_update = now

        # Update position and size via common controller
        x, y, radius = self.controller.update(hands, dt=dt)

        # Subtle comic quivering animation (distorted mouth / wobbly expression)
        speed_mult = 2.2 if self.is_grabbed else (1.5 if self.is_hovered else 1.0)
        self.quiver_phase = (self.quiver_phase + 7.5 * speed_mult * dt) % (2.0 * math.pi)
        self.wobble_angle = math.sin(self.quiver_phase * 0.8) * 0.05
        self.blink_timer = (self.blink_timer + dt) % 4.5

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
        """Draws crackling electric plasma arcs from pinch point to face."""
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
        """Renders the holographic Bhondu Face with bulging eyes, quivering mouth, and cyber accents."""
        cx, cy = self.x, self.y
        r = self.current_radius
        h, w = frame.shape[:2]

        # 1. Render Shockwaves
        for sw in self.shockwaves:
            sw.render(frame, self.theme.shockwave)

        # 2. Local ROI Bounding Box
        pad = int(r * 1.8) + 10
        x1 = max(0, int(cx - pad))
        y1 = max(0, int(cy - pad))
        x2 = min(w, int(cx + pad + 1))
        y2 = min(h, int(cy + pad + 1))

        if x2 <= x1 or y2 <= y1:
            return

        local_cx = cx - x1
        local_cy = cy - y1
        roi = frame[y1:y2, x1:x2]

        # 3. Ambient Volumetric Glow Field (in-place saturated addition)
        glow_r = int(r * 1.5)
        if glow_r > 5:
            gx, gy = np.ogrid[y1 - cy:y2 - cy, x1 - cx:x2 - cx]
            dist = np.sqrt(gx * gx + gy * gy)
            aura = np.clip(1.0 - (dist / float(glow_r)), 0.0, 1.0) ** 2.2
            aura_w = np.array(self.theme.inner_glow, dtype=np.float32) * 0.42
            glow_bgr = aura[:, :, None] * aura_w
            glow_u8 = np.clip(glow_bgr, 0, 255).astype(np.uint8)
            cv2.add(roi, glow_u8, dst=roi)

        # 4. Procedural Face Elements inside Local ROI
        overlay = roi.copy()
        rot = self.rotation + self.wobble_angle

        cos_r = math.cos(rot)
        sin_r = math.sin(rot)

        def transform_pt(px_rel: float, py_rel: float) -> Tuple[int, int]:
            rx = px_rel * cos_r - py_rel * sin_r
            ry = px_rel * sin_r + py_rel * cos_r
            return (int(round(local_cx + rx)), int(round(local_cy + ry)))

        rim_color = self.theme.ring_primary
        accent_color = self.theme.hud_accent
        cheek_color = (255, 140, 180)  # Rosy neon blush

        # --- A. Circular Head Outline & Internal Glass Fill ---
        r_int = max(8, int(r))
        center_pt = (int(round(local_cx)), int(round(local_cy)))

        # Translucent face mask
        cv2.circle(overlay, center_pt, r_int, (20, 28, 38), -1, cv2.LINE_AA)
        # Double outer holographic neon rim
        cv2.circle(overlay, center_pt, r_int, rim_color, 2, cv2.LINE_AA)
        cv2.circle(overlay, center_pt, max(4, r_int - 3), accent_color, 1, cv2.LINE_AA)

        # --- B. Bulging Upward-Gazing Eyes ---
        eye_spacing = r * 0.42
        eye_y_rel = -r * 0.18
        eye_rx = max(4, int(r * 0.28))
        eye_ry = max(5, int(r * 0.35))  # Bulging vertically

        for side in (-1.0, 1.0):
            eye_cx = side * eye_spacing
            eye_cy = eye_y_rel
            e_pt = transform_pt(eye_cx, eye_cy)

            # Eye white (bulging oval)
            cv2.ellipse(overlay, e_pt, (eye_rx, eye_ry), int(math.degrees(rot)), 0, 360, (245, 250, 255), -1, cv2.LINE_AA)
            cv2.ellipse(overlay, e_pt, (eye_rx, eye_ry), int(math.degrees(rot)), 0, 360, rim_color, 1, cv2.LINE_AA)

            # Upward/sideways looking pupil (the classic Bhondu gaze!)
            pupil_offset_x = side * (eye_rx * 0.22)
            pupil_offset_y = -eye_ry * 0.45
            pupil_pt = transform_pt(eye_cx + pupil_offset_x, eye_cy + pupil_offset_y)
            pupil_r = max(2, int(eye_rx * 0.48))
            cv2.circle(overlay, pupil_pt, pupil_r, (15, 20, 30), -1, cv2.LINE_AA)

            # Specular highlight sparks (gives that goofy bewildered spark)
            spark1_pt = transform_pt(eye_cx + pupil_offset_x - pupil_r * 0.35, eye_cy + pupil_offset_y - pupil_r * 0.35)
            spark2_pt = transform_pt(eye_cx + pupil_offset_x + pupil_r * 0.30, eye_cy + pupil_offset_y + pupil_r * 0.30)
            cv2.circle(overlay, spark1_pt, max(1, pupil_r // 3), (255, 255, 255), -1, cv2.LINE_AA)
            cv2.circle(overlay, spark2_pt, max(1, pupil_r // 5), (255, 255, 255), -1, cv2.LINE_AA)

        # --- C. Wobbly / Inquisitive Arched Eyebrows ---
        brow_y = -r * 0.62
        brow_w = r * 0.32
        for side in (-1.0, 1.0):
            # Eyebrow arch points
            b_pts = [
                transform_pt(side * (eye_spacing - brow_w * 0.5), brow_y + r * 0.06),
                transform_pt(side * eye_spacing, brow_y - r * 0.08),
                transform_pt(side * (eye_spacing + brow_w * 0.5), brow_y + r * 0.04),
            ]
            b_arr = np.array(b_pts, dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(overlay, [b_arr], False, rim_color, 2, cv2.LINE_AA)

        # --- D. Rosy Cheeks (Neon Blush) ---
        cheek_y = r * 0.24
        cheek_spacing = r * 0.55
        for side in (-1.0, 1.0):
            ch_pt = transform_pt(side * cheek_spacing, cheek_y)
            cv2.ellipse(overlay, ch_pt, (int(r * 0.18), int(r * 0.10)), int(math.degrees(rot)), 0, 360, cheek_color, -1, cv2.LINE_AA)

        # --- E. Squiggly Quivering Mouth (Distorted Emoji Signature) ---
        mouth_y = r * 0.44
        mouth_pts = []
        num_mouth_pts = 12
        mouth_half_w = r * 0.28
        quiver = math.sin(self.quiver_phase) * (r * 0.04)

        for i in range(num_mouth_pts):
            t = (i / float(num_mouth_pts - 1)) * 2.0 - 1.0  # -1.0 to 1.0
            # Sinuous curve with quivering wave
            mx = t * mouth_half_w
            my = mouth_y + (t * t) * (r * 0.08) + math.sin(t * 5.0 + self.quiver_phase) * (r * 0.04)
            mouth_pts.append(transform_pt(mx, my))

        m_arr = np.array(mouth_pts, dtype=np.int32).reshape((-1, 1, 2))
        cv2.polylines(overlay, [m_arr], False, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.polylines(overlay, [m_arr], False, rim_color, 1, cv2.LINE_AA)

        # --- F. Subtle Cybernetic Scanlines across Face ---
        scan_step = max(4, int(r * 0.16))
        for sy_rel in range(-r_int + scan_step, r_int, scan_step):
            chord_half = math.sqrt(max(0.0, r_int * r_int - sy_rel * sy_rel))
            p1 = transform_pt(-chord_half * 0.85, sy_rel)
            p2 = transform_pt(chord_half * 0.85, sy_rel)
            cv2.line(overlay, p1, p2, (30, 50, 70), 1)

        # Alpha composite overlay back into ROI
        cv2.addWeighted(overlay, 0.82, roi, 0.18, 0, roi)

        # 5. Render Orbiting Emoji Sparks
        self.particles.render(frame, cx, cy, r * 1.15, self.theme.ring_secondary)

        # 6. Render Electric Tether if Grabbed
        if pinch_pt is not None:
            self.draw_electric_tether(frame, pinch_pt, (cx, cy), self.theme.inner_glow)
