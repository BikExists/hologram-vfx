"""Main Application Engine for Hand-Tracked Holographic VFX.

Orchestrates webcam capture, hand tracking, gesture estimation,
physics simulation, holographic rendering, and interactive UI.
"""

import time
from typing import Optional, Tuple
import cv2
import numpy as np

from src.camera import CameraManager, SyntheticCamera
from src.hand_tracker import HandTracker, HandData
from src.interaction import OrbController
from src.vfx.color_themes import THEME_KEYS, get_theme
from src.vfx.hud import HUD
from src.vfx.orb_renderer import OrbRenderer


class HolographicVFXApp:
    """Core application coordinating capture, tracking, VFX, and display."""

    def __init__(
        self,
        camera_id: int = 0,
        width: int = 640,
        height: int = 480,
        theme_name: str = "cyan",
        synthetic_mode: bool = False,
        headless: bool = False,
    ):
        self.width = width
        self.height = height
        self.synthetic_mode = synthetic_mode
        self.headless = headless

        # Subsystems
        if synthetic_mode:
            self.camera = SyntheticCamera(width=width, height=height)
        else:
            self.camera = CameraManager(camera_id=camera_id, width=width, height=height)

        self.tracker = HandTracker()
        self.renderer = OrbRenderer(theme_name=theme_name)
        self.hud = HUD()

        # Wire up shockwave triggers to orb events
        self.orb = OrbController(
            frame_width=width,
            frame_height=height,
            on_grab=self._on_orb_grabbed,
            on_release=self._on_orb_released,
        )

        # Theme cycling
        self.theme_idx = THEME_KEYS.index(theme_name) if theme_name in THEME_KEYS else 0

        # Performance monitoring
        self.fps: float = 30.0
        self.frame_time_ms: float = 33.3
        self._fps_history = [30.0] * 10
        self._prev_frame_time = time.perf_counter()

        self.running: bool = False

    def _on_orb_grabbed(self, x: float, y: float, r: float) -> None:
        """Triggered when user pinches and grabs the orb."""
        self.renderer.trigger_shockwave(x, y, r)

    def _on_orb_released(self, x: float, y: float, r: float) -> None:
        """Triggered when user releases the grab."""
        self.renderer.trigger_shockwave(x, y, r)

    def cycle_theme(self) -> str:
        """Cycles to the next available color theme."""
        self.theme_idx = (self.theme_idx + 1) % len(THEME_KEYS)
        theme_key = THEME_KEYS[self.theme_idx]
        self.renderer.set_theme(theme_key)
        return theme_key

    def step_frame(self) -> Tuple[bool, Optional[np.ndarray], dict]:
        """Processes a single video frame and returns (success, rendered_frame, telemetry)."""
        ret, frame = self.camera.read_frame()
        if not ret or frame is None:
            return False, None, {}

        # 1. Flip horizontally for intuitive mirror mode
        frame = cv2.flip(frame, 1)

        now = time.perf_counter()
        dt = max(0.001, min(0.1, now - self._prev_frame_time))
        self._prev_frame_time = now

        # Update FPS moving average
        inst_fps = 1.0 / dt
        self._fps_history.append(inst_fps)
        if len(self._fps_history) > 15:
            self._fps_history.pop(0)
        self.fps = sum(self._fps_history) / len(self._fps_history)
        self.frame_time_ms = dt * 1000.0

        # 2. Hand Tracking
        hand_data: Optional[HandData] = self.tracker.process_frame(frame, timestamp=now)
        hand_detected = hand_data is not None

        # 3. Update Orb Physics and State Machine
        orb_x, orb_y, orb_radius = self.orb.update(hand_data, dt=dt)

        # 4. Render Holographic Landmarks (if toggled)
        if hand_detected and self.hud.show_landmarks:
            self.tracker.draw_holographic_landmarks(frame, hand_data, self.renderer.theme.ring_primary)

        # 5. Render Holographic VFX Stack
        pinch_pt = hand_data.pinch_point_px if hand_detected else None
        self.renderer.render(
            frame=frame,
            center=(orb_x, orb_y),
            radius=orb_radius,
            is_grabbed=self.orb.is_grabbed,
            pinch_pt=pinch_pt,
            dt=dt,
        )

        # 6. Render Sci-Fi HUD Overlay
        state_str = self.orb.get_state_label(hand_detected)
        openness_val = hand_data.openness if hand_detected else None
        is_pinching = hand_data.is_pinching if hand_detected else False

        self.hud.render(
            frame=frame,
            fps=self.fps,
            frame_time_ms=self.frame_time_ms,
            theme=self.renderer.theme,
            state_label=state_str,
            openness=openness_val,
            is_pinching=is_pinching,
            is_grabbed=self.orb.is_grabbed,
            hand_detected=hand_detected,
        )

        telemetry = {
            "fps": self.fps,
            "frame_time_ms": self.frame_time_ms,
            "orb_x": orb_x,
            "orb_y": orb_y,
            "orb_radius": orb_radius,
            "is_grabbed": self.orb.is_grabbed,
            "hand_detected": hand_detected,
            "openness": openness_val,
        }

        return True, frame, telemetry

    def run(self, max_frames: Optional[int] = None) -> None:
        """Starts the interactive application loop."""
        if not self.synthetic_mode:
            if not self.camera.open():
                print(f"[Error] Failed to open camera ID {self.camera.camera_id}.")
                print("[Info] Falling back to synthetic test feed...")
                self.camera = SyntheticCamera(width=self.width, height=self.height)

        window_name = "Holographic VFX - Hand-Tracked Orb"
        if not self.headless:
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL | cv2.WINDOW_GUI_EXPANDED)
            cv2.resizeWindow(window_name, self.width, self.height)

        self.running = True
        frame_count = 0

        try:
            while self.running:
                ret, frame, telemetry = self.step_frame()
                if not ret or frame is None:
                    print("[Warning] Frame read failed.")
                    break

                frame_count += 1
                if max_frames and frame_count >= max_frames:
                    break

                if not self.headless:
                    cv2.imshow(window_name, frame)
                    key = cv2.waitKey(1) & 0xFF

                    if key in (27, ord("q"), ord("Q")):
                        print("\n[Info] Exit requested by user.")
                        break
                    elif key in (ord("c"), ord("C")):
                        new_theme = self.cycle_theme()
                        print(f"[Info] Switched theme to: {new_theme}")
                    elif key in (ord("r"), ord("R")):
                        self.orb.reset_position()
                        print("[Info] Reset orb position.")
                    elif key in (ord("h"), ord("H")):
                        self.hud.toggle_landmarks()
                    elif key in (ord("s"), ord("S")):
                        filename = f"hologram_capture_{int(time.time())}.png"
                        cv2.imwrite(filename, frame)
                        print(f"[Info] Screenshot saved: {filename}")

                    # Handle window close [X] button
                    if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                        break

        except KeyboardInterrupt:
            print("\n[Info] Interrupted by user.")
        finally:
            self.close()

    def close(self) -> None:
        """Clean shutdown and resource release."""
        self.running = False
        if hasattr(self, "camera") and self.camera is not None:
            self.camera.release()
        if hasattr(self, "tracker") and self.tracker is not None:
            self.tracker.close()
        if not self.headless:
            try:
                cv2.destroyAllWindows()
            except Exception:
                pass
        print("[Info] Holographic VFX System shutdown cleanly.")
