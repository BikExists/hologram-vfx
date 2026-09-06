"""Orb State Machine, Kinematics, and Hand Interaction.

Coordinates orb states (Floating, Hovered, Grabbed, Released),
spring-damper physics, smooth radius scaling via hand openness,
and viewport boundary constraints.
"""

import math
import time
from typing import Callable, Optional, Tuple
from src.filters import EMAFilter, OneEuroFilter, PointFilter
from src.hand_tracker import HandData


class OrbController:
    """Controls the position, size, and interaction dynamics of the holographic orb."""

    def __init__(
        self,
        frame_width: int = 640,
        frame_height: int = 480,
        min_radius: float = 28.0,
        max_radius: float = 125.0,
        default_radius: float = 55.0,
        on_grab: Optional[Callable[[float, float, float], None]] = None,
        on_release: Optional[Callable[[float, float, float], None]] = None,
    ):
        self.w = frame_width
        self.h = frame_height

        self.min_radius = float(min_radius)
        self.max_radius = float(max_radius)
        self.default_radius = float(default_radius)

        # Callbacks for VFX events (e.g. shockwaves, sound)
        self.on_grab = on_grab
        self.on_release = on_release

        # Spatial state
        self.x: float = frame_width * 0.5
        self.y: float = frame_height * 0.5
        self.rest_x: float = self.x
        self.rest_y: float = self.y
        self.vx: float = 0.0
        self.vy: float = 0.0

        # Radius state
        self.current_radius: float = self.default_radius
        self.target_radius: float = self.default_radius

        # Interaction state
        self.is_grabbed: bool = False
        self.is_hovered: bool = False
        self.grab_offset_x: float = 0.0
        self.grab_offset_y: float = 0.0

        # Smoothers
        self._pos_filter = PointFilter(mincutoff=1.5, beta=0.04)
        self._radius_filter = OneEuroFilter(mincutoff=1.0, beta=0.03)

        self.time_start = time.perf_counter()
        self.last_update = time.perf_counter()

    def reset_position(self) -> None:
        """Centers orb in the viewport."""
        self.x = self.w * 0.5
        self.y = self.h * 0.5
        self.rest_x = self.x
        self.rest_y = self.y
        self.vx = 0.0
        self.vy = 0.0
        self.is_grabbed = False
        self.is_hovered = False
        self._pos_filter.reset()

    def resize_viewport(self, width: int, height: int) -> None:
        """Updates boundary dimensions if camera resolution changes."""
        self.w = width
        self.h = height

    def _constrain_to_viewport(self) -> None:
        """Ensures the orb remains strictly within visible screen boundaries."""
        margin = max(15.0, self.current_radius * 1.1)
        min_x = margin
        max_x = max(min_x, self.w - margin)
        min_y = margin
        max_y = max(min_y, self.h - margin)

        self.x = max(min_x, min(max_x, self.x))
        self.y = max(min_y, min(max_y, self.y))

    def update(
        self,
        hand_data: Optional[HandData],
        dt: Optional[float] = None,
    ) -> Tuple[float, float, float]:
        """Updates orb kinematics, size, and interaction state.

        Returns
        -------
        (x, y, radius) current orb spatial parameters.
        """
        now = time.perf_counter()
        if dt is None:
            dt = max(0.001, min(0.1, now - self.last_update))
        self.last_update = now
        elapsed = now - self.time_start

        # 1. Update Target Radius from Hand Openness
        if hand_data is not None:
            # Map openness [0.0, 1.0] -> [min_radius, max_radius]
            target_r = self.min_radius + hand_data.openness * (self.max_radius - self.min_radius)
        else:
            # Gradually relax back to default radius when no hand is present
            target_r = self.default_radius

        # Smooth radius transitions
        self.current_radius = float(self._radius_filter.filter(target_r, timestamp=now))

        # 2. Check Hover and Grab Interaction
        if hand_data is not None:
            pinch_x, pinch_y = hand_data.pinch_point_px
            dist_to_orb = math.hypot(pinch_x - self.x, pinch_y - self.y)

            # Grab threshold: proportional to orb size plus palm threshold
            grab_reach = max(self.current_radius * 1.5, 45.0)
            self.is_hovered = dist_to_orb <= grab_reach

            # State Transition: Enter Grab
            if not self.is_grabbed:
                if hand_data.is_pinching and self.is_hovered:
                    self.is_grabbed = True
                    self.grab_offset_x = self.x - pinch_x
                    self.grab_offset_y = self.y - pinch_y
                    if self.on_grab:
                        self.on_grab(self.x, self.y, self.current_radius)

            # State Transition: Maintain or Release Grab
            if self.is_grabbed:
                if not hand_data.is_pinching:
                    # Released!
                    self.is_grabbed = False
                    self.rest_x = self.x
                    self.rest_y = self.y
                    if self.on_release:
                        self.on_release(self.x, self.y, self.current_radius)
                else:
                    # Follow hand pinch position with responsive spring follow
                    target_x = pinch_x + self.grab_offset_x * 0.5
                    target_y = pinch_y + self.grab_offset_y * 0.5

                    # Smooth follow
                    filtered_pos = self._pos_filter.filter_pt((target_x, target_y), timestamp=now)
                    self.x = filtered_pos[0]
                    self.y = filtered_pos[1]
                    self.rest_x = self.x
                    self.rest_y = self.y
                    self.vx = 0.0
                    self.vy = 0.0
        else:
            # If hand was lost while grabbed, safely release
            if self.is_grabbed:
                self.is_grabbed = False
                self.rest_x = self.x
                self.rest_y = self.y
                if self.on_release:
                    self.on_release(self.x, self.y, self.current_radius)
            self.is_hovered = False

        # 3. Ambient Floating Dynamics when NOT grabbed
        if not self.is_grabbed:
            # Harmonic ambient levitation
            bob_y = math.sin(elapsed * 2.2) * 5.5
            bob_x = math.cos(elapsed * 1.1) * 2.5

            # Smoothly settle toward resting anchor point
            damping = 8.0
            self.vx = (self.rest_x + bob_x - self.x) * damping
            self.vy = (self.rest_y + bob_y - self.y) * damping

            self.x += self.vx * dt
            self.y += self.vy * dt

        # 4. Viewport Boundary Confinement
        self._constrain_to_viewport()

        return self.x, self.y, self.current_radius

    def get_state_label(self, hand_detected: bool) -> str:
        """Returns human-readable state string for HUD."""
        if self.is_grabbed:
            return "GRABBED [PINCH]"
        if not hand_detected:
            return "FLOATING (NO HAND)"
        if self.is_hovered:
            return "HOVER (PINCH TO GRAB)"
        return "TRACKING (REACH FOR ORB)"
