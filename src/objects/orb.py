"""Holographic Orb Implementation.

Reference holographic object implementation providing multi-layer exponential glow,
3D gyroscopic rotating rings, Keplerian particles, electric plasma tethers,
and shockwave bursts.
"""

from typing import Callable, Optional, Tuple, Union
import numpy as np

from src.hand_tracker import HandData
from src.objects.base import BaseHolographicObject
from src.vfx.color_themes import ColorTheme
from src.vfx.orb_renderer import OrbRenderer


class HolographicOrb(BaseHolographicObject):
    """Holographic Glowing Energy Orb reference object."""

    def __init__(
        self,
        frame_width: int = 640,
        frame_height: int = 480,
        theme_name: str = "cyan",
        on_grab: Optional[Callable[[float, float, float], None]] = None,
        on_release: Optional[Callable[[float, float, float], None]] = None,
    ):
        super().__init__(
            name="Orb",
            frame_width=frame_width,
            frame_height=frame_height,
            theme_name=theme_name,
            min_radius=28.0,
            max_radius=125.0,
            default_radius=55.0,
            on_grab=on_grab,
            on_release=on_release,
        )
        self.renderer = OrbRenderer(theme_name=theme_name)

    def set_theme(self, theme_or_name: Union[str, ColorTheme]) -> None:
        """Updates color theme and synchronizes with renderer."""
        super().set_theme(theme_or_name)
        if hasattr(self, "renderer"):
            self.renderer.set_theme(self.theme)

    def trigger_shockwave(self, cx: float, cy: float, radius: float) -> None:
        """Triggers radial burst and shockwave on the renderer."""
        self.renderer.trigger_shockwave(cx, cy, radius)

    def update(
        self,
        hand_data: Optional[HandData],
        dt: Optional[float] = None,
    ) -> Tuple[float, float, float]:
        """Updates orb kinematics, openness scaling, and spring physics."""
        return self.controller.update(hand_data, dt=dt)

    def render(
        self,
        frame: np.ndarray,
        pinch_pt: Optional[Tuple[float, float]] = None,
        dt: Optional[float] = None,
    ) -> None:
        """Composites the full holographic orb VFX stack onto the frame."""
        self.renderer.render(
            frame=frame,
            center=(self.x, self.y),
            radius=self.current_radius,
            is_grabbed=self.is_grabbed,
            pinch_pt=pinch_pt,
            dt=dt,
        )
