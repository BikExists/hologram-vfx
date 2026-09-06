"""3D Holographic Particle System.

Simulates orbiting energy sparkles in pseudo-3D around the orb core,
along with transient radial bursts when grabbing or releasing.
"""

import math
import random
from typing import List, Tuple
import cv2
import numpy as np


class OrbitParticle:
    """A particle in an inclined 3D orbital trajectory around the orb."""

    def __init__(self, base_radius: float):
        self.reset(base_radius)

    def reset(self, base_radius: float) -> None:
        self.orbit_mult = random.uniform(0.7, 1.8)
        self.inclination = random.uniform(0, math.pi)
        self.tilt = random.uniform(-0.5, 0.5)
        self.angle = random.uniform(0, 2 * math.pi)
        self.speed = random.uniform(1.2, 3.5) * (1 if random.random() > 0.35 else -1)
        self.base_size = random.uniform(1.0, 2.8)
        self.phase = random.uniform(0, 2 * math.pi)

    def update(self, dt: float) -> None:
        self.angle = (self.angle + self.speed * dt) % (2 * math.pi)


class BurstParticle:
    """A transient particle expanding outwards upon gesture trigger."""

    def __init__(self, cx: float, cy: float, speed: float, angle: float, lifetime: float = 0.5):
        self.x = cx
        self.y = cy
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.lifetime = lifetime
        self.age = 0.0
        self.size = random.uniform(1.5, 3.0)

    def update(self, dt: float) -> bool:
        """Returns True if particle is still alive."""
        self.age += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        # Friction
        self.vx *= 0.94
        self.vy *= 0.94
        return self.age < self.lifetime


class ParticleSystem:
    """Manages orbital particles and transient bursts around the orb."""

    def __init__(self, num_orbit_particles: int = 60):
        self.orbit_particles: List[OrbitParticle] = [
            OrbitParticle(base_radius=50.0) for _ in range(num_orbit_particles)
        ]
        self.burst_particles: List[BurstParticle] = []

    def spawn_burst(self, cx: float, cy: float, count: int = 24, speed_range: Tuple[float, float] = (80.0, 260.0)) -> None:
        """Triggers a radial burst of energy sparkles."""
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(*speed_range)
            lifetime = random.uniform(0.35, 0.7)
            self.burst_particles.append(BurstParticle(cx, cy, speed, angle, lifetime))

    def update(self, dt: float) -> None:
        """Updates particle kinematics."""
        for p in self.orbit_particles:
            p.update(dt)

        # Update burst particles and filter dead ones
        self.burst_particles = [bp for bp in self.burst_particles if bp.update(dt)]

    def render(
        self,
        canvas: np.ndarray,
        center_x: float,
        center_y: float,
        current_radius: float,
        color_bgr: Tuple[int, int, int],
    ) -> None:
        """Draws all active particles onto canvas using additive blending."""
        h, w = canvas.shape[:2]
        if current_radius <= 2:
            return

        # Render 3D orbit particles
        for p in self.orbit_particles:
            r = current_radius * p.orbit_mult
            # 3D spherical / elliptical coords
            x_3d = r * math.cos(p.angle)
            y_3d = r * math.sin(p.angle) * math.cos(p.inclination)
            z_3d = r * math.sin(p.angle) * math.sin(p.inclination)

            # Perspective depth scale
            # z_3d in [-r, r] -> depth in [0.7, 1.3]
            depth = 1.0 + (z_3d / (3.0 * max(10.0, r)))
            depth = max(0.4, min(1.6, depth))

            px = int(center_x + x_3d * depth)
            py = int(center_y + y_3d * depth)

            if 0 <= px < w and 0 <= py < h:
                # Intensity scales with depth (front particles are brighter)
                brightness = math.sin(p.angle + p.phase) * 0.2 + 0.8
                alpha = max(0.2, min(1.0, (depth - 0.4) / 1.2 * brightness))
                radius = max(1, int(round(p.base_size * depth)))

                particle_color = (
                    int(color_bgr[0] * alpha),
                    int(color_bgr[1] * alpha),
                    int(color_bgr[2] * alpha),
                )
                cv2.circle(canvas, (px, py), radius, particle_color, -1, cv2.LINE_AA)

        # Render burst particles
        for bp in self.burst_particles:
            px = int(bp.x)
            py = int(bp.y)
            if 0 <= px < w and 0 <= py < h:
                progress = bp.age / bp.lifetime
                alpha = max(0.0, 1.0 - progress)
                radius = max(1, int(round(bp.size * alpha)))

                burst_color = (
                    int(color_bgr[0] * alpha),
                    int(color_bgr[1] * alpha),
                    int(color_bgr[2] * alpha),
                )
                cv2.circle(canvas, (px, py), radius, burst_color, -1, cv2.LINE_AA)
