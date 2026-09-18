"""Common Holographic Object contract and abstract base definition.

Defines the unified interface for all holographic objects (Orb, Cube, Planet)
operating strictly in pixel coordinates for consistent kinematics, interaction,
viewport constraints, theme propagation, and visual compositing.
"""

from abc import ABC, abstractmethod
from typing import Callable, List, Optional, Tuple, Union
import numpy as np

from src.gestures import InteractionMode
from src.hand_tracker import HandData
from src.interaction import OrbController
from src.vfx.color_themes import ColorTheme, THEMES, get_theme


class BaseHolographicObject(ABC):
    """Abstract base class establishing the common contract for holographic objects."""

    def __init__(
        self,
        name: str,
        frame_width: int = 640,
        frame_height: int = 480,
        theme_name: str = "cyan",
        min_radius: float = 28.0,
        max_radius: float = 125.0,
        default_radius: float = 55.0,
        on_grab: Optional[Callable[[float, float, float], None]] = None,
        on_release: Optional[Callable[[float, float, float], None]] = None,
    ):
        self.name: str = name
        self.w: int = frame_width
        self.h: int = frame_height
        self._theme: ColorTheme = get_theme(theme_name)

        # Core kinematics controller handling spring follow, OneEuro smoothing, and boundary confinement
        self.controller = OrbController(
            frame_width=frame_width,
            frame_height=frame_height,
            min_radius=min_radius,
            max_radius=max_radius,
            default_radius=default_radius,
            on_grab=on_grab or self._internal_on_grab,
            on_release=on_release or self._internal_on_release,
            on_theme_change=self.set_theme,
            initial_theme=theme_name,
        )

    # -------------------------------------------------------------------------
    # Spatial State Properties (All in Frame Pixel Coordinates)
    # -------------------------------------------------------------------------

    @property
    def x(self) -> float:
        """Center X position in pixel coordinates."""
        return self.controller.x

    @x.setter
    def x(self, value: float) -> None:
        self.controller.x = float(value)
        self.controller.rest_x = float(value)

    @property
    def y(self) -> float:
        """Center Y position in pixel coordinates."""
        return self.controller.y

    @y.setter
    def y(self, value: float) -> None:
        self.controller.y = float(value)
        self.controller.rest_y = float(value)

    @property
    def current_radius(self) -> float:
        """Current bounding radius / scale in pixel coordinates."""
        return self.controller.current_radius

    @current_radius.setter
    def current_radius(self, value: float) -> None:
        self.controller.current_radius = float(value)
        self.controller.target_radius = float(value)

    @property
    def is_grabbed(self) -> bool:
        """True if user is actively pinching and holding the object."""
        return self.controller.is_grabbed

    @is_grabbed.setter
    def is_grabbed(self, value: bool) -> None:
        self.controller.is_grabbed = bool(value)

    @property
    def is_hovered(self) -> bool:
        """True if user's hand is in proximity to the object."""
        return self.controller.is_hovered

    @property
    def rotation(self) -> float:
        """Current rotation angle in radians."""
        return self.controller.rotation

    @rotation.setter
    def rotation(self, value: float) -> None:
        self.controller.rotation = float(value)

    @property
    def two_hand_scale(self) -> float:
        """Relative scale multiplier derived from two-hand distance."""
        return self.controller.two_hand_scale

    @property
    def interaction_mode(self) -> str:
        """Current interaction mode ('NO_HANDS', 'SINGLE_HAND', 'TWO_HANDS', 'INDEPENDENT_DUAL_HAND')."""
        return self.controller.interaction_mode

    @property
    def selected_mode(self) -> InteractionMode:
        """User-selected interaction mode (STANDARD or INDEPENDENT)."""
        return self.controller.selected_mode

    @selected_mode.setter
    def selected_mode(self, mode: InteractionMode) -> None:
        self.controller.selected_mode = mode

    def cycle_interaction_mode(self) -> InteractionMode:
        """Cycles between STANDARD and INDEPENDENT interaction modes."""
        return self.controller.cycle_interaction_mode()

    def get_mode_display_name(self) -> str:
        """Human-readable display name for selected interaction mode."""
        return self.controller.get_mode_display_name()

    @property
    def theme(self) -> ColorTheme:
        """Active color theme."""
        return self._theme

    # -------------------------------------------------------------------------
    # Lifecycle, Viewport, and State Management
    # -------------------------------------------------------------------------

    def set_theme(self, theme_or_name: Union[str, ColorTheme]) -> None:
        """Updates color palette."""
        if isinstance(theme_or_name, ColorTheme):
            self._theme = theme_or_name
            for k, v in THEMES.items():
                if v == theme_or_name or v.name == theme_or_name.name:
                    self.controller.current_theme_key = k
                    break
        else:
            self._theme = get_theme(str(theme_or_name))
            self.controller.current_theme_key = str(theme_or_name)

    def resize_viewport(self, width: int, height: int) -> None:
        """Adapts boundary dimensions and rest anchor when camera resolution changes."""
        self.w = width
        self.h = height
        self.controller.resize_viewport(width, height)

    def reset_position(self) -> None:
        """Centers object in the viewport."""
        self.controller.reset_position()

    def transfer_state_from(self, other: "BaseHolographicObject") -> None:
        """Seamlessly inherits spatial position, scale, velocity, rotation, mode, and theme from another object."""
        self.controller.x = other.controller.x
        self.controller.y = other.controller.y
        self.controller.rest_x = other.controller.rest_x
        self.controller.rest_y = other.controller.rest_y
        self.controller.vx = other.controller.vx
        self.controller.vy = other.controller.vy
        self.controller.current_radius = other.controller.current_radius
        self.controller.target_radius = other.controller.target_radius
        self.controller.rotation = other.controller.rotation
        self.controller.raw_rotation = other.controller.raw_rotation
        self.controller.two_hand_scale = other.controller.two_hand_scale
        self.controller.selected_mode = other.controller.selected_mode
        self.controller.interaction_mode = other.controller.interaction_mode
        self.controller.is_grabbed = other.controller.is_grabbed
        self.controller.grab_offset_x = other.controller.grab_offset_x
        self.controller.grab_offset_y = other.controller.grab_offset_y
        self.controller.primary_offset_x = other.controller.primary_offset_x
        self.controller.primary_offset_y = other.controller.primary_offset_y
        self.controller.prev_primary_angle = other.controller.prev_primary_angle
        self.controller.ref_secondary_openness = other.controller.ref_secondary_openness
        self.controller.prev_secondary_angle = other.controller.prev_secondary_angle
        self.controller.accum_secondary_angle = other.controller.accum_secondary_angle
        self.controller.base_theme_idx = other.controller.base_theme_idx
        self.controller.last_theme_step = other.controller.last_theme_step
        self.controller.current_theme_key = other.controller.current_theme_key
        self.set_theme(other.theme)
        self.resize_viewport(other.w, other.h)

    def get_state_label(self, hand_detected: bool = False) -> str:
        """Human-readable interaction state label for HUD."""
        return self.controller.get_state_label(hand_detected)

    def _internal_on_grab(self, x: float, y: float, r: float) -> None:
        """Default hook on grab."""
        self.trigger_shockwave(x, y, r)

    def _internal_on_release(self, x: float, y: float, r: float) -> None:
        """Default hook on release."""
        self.trigger_shockwave(x, y, r)

    # -------------------------------------------------------------------------
    # Abstract Contract Methods to be implemented by Orb, Cube, and Planet
    # -------------------------------------------------------------------------

    @abstractmethod
    def trigger_shockwave(self, cx: float, cy: float, radius: float) -> None:
        """Triggers a radial energy burst and ripple at (cx, cy)."""
        pass

    @abstractmethod
    def update(
        self,
        hands: Union[Optional[HandData], List[HandData]] = None,
        dt: Optional[float] = None,
    ) -> Tuple[float, float, float]:
        """Updates kinematics, internal rotations, and dynamics. Returns (x, y, radius)."""
        pass

    @abstractmethod
    def render(
        self,
        frame: np.ndarray,
        pinch_pt: Optional[Tuple[float, float]] = None,
        dt: Optional[float] = None,
    ) -> None:
        """Composites the holographic object visual effects onto the video frame."""
        pass

