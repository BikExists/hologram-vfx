"""UI State Machine for Holographic Interface.

Defines UI states (WELCOME, RUNNING, MENU) and deterministic,
debounced state transitions with hysteresis and hand-loss protection.
"""

from enum import Enum
import time
from typing import Optional, Tuple


class UIState(str, Enum):
    """Primary application interface states."""

    WELCOME = "WELCOME"  # Introductory holographic welcome overlay
    RUNNING = "RUNNING"  # Primary interactive holographic VFX scene
    MENU = "MENU"        # Holographic control panel / menu overlay


class UIStateMachine:
    """Manages transitions between WELCOME, RUNNING, and MENU with hysteresis."""

    def __init__(self, initial_state: UIState = UIState.WELCOME, transition_cooldown: float = 0.35):
        self.state: UIState = initial_state
        self.cooldown: float = transition_cooldown
        self.last_transition_time: float = 0.0
        self.state_time_start: float = time.perf_counter()

    @property
    def time_in_state(self) -> float:
        """Elapsed time in seconds in the current state."""
        return time.perf_counter() - self.state_time_start

    def can_transition(self) -> bool:
        """True if sufficient cooldown time has elapsed since last state change."""
        return (time.perf_counter() - self.last_transition_time) >= self.cooldown

    def transition_to(self, new_state: UIState, force: bool = False) -> Tuple[bool, str]:
        """Attempts a transition to new_state with debounce protection."""
        if new_state == self.state:
            return False, f"Already in {self.state.value}"

        now = time.perf_counter()
        if not force and (now - self.last_transition_time) < self.cooldown:
            return False, f"Transition debounced (cooldown {self.cooldown:.2f}s)"

        prev_state = self.state
        self.state = new_state
        self.last_transition_time = now
        self.state_time_start = now
        return True, f"UI State: {prev_state.value} -> {new_state.value}"

    def dismiss_welcome(self, force: bool = True) -> Tuple[bool, str]:
        """Transitions from WELCOME to RUNNING."""
        if self.state == UIState.WELCOME:
            return self.transition_to(UIState.RUNNING, force=force)
        return False, "Not in WELCOME state"

    def open_menu(self, force: bool = False) -> Tuple[bool, str]:
        """Opens the holographic menu from RUNNING."""
        if self.state == UIState.RUNNING:
            return self.transition_to(UIState.MENU, force=force)
        return False, f"Cannot open menu from {self.state.value}"

    def close_menu(self, force: bool = False) -> Tuple[bool, str]:
        """Closes the holographic menu and returns to RUNNING."""
        if self.state == UIState.MENU:
            return self.transition_to(UIState.RUNNING, force=force)
        return False, f"Cannot close menu from {self.state.value}"

    def toggle_menu(self, force: bool = False) -> Tuple[bool, str]:
        """Toggles between RUNNING and MENU states."""
        if self.state == UIState.RUNNING:
            return self.open_menu(force=force)
        elif self.state == UIState.MENU:
            return self.close_menu(force=force)
        return False, f"Cannot toggle menu from {self.state.value}"
