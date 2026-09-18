"""Holographic Object Manager and Switcher.

Coordinates active holographic objects (Orb, Cube, Planet, Ghost Orchid, Bhondu Face,
Bioluminescent Jellyfish), seamless runtime switching via keys 1-6 or holographic menu,
state preservation (position, scale, theme, viewport), and user notification telemetry.
"""

import time
from typing import Callable, Dict, Optional, Tuple, Union

from src.objects.base import BaseHolographicObject
from src.objects.bhondu_face import HolographicBhonduFace
from src.objects.cube import HolographicCube
from src.objects.ghost_orchid import HolographicGhostOrchid
from src.objects.jellyfish import HolographicJellyfish
from src.objects.orb import HolographicOrb
from src.objects.planet import HolographicPlanet
from src.vfx.color_themes import ColorTheme


class HolographicObjectManager:
    """Manages instantiation, state transfer, and runtime switching of all 6 holographic objects."""

    OBJECT_TYPES = {
        1: ("Orb", HolographicOrb),
        2: ("Cube", HolographicCube),
        3: ("Planet", HolographicPlanet),
        4: ("Ghost Orchid", HolographicGhostOrchid),
        5: ("Bhondu Face", HolographicBhonduFace),
        6: ("Jellyfish", HolographicJellyfish),
    }

    def __init__(
        self,
        frame_width: int = 640,
        frame_height: int = 480,
        theme_name: str = "cyan",
        initial_object_id: int = 1,
        on_grab: Optional[Callable[[float, float, float], None]] = None,
        on_release: Optional[Callable[[float, float, float], None]] = None,
    ):
        self.width = frame_width
        self.height = frame_height
        self.theme_name = theme_name
        self.on_grab = on_grab
        self.on_release = on_release

        # Instantiate all 6 holographic objects
        self.objects: Dict[int, BaseHolographicObject] = {
            1: HolographicOrb(
                frame_width=frame_width,
                frame_height=frame_height,
                theme_name=theme_name,
                on_grab=on_grab,
                on_release=on_release,
            ),
            2: HolographicCube(
                frame_width=frame_width,
                frame_height=frame_height,
                theme_name=theme_name,
                on_grab=on_grab,
                on_release=on_release,
            ),
            3: HolographicPlanet(
                frame_width=frame_width,
                frame_height=frame_height,
                theme_name=theme_name,
                on_grab=on_grab,
                on_release=on_release,
            ),
            4: HolographicGhostOrchid(
                frame_width=frame_width,
                frame_height=frame_height,
                theme_name=theme_name,
                on_grab=on_grab,
                on_release=on_release,
            ),
            5: HolographicBhonduFace(
                frame_width=frame_width,
                frame_height=frame_height,
                theme_name=theme_name,
                on_grab=on_grab,
                on_release=on_release,
            ),
            6: HolographicJellyfish(
                frame_width=frame_width,
                frame_height=frame_height,
                theme_name=theme_name,
                on_grab=on_grab,
                on_release=on_release,
            ),
        }

        self.current_id: int = initial_object_id if initial_object_id in self.objects else 1
        self.status_message: Optional[str] = None
        self.status_message_time: float = 0.0

    @property
    def active_object_id(self) -> int:
        """Returns the integer ID of the currently active holographic object."""
        return self.current_id

    def get_active_object(self) -> BaseHolographicObject:
        """Returns the currently active holographic object."""
        return self.objects[self.current_id]

    def select_object(self, object_id: int) -> Tuple[bool, str]:
        """Switches to the requested holographic object (1..6)."""
        if object_id not in self.objects:
            return False, f"Invalid object ID {object_id}. Valid range: 1..6."

        if object_id == self.current_id:
            active_name = self.get_active_object().name
            return True, f"{active_name} already active"

        prev_obj = self.get_active_object()
        new_obj = self.objects[object_id]

        # Transfer spatial position, scale, velocity, mode, and theme so the new object doesn't jump
        new_obj.transfer_state_from(prev_obj)

        # Trigger lightweight holographic transition shockwave
        new_obj.trigger_shockwave(new_obj.x, new_obj.y, new_obj.current_radius)

        self.current_id = object_id
        msg = f"Switched to {new_obj.name}"
        self.status_message = msg
        self.status_message_time = time.perf_counter()
        print(f"[Hologram] {msg}")
        return True, msg

    def set_theme(self, theme_or_name: Union[str, ColorTheme]) -> None:
        """Propagates color theme to all holographic objects."""
        for obj in self.objects.values():
            obj.set_theme(theme_or_name)

    def resize_viewport(self, width: int, height: int) -> None:
        """Propagates viewport boundary changes to all holographic objects."""
        self.width = width
        self.height = height
        for obj in self.objects.values():
            obj.resize_viewport(width, height)

    def reset_position(self) -> None:
        """Centers the active holographic object."""
        self.get_active_object().reset_position()

    def cycle_interaction_mode(self) -> Tuple[object, str]:
        """Cycles interaction mode between STANDARD and INDEPENDENT across all objects."""
        active_obj = self.get_active_object()
        new_mode = active_obj.cycle_interaction_mode()
        for obj in self.objects.values():
            obj.selected_mode = new_mode
        mode_name = active_obj.get_mode_display_name()
        msg = f"Mode: {mode_name}"
        self.status_message = msg
        self.status_message_time = time.perf_counter()
        return new_mode, msg
