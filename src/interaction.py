"""Orb State Machine, Kinematics, and Hand Interaction.

Coordinates orb states (Floating, Hovered, Grabbed, Released),
spring-damper physics, smooth radius scaling via hand openness,
and viewport boundary constraints.
"""

import math
import time
from typing import Callable, List, Optional, Tuple, Union
from src.filters import EMAFilter, OneEuroFilter, PointFilter
from src.gestures import (
    compute_two_hand_angle,
    compute_two_hand_distance,
    compute_two_hand_midpoint,
    unwrap_angle_delta,
)
from src.hand_tracker import HandData


class OrbController:
    """Controls position, size, rotation, and interaction dynamics of holographic objects."""

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

        # Radius & Transform state
        self.current_radius: float = self.default_radius
        self.target_radius: float = self.default_radius
        self.rotation: float = 0.0  # Filtered rotation in radians
        self.raw_rotation: float = 0.0  # Unfiltered accumulated rotation in radians
        self.two_hand_scale: float = 1.0  # Relative scale multiplier
        self.two_hand_transformed: bool = False

        # Interaction mode: "NO_HANDS", "SINGLE_HAND", "TWO_HANDS"
        self.interaction_mode: str = "NO_HANDS"

        # Two-hand reference baselines (captured at moment of entry to prevent jumps)
        self.ref_two_hand_distance: Optional[float] = None
        self.ref_two_hand_angle: Optional[float] = None
        self.prev_two_hand_angle: Optional[float] = None
        self.base_radius: float = self.default_radius
        self.base_rotation: float = 0.0
        self.two_hand_offset_x: float = 0.0
        self.two_hand_offset_y: float = 0.0

        # Interaction state
        self.is_grabbed: bool = False
        self.is_hovered: bool = False
        self.grab_offset_x: float = 0.0
        self.grab_offset_y: float = 0.0

        # Single-hand smoothers
        self._pos_filter = PointFilter(mincutoff=1.5, beta=0.04)
        self._radius_filter = OneEuroFilter(mincutoff=1.0, beta=0.03)

        # Two-hand smoothers (low jitter, responsive feel)
        self._two_hand_scale_filter = OneEuroFilter(mincutoff=1.0, beta=0.04)
        self._two_hand_rot_filter = OneEuroFilter(mincutoff=1.2, beta=0.05)
        self._two_hand_pos_filter = PointFilter(mincutoff=1.5, beta=0.04)

        self.time_start = time.perf_counter()
        self.last_update = time.perf_counter()

    def reset_position(self) -> None:
        """Centers object in the viewport and resets transform offsets."""
        self.x = self.w * 0.5
        self.y = self.h * 0.5
        self.rest_x = self.x
        self.rest_y = self.y
        self.vx = 0.0
        self.vy = 0.0
        self.rotation = 0.0
        self.raw_rotation = 0.0
        self.two_hand_scale = 1.0
        self.two_hand_transformed = False
        self.is_grabbed = False
        self.is_hovered = False
        self.interaction_mode = "NO_HANDS"
        self.ref_two_hand_distance = None
        self.ref_two_hand_angle = None
        self.prev_two_hand_angle = None
        self._pos_filter.reset()
        self._radius_filter.reset()
        self._two_hand_scale_filter.reset()
        self._two_hand_rot_filter.reset()
        self._two_hand_pos_filter.reset()

    def resize_viewport(self, width: int, height: int) -> None:
        """Updates boundary dimensions if camera resolution changes."""
        self.w = width
        self.h = height

    def _constrain_to_viewport(self) -> None:
        """Ensures the object remains strictly within visible screen boundaries."""
        margin = max(15.0, self.current_radius * 1.1)
        min_x = margin
        max_x = max(min_x, self.w - margin)
        min_y = margin
        max_y = max(min_y, self.h - margin)

        self.x = max(min_x, min(max_x, self.x))
        self.y = max(min_y, min(max_y, self.y))

    def update(
        self,
        hands: Union[Optional[HandData], List[HandData]] = None,
        dt: Optional[float] = None,
    ) -> Tuple[float, float, float]:
        """Updates object kinematics, two-hand scale/rotation, and interaction state.

        Parameters
        ----------
        hands : Single HandData, list of HandData, or None.
        dt : Delta time in seconds.

        Returns
        -------
        (x, y, radius) current object spatial parameters.
        """
        now = time.perf_counter()
        if dt is None:
            dt = max(0.001, min(0.1, now - self.last_update))
        self.last_update = now
        elapsed = now - self.time_start

        # Normalize hands input into a list of valid HandData objects
        if hands is None:
            hand_list: List[HandData] = []
        elif isinstance(hands, HandData):
            hand_list = [hands]
        elif isinstance(hands, list):
            hand_list = [h for h in hands if h is not None]
        else:
            hand_list = []

        num_hands = len(hand_list)

        # ---------------------------------------------------------------------
        # Case A: TWO HANDS (Simultaneous Scale + Rotation)
        # ---------------------------------------------------------------------
        if num_hands >= 2:
            hand_a, hand_b = hand_list[0], hand_list[1]

            # Establish persistent left/right hand identity to avoid polar flips
            if hand_a.handedness != hand_b.handedness and "Left" in (hand_a.handedness, hand_b.handedness):
                h_left = hand_a if hand_a.handedness == "Left" else hand_b
                h_right = hand_b if hand_b.handedness == "Right" else hand_a
            else:
                # Fallback to screen X coordinate
                if hand_a.palm_center_px[0] <= hand_b.palm_center_px[0]:
                    h_left, h_right = hand_a, hand_b
                else:
                    h_left, h_right = hand_b, hand_a

            pt_a = h_left.palm_center_px
            pt_b = h_right.palm_center_px

            curr_dist = compute_two_hand_distance(pt_a, pt_b)
            curr_angle = compute_two_hand_angle(pt_a, pt_b)
            mid = compute_two_hand_midpoint(pt_a, pt_b)

            # State Transition: Enter TWO_HANDS mode smoothly (Zero Instant Jump)
            if self.interaction_mode != "TWO_HANDS":
                self.interaction_mode = "TWO_HANDS"
                self.two_hand_transformed = True
                self.ref_two_hand_distance = max(20.0, curr_dist)
                self.ref_two_hand_angle = curr_angle
                self.prev_two_hand_angle = curr_angle
                self.base_radius = self.current_radius
                self.base_rotation = self.rotation
                self.raw_rotation = self.rotation
                self.two_hand_offset_x = self.x - mid[0]
                self.two_hand_offset_y = self.y - mid[1]
                self.two_hand_scale = self.current_radius / max(1.0, self.default_radius)
                if self.is_grabbed:
                    self.is_grabbed = False
                self._two_hand_scale_filter.reset()
                self._two_hand_rot_filter.reset()
                self._two_hand_pos_filter.reset()

            # 1. Scale from Hand Distance
            ref_dist = max(20.0, self.ref_two_hand_distance or curr_dist)
            raw_scale_ratio = curr_dist / ref_dist
            target_r = self.base_radius * raw_scale_ratio
            # Sensible clamping bounds: allow scaling from 60% of min up to 160% of max
            clamped_r = max(self.min_radius * 0.6, min(self.max_radius * 1.6, target_r))
            self.current_radius = float(self._two_hand_scale_filter.filter(clamped_r, timestamp=now))
            self.target_radius = self.current_radius
            self.two_hand_scale = self.current_radius / max(1.0, self.default_radius)

            # 2. Rotation from Hand Angle (with unwrapping across +/- 180 deg)
            prev_ang = self.prev_two_hand_angle if self.prev_two_hand_angle is not None else curr_angle
            angle_delta = unwrap_angle_delta(curr_angle, prev_ang)
            self.prev_two_hand_angle = curr_angle

            self.raw_rotation += angle_delta
            self.rotation = float(self._two_hand_rot_filter.filter(self.raw_rotation, timestamp=now))

            # 3. Position follows Two-Hand Midpoint
            target_x = mid[0] + self.two_hand_offset_x
            target_y = mid[1] + self.two_hand_offset_y
            filtered_pos = self._two_hand_pos_filter.filter_pt((target_x, target_y), timestamp=now)
            self.x = filtered_pos[0]
            self.y = filtered_pos[1]
            self.rest_x = self.x
            self.rest_y = self.y
            self.vx = 0.0
            self.vy = 0.0
            self.is_hovered = True

        # ---------------------------------------------------------------------
        # Case B: ONE HAND (Existing Pinch Grab + Position Follow)
        # ---------------------------------------------------------------------
        elif num_hands == 1:
            hand_data = hand_list[0]

            # State Transition: Exit TWO_HANDS into SINGLE_HAND (Preserve Transform)
            if self.interaction_mode == "TWO_HANDS":
                self.interaction_mode = "SINGLE_HAND"
                self.ref_two_hand_distance = None
                self.ref_two_hand_angle = None
                self.prev_two_hand_angle = None
                self.raw_rotation = self.rotation
                self.target_radius = self.current_radius
                self._radius_filter.reset()
            else:
                self.interaction_mode = "SINGLE_HAND"

            # Radius update: if scaled by two-hand mode, preserve scale; otherwise use hand openness
            if self.two_hand_transformed:
                self.target_radius = self.current_radius
            else:
                target_r = self.min_radius + hand_data.openness * (self.max_radius - self.min_radius)
                self.current_radius = float(self._radius_filter.filter(target_r, timestamp=now))

            # 2. Check Hover and Grab Interaction
            pinch_x, pinch_y = hand_data.pinch_point_px
            dist_to_obj = math.hypot(pinch_x - self.x, pinch_y - self.y)
            grab_reach = max(self.current_radius * 1.5, 45.0)
            self.is_hovered = dist_to_obj <= grab_reach

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
                    self.is_grabbed = False
                    self.rest_x = self.x
                    self.rest_y = self.y
                    if self.on_release:
                        self.on_release(self.x, self.y, self.current_radius)
                else:
                    # Follow hand pinch position
                    target_x = pinch_x + self.grab_offset_x * 0.5
                    target_y = pinch_y + self.grab_offset_y * 0.5
                    filtered_pos = self._pos_filter.filter_pt((target_x, target_y), timestamp=now)
                    self.x = filtered_pos[0]
                    self.y = filtered_pos[1]
                    self.rest_x = self.x
                    self.rest_y = self.y
                    self.vx = 0.0
                    self.vy = 0.0

        # ---------------------------------------------------------------------
        # Case C: NO HANDS (Ambient Floating, Preserve Final Transform)
        # ---------------------------------------------------------------------
        else:
            if self.interaction_mode == "TWO_HANDS":
                self.ref_two_hand_distance = None
                self.ref_two_hand_angle = None
                self.prev_two_hand_angle = None

            if self.is_grabbed:
                self.is_grabbed = False
                self.rest_x = self.x
                self.rest_y = self.y
                if self.on_release:
                    self.on_release(self.x, self.y, self.current_radius)

            self.interaction_mode = "NO_HANDS"
            self.is_hovered = False

            # Relax radius smoothly back toward default
            self.current_radius = float(self._radius_filter.filter(self.default_radius, timestamp=now))

        # ---------------------------------------------------------------------
        # Ambient Floating Dynamics when NOT grabbed and NOT in two-hand mode
        # ---------------------------------------------------------------------
        if not self.is_grabbed and self.interaction_mode != "TWO_HANDS":
            bob_y = math.sin(elapsed * 2.2) * 5.5
            bob_x = math.cos(elapsed * 1.1) * 2.5
            damping = 8.0
            self.vx = (self.rest_x + bob_x - self.x) * damping
            self.vy = (self.rest_y + bob_y - self.y) * damping
            self.x += self.vx * dt
            self.y += self.vy * dt

        # Viewport Boundary Confinement
        self._constrain_to_viewport()

        return self.x, self.y, self.current_radius

    def get_state_label(self, hand_detected: bool = False) -> str:
        """Returns human-readable state string for HUD."""
        if self.interaction_mode == "TWO_HANDS":
            rot_deg = int(math.degrees(self.rotation))
            return f"TWO-HAND [S:{self.two_hand_scale:.2f}x R:{rot_deg:+d}deg]"
        if self.is_grabbed:
            return "GRABBED [PINCH]"
        if not hand_detected or self.interaction_mode == "NO_HANDS":
            return "FLOATING (NO HAND)"
        if self.is_hovered:
            return "HOVER (PINCH TO GRAB)"
        return "TRACKING (REACH FOR OBJECT)"

