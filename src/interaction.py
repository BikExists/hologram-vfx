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
    InteractionMode,
    compute_hand_orientation,
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
        on_theme_change: Optional[Callable[[str], None]] = None,
        initial_theme: str = "cyan",
        initial_mode: InteractionMode = InteractionMode.STANDARD,
    ):
        self.w = frame_width
        self.h = frame_height

        self.min_radius = float(min_radius)
        self.max_radius = float(max_radius)
        self.default_radius = float(default_radius)

        # Callbacks for VFX events (e.g. shockwaves, sound, theme change)
        self.on_grab = on_grab
        self.on_release = on_release
        self.on_theme_change = on_theme_change
        self.current_theme_key: str = initial_theme

        # User-selected interaction mode: InteractionMode.STANDARD or InteractionMode.INDEPENDENT
        self.selected_mode: InteractionMode = initial_mode

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

        # Active interaction mode state: "NO_HANDS", "SINGLE_HAND", "TWO_HANDS", "INDEPENDENT_DUAL_HAND"
        self.interaction_mode: str = "NO_HANDS"

        # Standard two-hand reference baselines (captured at moment of entry)
        self.ref_two_hand_distance: Optional[float] = None
        self.ref_two_hand_angle: Optional[float] = None
        self.prev_two_hand_angle: Optional[float] = None
        self.base_radius: float = self.default_radius
        self.base_rotation: float = 0.0
        self.two_hand_offset_x: float = 0.0
        self.two_hand_offset_y: float = 0.0

        # Independent dual-hand reference baselines
        self.primary_offset_x: float = 0.0
        self.primary_offset_y: float = 0.0
        self.prev_primary_angle: Optional[float] = None
        self.ref_secondary_openness: Optional[float] = None
        self.prev_secondary_angle: Optional[float] = None
        self.accum_secondary_angle: float = 0.0
        self.base_theme_idx: int = 0
        self.last_theme_step: int = 0

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

    def cycle_interaction_mode(self) -> InteractionMode:
        """Cycles between STANDARD and INDEPENDENT interaction modes."""
        if self.selected_mode == InteractionMode.STANDARD:
            self.selected_mode = InteractionMode.INDEPENDENT
        else:
            self.selected_mode = InteractionMode.STANDARD
        self._reset_mode_baselines()
        self.interaction_mode = "MODE_SWITCH"
        return self.selected_mode

    def get_mode_display_name(self) -> str:
        """Returns human-readable name of the selected interaction mode."""
        if self.selected_mode == InteractionMode.INDEPENDENT:
            return "INDEPENDENT DUAL-HAND"
        return "STANDARD 2-HAND"

    def _reset_mode_baselines(self) -> None:
        """Resets mode-specific baseline captures to prevent sudden jumps."""
        self.ref_two_hand_distance = None
        self.ref_two_hand_angle = None
        self.prev_two_hand_angle = None
        self.primary_offset_x = 0.0
        self.primary_offset_y = 0.0
        self.prev_primary_angle = None
        self.ref_secondary_openness = None
        self.prev_secondary_angle = None
        self.accum_secondary_angle = 0.0
        self.last_theme_step = 0

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
        self._reset_mode_baselines()
        self._pos_filter.reset()
        self._radius_filter.reset()
        self._two_hand_scale_filter.reset()
        self._two_hand_rot_filter.reset()
        self._two_hand_pos_filter.reset()

    def resize_viewport(self, width: int, height: int) -> None:
        """Updates boundary dimensions and preserves normalized spatial placement."""
        if width <= 0 or height <= 0:
            return

        old_w = self.w
        old_h = self.h
        self.w = width
        self.h = height
        self.rest_x = width * 0.5
        self.rest_y = height * 0.5

        if old_w > 0 and old_h > 0 and (old_w != width or old_h != height):
            # Preserve normalized spatial placement across resolution changes
            x_normalized = self.x / float(old_w)
            y_normalized = self.y / float(old_h)
            self.x = x_normalized * float(width)
            self.y = y_normalized * float(height)

            # Re-anchor position filters to prevent spring velocity jerk
            self._pos_filter.reset()
            self._two_hand_pos_filter.reset()

        self._constrain_to_viewport()

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

    def _assign_hands(
        self, hand_list: List[HandData]
    ) -> Tuple[Optional[HandData], Optional[HandData]]:
        """Deterministically assigns primary and secondary hands.

        Primary Hand: Left hand (controls position + rotation).
        Secondary Hand: Right hand (controls scale + theme).
        Fallback when handedness is unavailable/identical: Leftmost on screen = Primary.
        """
        if not hand_list:
            return None, None
        if len(hand_list) == 1:
            return hand_list[0], None

        h0, h1 = hand_list[0], hand_list[1]
        if (
            h0.handedness != h1.handedness
            and "Left" in (h0.handedness, h1.handedness)
            and "Right" in (h0.handedness, h1.handedness)
        ):
            primary = h0 if h0.handedness == "Left" else h1
            secondary = h1 if h1.handedness == "Right" else h0
            return primary, secondary

        # Fallback to horizontal screen X coordinate
        if h0.palm_center_px[0] <= h1.palm_center_px[0]:
            return h0, h1
        return h1, h0

    def _update_standard_two_hand(
        self,
        h_left: HandData,
        h_right: HandData,
        now: float,
        dt: float,
    ) -> None:
        """Standard Two-Hand Transform mode: Distance -> Scale, Angle -> Rotation, Midpoint -> Position."""
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

    def _update_independent_dual_hand(
        self,
        primary_hand: HandData,
        secondary_hand: HandData,
        now: float,
        dt: float,
    ) -> None:
        """Independent Dual-Hand Control mode:

        Primary Hand: Movement -> Position, Orientation -> Rotation.
        Secondary Hand: Openness -> Scale, Orientation -> Theme/Color.
        """
        curr_prim_angle = compute_hand_orientation(primary_hand.landmarks_px)
        curr_sec_angle = compute_hand_orientation(secondary_hand.landmarks_px)

        # State Transition: Enter INDEPENDENT_DUAL_HAND smoothly (Zero Instant Jump)
        if self.interaction_mode != "INDEPENDENT_DUAL_HAND":
            self.interaction_mode = "INDEPENDENT_DUAL_HAND"
            self.two_hand_transformed = True

            # Primary hand baselines (Position & Rotation)
            self.primary_offset_x = self.x - primary_hand.palm_center_px[0]
            self.primary_offset_y = self.y - primary_hand.palm_center_px[1]
            self.prev_primary_angle = curr_prim_angle
            self.raw_rotation = self.rotation
            self.base_rotation = self.rotation

            # Secondary hand baselines (Scale & Theme)
            self.ref_secondary_openness = secondary_hand.openness
            self.base_radius = self.current_radius
            self.prev_secondary_angle = curr_sec_angle
            self.accum_secondary_angle = 0.0
            self.last_theme_step = 0
            from src.vfx.color_themes import THEME_KEYS
            self.base_theme_idx = (
                THEME_KEYS.index(self.current_theme_key)
                if self.current_theme_key in THEME_KEYS
                else 0
            )

            if self.is_grabbed:
                self.is_grabbed = False
            self._two_hand_scale_filter.reset()
            self._two_hand_rot_filter.reset()
            self._pos_filter.reset()

        # 1. Primary Hand Movement -> Position
        target_x = primary_hand.palm_center_px[0] + self.primary_offset_x
        target_y = primary_hand.palm_center_px[1] + self.primary_offset_y
        filtered_pos = self._pos_filter.filter_pt((target_x, target_y), timestamp=now)
        self.x = filtered_pos[0]
        self.y = filtered_pos[1]
        self.rest_x = self.x
        self.rest_y = self.y
        self.vx = 0.0
        self.vy = 0.0
        self.is_hovered = True

        # 2. Primary Hand Orientation -> Rotation
        prev_prim = (
            self.prev_primary_angle
            if self.prev_primary_angle is not None
            else curr_prim_angle
        )
        angle_delta = unwrap_angle_delta(curr_prim_angle, prev_prim)
        self.prev_primary_angle = curr_prim_angle
        self.raw_rotation += angle_delta
        self.rotation = float(
            self._two_hand_rot_filter.filter(self.raw_rotation, timestamp=now)
        )

        # 3. Secondary Hand Openness -> Scale
        ref_open = (
            self.ref_secondary_openness
            if self.ref_secondary_openness is not None
            else secondary_hand.openness
        )
        open_delta = secondary_hand.openness - ref_open
        target_r = self.base_radius + open_delta * (self.max_radius - self.min_radius)
        clamped_r = max(self.min_radius * 0.6, min(self.max_radius * 1.6, target_r))
        self.current_radius = float(
            self._two_hand_scale_filter.filter(clamped_r, timestamp=now)
        )
        self.target_radius = self.current_radius
        self.two_hand_scale = self.current_radius / max(1.0, self.default_radius)

        # 4. Secondary Hand Orientation -> Theme/Color (with deadband hysteresis)
        prev_sec = (
            self.prev_secondary_angle
            if self.prev_secondary_angle is not None
            else curr_sec_angle
        )
        delta_sec = unwrap_angle_delta(curr_sec_angle, prev_sec)
        self.prev_secondary_angle = curr_sec_angle
        self.accum_secondary_angle += delta_sec

        from src.vfx.color_themes import THEME_KEYS
        sector_width = math.pi * 0.5  # 90 degrees
        hysteresis = 0.15  # ~8.6 degrees deadband
        k = self.last_theme_step
        upper_bound = (k + 0.5) * sector_width + hysteresis
        lower_bound = (k - 0.5) * sector_width - hysteresis

        if self.accum_secondary_angle > upper_bound:
            k += int((self.accum_secondary_angle - upper_bound) / sector_width) + 1
        elif self.accum_secondary_angle < lower_bound:
            k -= int((lower_bound - self.accum_secondary_angle) / sector_width) + 1

        if k != self.last_theme_step:
            self.last_theme_step = k
            target_theme_idx = (self.base_theme_idx + k) % len(THEME_KEYS)
            new_theme_key = THEME_KEYS[target_theme_idx]
            if new_theme_key != self.current_theme_key:
                self.current_theme_key = new_theme_key
                if self.on_theme_change:
                    self.on_theme_change(new_theme_key)

    def update(
        self,
        hands: Union[Optional[HandData], List[HandData]] = None,
        dt: Optional[float] = None,
    ) -> Tuple[float, float, float]:
        """Updates object kinematics, transform state, and interaction dynamics."""
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
        # Case A: TWO HANDS
        # ---------------------------------------------------------------------
        if num_hands >= 2:
            primary, secondary = self._assign_hands(hand_list)
            if self.selected_mode == InteractionMode.INDEPENDENT:
                self._update_independent_dual_hand(primary, secondary, now, dt)
            else:
                self._update_standard_two_hand(primary, secondary, now, dt)

        # ---------------------------------------------------------------------
        # Case B: ONE HAND
        # ---------------------------------------------------------------------
        elif num_hands == 1:
            hand_data = hand_list[0]

            # State Transition: Exit TWO_HANDS or INDEPENDENT into SINGLE_HAND (Preserve Transform)
            if self.interaction_mode in ("TWO_HANDS", "INDEPENDENT_DUAL_HAND"):
                self.interaction_mode = "SINGLE_HAND"
                self.ref_two_hand_distance = None
                self.ref_two_hand_angle = None
                self.prev_two_hand_angle = None
                self.ref_secondary_openness = None
                self.prev_secondary_angle = None
                self.accum_secondary_angle = 0.0
                self.raw_rotation = self.rotation
                self.target_radius = self.current_radius
                self._radius_filter.reset()
                # Anchor primary position and orientation seamlessly
                self.primary_offset_x = self.x - hand_data.palm_center_px[0]
                self.primary_offset_y = self.y - hand_data.palm_center_px[1]
                self.prev_primary_angle = compute_hand_orientation(hand_data.landmarks_px)
            else:
                self.interaction_mode = "SINGLE_HAND"

            if self.selected_mode == InteractionMode.INDEPENDENT:
                # In Independent mode, single remaining hand acts as primary controller
                if self.prev_primary_angle is None:
                    self.primary_offset_x = self.x - hand_data.palm_center_px[0]
                    self.primary_offset_y = self.y - hand_data.palm_center_px[1]
                    self.prev_primary_angle = compute_hand_orientation(hand_data.landmarks_px)

                # Primary movement -> position
                target_x = hand_data.palm_center_px[0] + self.primary_offset_x
                target_y = hand_data.palm_center_px[1] + self.primary_offset_y
                filtered_pos = self._pos_filter.filter_pt((target_x, target_y), timestamp=now)
                self.x, self.y = filtered_pos[0], filtered_pos[1]
                self.rest_x, self.rest_y = self.x, self.y
                self.vx, self.vy = 0.0, 0.0

                # Primary orientation -> rotation
                curr_prim_angle = compute_hand_orientation(hand_data.landmarks_px)
                angle_delta = unwrap_angle_delta(curr_prim_angle, self.prev_primary_angle)
                self.prev_primary_angle = curr_prim_angle
                self.raw_rotation += angle_delta
                self.rotation = float(
                    self._two_hand_rot_filter.filter(self.raw_rotation, timestamp=now)
                )

                # Scale and theme preserved
                self.target_radius = self.current_radius
                self.is_hovered = True

                # Check pinch for grab callbacks
                if hand_data.is_pinching and not self.is_grabbed:
                    self.is_grabbed = True
                    if self.on_grab:
                        self.on_grab(self.x, self.y, self.current_radius)
                elif not hand_data.is_pinching and self.is_grabbed:
                    self.is_grabbed = False
                    if self.on_release:
                        self.on_release(self.x, self.y, self.current_radius)

            else:
                # Standard mode single-hand behavior
                if self.two_hand_transformed:
                    self.target_radius = self.current_radius
                else:
                    target_r = self.min_radius + hand_data.openness * (self.max_radius - self.min_radius)
                    self.current_radius = float(self._radius_filter.filter(target_r, timestamp=now))

                # Check Hover and Grab Interaction
                pinch_x, pinch_y = hand_data.pinch_point_px
                dist_to_obj = math.hypot(pinch_x - self.x, pinch_y - self.y)
                grab_reach = max(self.current_radius * 1.5, 45.0)
                self.is_hovered = dist_to_obj <= grab_reach

                if not self.is_grabbed:
                    if hand_data.is_pinching and self.is_hovered:
                        self.is_grabbed = True
                        self.grab_offset_x = self.x - pinch_x
                        self.grab_offset_y = self.y - pinch_y
                        if self.on_grab:
                            self.on_grab(self.x, self.y, self.current_radius)

                if self.is_grabbed:
                    if not hand_data.is_pinching:
                        self.is_grabbed = False
                        self.rest_x = self.x
                        self.rest_y = self.y
                        if self.on_release:
                            self.on_release(self.x, self.y, self.current_radius)
                    else:
                        target_x = pinch_x + self.grab_offset_x * 0.5
                        target_y = pinch_y + self.grab_offset_y * 0.5
                        filtered_pos = self._pos_filter.filter_pt((target_x, target_y), timestamp=now)
                        self.x, self.y = filtered_pos[0], filtered_pos[1]
                        self.rest_x, self.rest_y = self.x, self.y
                        self.vx, self.vy = 0.0, 0.0

        # ---------------------------------------------------------------------
        # Case C: NO HANDS (Ambient Floating, Preserve Final Transform)
        # ---------------------------------------------------------------------
        else:
            if self.interaction_mode in ("TWO_HANDS", "INDEPENDENT_DUAL_HAND"):
                self._reset_mode_baselines()

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
        if not self.is_grabbed and self.interaction_mode not in ("TWO_HANDS", "INDEPENDENT_DUAL_HAND"):
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
        if self.interaction_mode == "INDEPENDENT_DUAL_HAND":
            rot_deg = int(math.degrees(self.rotation))
            return f"INDEP-DUAL [S:{self.two_hand_scale:.2f}x R:{rot_deg:+d}deg]"
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

