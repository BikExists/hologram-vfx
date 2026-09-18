"""Holographic Cube Implementation.

A high-tech rotating 3D holographic wireframe cube with perspective projection,
glowing edges, depth-sorted translucent faceted faces with holographic scanlines,
vertex node beacons, orbital particles, electric pinch tethers, and shockwaves.
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


class HolographicCube(BaseHolographicObject):
    """3D Rotating Holographic Cybernetic Cube."""

    # 12 edges connecting 8 vertices
    EDGES = [
        (0, 1), (1, 2), (2, 3), (3, 0),  # Back face
        (4, 5), (5, 6), (6, 7), (7, 4),  # Front face
        (0, 4), (1, 5), (2, 6), (3, 7),  # Connecting pillars
    ]

    # 6 faces defined by vertex indices
    FACES = [
        (0, 1, 2, 3),  # Z-
        (4, 5, 6, 7),  # Z+
        (0, 1, 5, 4),  # Y-
        (2, 3, 7, 6),  # Y+
        (0, 3, 7, 4),  # X-
        (1, 2, 6, 5),  # X+
    ]

    def __init__(
        self,
        frame_width: int = 640,
        frame_height: int = 480,
        theme_name: str = "cyan",
        on_grab: Optional[Callable[[float, float, float], None]] = None,
        on_release: Optional[Callable[[float, float, float], None]] = None,
    ):
        super().__init__(
            name="Cube",
            frame_width=frame_width,
            frame_height=frame_height,
            theme_name=theme_name,
            min_radius=28.0,
            max_radius=125.0,
            default_radius=55.0,
            on_grab=on_grab,
            on_release=on_release,
        )

        # 3D Euler rotation angles (radians)
        self.pitch: float = 0.4
        self.yaw: float = 0.5
        self.roll: float = 0.2

        # Visual VFX components
        self.particles = ParticleSystem(num_orbit_particles=45)
        self.shockwaves: List[Shockwave] = []
        self.time_start = time.perf_counter()
        self.last_update = time.perf_counter()

    def trigger_shockwave(self, cx: float, cy: float, radius: float) -> None:
        """Triggers expanding ripple shockwaves and particle bursts."""
        self.shockwaves.append(
            Shockwave(cx, cy, start_radius=radius * 0.8, max_radius=radius * 2.2, duration=0.45)
        )
        self.particles.spawn_burst(cx, cy, count=24, speed_range=(70.0, 200.0))

    def update(
        self,
        hands: Union[Optional[HandData], List[HandData]] = None,
        dt: Optional[float] = None,
    ) -> Tuple[float, float, float]:
        """Updates kinematics, continuous 3D rotation, two-hand transform, and particles."""
        now = time.perf_counter()
        if dt is None:
            dt = max(0.001, min(0.1, now - self.last_update))
        self.last_update = now

        # Update position and size via common controller
        x, y, radius = self.controller.update(hands, dt=dt)

        # Continuous 3D rotation
        speed_mult = 1.6 if self.is_grabbed else (0.5 if self.interaction_mode == "TWO_HANDS" else 1.0)
        self.pitch = (self.pitch + 0.65 * speed_mult * dt) % (2.0 * math.pi)
        self.yaw = (self.yaw + 0.95 * speed_mult * dt) % (2.0 * math.pi)
        self.roll = (self.roll + 0.45 * speed_mult * dt) % (2.0 * math.pi)

        # Update VFX particles and shockwaves
        self.particles.update(dt)
        self.shockwaves = [sw for sw in self.shockwaves if sw.update(dt)]

        return x, y, radius

    def _get_rotation_matrix(self) -> np.ndarray:
        """Computes 3D composite rotation matrix (Roll * Yaw * Pitch) incorporating two-hand rotation."""
        effective_roll = (self.roll + self.rotation) % (2.0 * math.pi)
        cp, sp = math.cos(self.pitch), math.sin(self.pitch)
        cy, sy = math.cos(self.yaw), math.sin(self.yaw)
        cr, sr = math.cos(effective_roll), math.sin(effective_roll)

        Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]], dtype=np.float32)
        Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]], dtype=np.float32)
        Rz = np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]], dtype=np.float32)

        return Rz @ (Ry @ Rx)

    def draw_electric_tether(
        self,
        frame: np.ndarray,
        start_pt: Tuple[float, float],
        end_pt: Tuple[float, float],
        color_bgr: Tuple[int, int, int],
    ) -> None:
        """Draws crackling electric plasma arcs from pinch point to cube."""
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

    def render(
        self,
        frame: np.ndarray,
        pinch_pt: Optional[Tuple[float, float]] = None,
        dt: Optional[float] = None,
    ) -> None:
        """Renders the 3D rotating holographic cube and associated VFX."""
        cx, cy = self.x, self.y
        scale = max(15.0, self.current_radius * 0.95)
        h, w = frame.shape[:2]

        # 1. Render Shockwaves
        for sw in self.shockwaves:
            sw.render(frame, self.theme.shockwave)

        # 2. Render Ambient Volumetric Glow Field
        glow_r = int(scale * 1.5)
        if glow_r > 5:
            x1 = max(0, int(cx - glow_r))
            y1 = max(0, int(cy - glow_r))
            x2 = min(w, int(cx + glow_r))
            y2 = min(h, int(cy + glow_r))
            if x2 > x1 and y2 > y1:
                gx, gy = np.ogrid[y1 - cy:y2 - cy, x1 - cx:x2 - cx]
                dist = np.sqrt(gx * gx + gy * gy)
                aura = np.clip(1.0 - (dist / float(glow_r)), 0.0, 1.0) ** 2.2
                roi = frame[y1:y2, x1:x2].astype(np.float32)
                for ch in range(3):
                    roi[:, :, ch] += aura * (self.theme.inner_glow[ch] * 0.45)
                frame[y1:y2, x1:x2] = np.clip(roi, 0, 255).astype(np.uint8)

        # 3. Compute 3D Rotated Vertices
        s = scale * 0.8
        base_verts = np.array([
            [-s, -s, -s],
            [s, -s, -s],
            [s, s, -s],
            [-s, s, -s],
            [-s, -s, s],
            [s, -s, s],
            [s, s, s],
            [-s, s, s],
        ], dtype=np.float32)

        R = self._get_rotation_matrix()
        rotated_verts = base_verts @ R.T

        # Perspective projection
        D = 400.0  # Camera distance
        proj_2d: List[Tuple[int, int]] = []
        for X, Y, Z in rotated_verts:
            factor = D / max(1.0, D + Z)
            px = int(cx + X * factor)
            py = int(cy + Y * factor)
            proj_2d.append((px, py))

        # 4. Render Depth-Sorted Translucent Faces
        face_depths = []
        for face_idx, face in enumerate(self.FACES):
            avg_z = sum(rotated_verts[v][2] for v in face) / 4.0
            face_depths.append((avg_z, face_idx, face))

        # Sort back-to-front
        face_depths.sort(key=lambda item: item[0], reverse=True)

        face_overlay = frame.copy()
        face_tint = tuple(max(10, int(c * 0.35)) for c in self.theme.inner_glow)

        for _, _, face in face_depths:
            pts = np.array([proj_2d[v] for v in face], dtype=np.int32)
            # Translucent fill
            cv2.fillConvexPoly(face_overlay, pts, face_tint, cv2.LINE_AA)
            # Subtle face diagonal wireframe
            cv2.line(face_overlay, proj_2d[face[0]], proj_2d[face[2]], self.theme.ring_secondary, 1, cv2.LINE_AA)

        cv2.addWeighted(face_overlay, 0.45, frame, 0.55, 0, frame)

        # 5. Render Glowing Edges
        for v1, v2 in self.EDGES:
            pt1 = proj_2d[v1]
            pt2 = proj_2d[v2]
            # Outer thick neon glow edge
            cv2.line(frame, pt1, pt2, self.theme.ring_primary, 3, cv2.LINE_AA)
            # Inner white-hot edge
            cv2.line(frame, pt1, pt2, (255, 255, 255), 1, cv2.LINE_AA)

        # 6. Render Vertex Node Beacons
        for px, py in proj_2d:
            cv2.circle(frame, (px, py), 4, self.theme.ring_secondary, -1, cv2.LINE_AA)
            cv2.circle(frame, (px, py), 2, (255, 255, 255), -1, cv2.LINE_AA)

        # 7. Render Electric Plasma Tether if grabbed
        if self.is_grabbed and pinch_pt is not None:
            # Connect to closest vertex
            closest_pt = min(
                proj_2d,
                key=lambda p: (p[0] - pinch_pt[0]) ** 2 + (p[1] - pinch_pt[1]) ** 2
            )
            self.draw_electric_tether(frame, pinch_pt, closest_pt, self.theme.tether)

        # 8. Render Orbiting 3D Particle Dust
        self.particles.render(frame, cx, cy, scale * 1.25, self.theme.particle)

        # 9. Core Sparkle
        cv2.circle(frame, (int(cx), int(cy)), max(2, int(scale * 0.12)), (255, 255, 255), -1, cv2.LINE_AA)
