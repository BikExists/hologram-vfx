"""Main Application Engine for Hand-Tracked Holographic VFX.

Orchestrates webcam capture, device switching, hand tracking, gesture estimation,
physics simulation, holographic rendering, and interactive UI.
"""

import time
from typing import Optional, Tuple
import cv2
import numpy as np

from src.camera import CameraSelector, CameraDeviceInfo
from src.hand_tracker import HandTracker, HandData
from src.objects import HolographicObjectManager, BaseHolographicObject
from src.vfx.color_themes import THEME_KEYS, get_theme
from src.vfx.hud import HUD


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
        available_cameras: Optional[list] = None,
    ):
        self.width = width
        self.height = height
        self.synthetic_mode = synthetic_mode
        self.headless = headless

        # Camera selection subsystem
        self.camera_selector = CameraSelector(
            initial_camera_id=camera_id,
            width=width,
            height=height,
            synthetic_mode=synthetic_mode,
            available_devices=available_cameras,
        )
        # Expose self.camera for backward compatibility
        self.camera = self.camera_selector

        self.tracker = HandTracker()
        self.hud = HUD()

        # Universal holographic object management system (Orb=1, Cube=2, Planet=3)
        self.object_manager = HolographicObjectManager(
            frame_width=width,
            frame_height=height,
            theme_name=theme_name,
            initial_object_id=1,
            on_grab=self._on_object_grabbed,
            on_release=self._on_object_released,
        )

        # Theme cycling
        self.theme_idx = THEME_KEYS.index(theme_name) if theme_name in THEME_KEYS else 0

        # Performance monitoring
        self.fps: float = 30.0
        self.frame_time_ms: float = 33.3
        self._fps_history = [30.0] * 10
        self._prev_frame_time = time.perf_counter()

        self.running: bool = False

    @property
    def active_object(self) -> BaseHolographicObject:
        """Currently active holographic object."""
        return self.object_manager.get_active_object()

    @property
    def orb(self):
        """Backward compatibility property returning the active holographic object."""
        return self.object_manager.get_active_object()

    @property
    def renderer(self):
        """Backward compatibility property exposing active object renderer."""
        obj = self.object_manager.get_active_object()
        return getattr(obj, "renderer", obj)

    def _on_object_grabbed(self, x: float, y: float, r: float) -> None:
        """Triggered when user pinches and grabs the active object."""
        self.active_object.trigger_shockwave(x, y, r)

    def _on_object_released(self, x: float, y: float, r: float) -> None:
        """Triggered when user releases the grab."""
        self.active_object.trigger_shockwave(x, y, r)

    def select_object(self, object_id: int) -> Tuple[bool, str]:
        """Switches between Holographic Objects (1=Orb, 2=Cube, 3=Planet)."""
        return self.object_manager.select_object(object_id)

    def cycle_theme(self) -> str:
        """Cycles to the next available color theme."""
        self.theme_idx = (self.theme_idx + 1) % len(THEME_KEYS)
        theme_key = THEME_KEYS[self.theme_idx]
        self.object_manager.set_theme(theme_key)
        return theme_key

    def switch_camera(self) -> Tuple[bool, str]:
        """Switches to the next detected camera device."""
        return self.camera_selector.switch_to_next()

    def step_frame(self) -> Tuple[bool, Optional[np.ndarray], dict]:
        """Processes a single video frame and returns (success, rendered_frame, telemetry)."""
        ret, frame = self.camera_selector.read_frame()
        if not ret or frame is None:
            return False, None, {}

        # 1. Flip horizontally for intuitive mirror mode
        frame = cv2.flip(frame, 1)

        # Dynamic viewport adaptation for varying camera resolutions
        h, w = frame.shape[:2]
        if w != self.width or h != self.height:
            self.width = w
            self.height = h
            self.object_manager.resize_viewport(w, h)

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

        # 3. Update Active Holographic Object Kinematics
        obj = self.active_object
        obj_x, obj_y, obj_radius = obj.update(hand_data, dt=dt)

        # 4. Render Holographic Landmarks (if toggled)
        if hand_detected and self.hud.show_landmarks:
            self.tracker.draw_holographic_landmarks(frame, hand_data, obj.theme.ring_primary)

        # 5. Render Active Holographic Object VFX Stack
        pinch_pt = hand_data.pinch_point_px if hand_detected else None
        obj.render(
            frame=frame,
            pinch_pt=pinch_pt,
            dt=dt,
        )

        # 6. Render Sci-Fi HUD Overlay
        state_str = obj.get_state_label(hand_detected)
        openness_val = hand_data.openness if hand_detected else None
        is_pinching = hand_data.is_pinching if hand_detected else False

        # Active camera and object switch notifications
        cur_dev = self.camera_selector.get_current_device()
        cam_notif = None
        if self.camera_selector.status_message and (now - self.camera_selector.status_message_time) < 2.5:
            cam_notif = self.camera_selector.status_message

        obj_notif = None
        if self.object_manager.status_message and (now - self.object_manager.status_message_time) < 2.5:
            obj_notif = self.object_manager.status_message

        self.hud.render(
            frame=frame,
            fps=self.fps,
            frame_time_ms=self.frame_time_ms,
            theme=obj.theme,
            state_label=state_str,
            openness=openness_val,
            is_pinching=is_pinching,
            is_grabbed=obj.is_grabbed,
            hand_detected=hand_detected,
            camera_name=cur_dev.name,
            camera_notification=cam_notif,
            object_name=obj.name,
            object_notification=obj_notif,
        )

        telemetry = {
            "fps": self.fps,
            "frame_time_ms": self.frame_time_ms,
            "object_type": obj.name,
            "object_x": obj_x,
            "object_y": obj_y,
            "object_radius": obj_radius,
            # Backward compatibility keys:
            "orb_x": obj_x,
            "orb_y": obj_y,
            "orb_radius": obj_radius,
            "is_grabbed": obj.is_grabbed,
            "hand_detected": hand_detected,
            "openness": openness_val,
            "camera_id": cur_dev.device_id,
            "camera_name": cur_dev.name,
            "width": self.width,
            "height": self.height,
        }

        return True, frame, telemetry

    def run(self, max_frames: Optional[int] = None) -> None:
        """Starts the interactive application loop."""
        if not self.camera_selector.open():
            print("[Warning] Initial camera open failed. Falling back to synthetic...")
            self.camera_selector.select_camera_by_id(-1)

        window_name = "Holographic VFX - Hand-Tracked Orb"
        if not self.headless:
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL | cv2.WINDOW_GUI_EXPANDED)
            cv2.resizeWindow(window_name, self.width, self.height)

        self.running = True
        frame_count = 0
        consecutive_read_failures = 0

        try:
            while self.running:
                ret, frame, telemetry = self.step_frame()
                if not ret or frame is None:
                    consecutive_read_failures += 1
                    if consecutive_read_failures >= 30:
                        print("[Warning] Extended frame read failure. Exiting loop.")
                        break
                    time.sleep(0.01)
                    continue

                consecutive_read_failures = 0
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
                    elif key in (ord("v"), ord("V")):
                        _, msg = self.switch_camera()
                        print(f"[Info] {msg}")
                    elif key in (ord("r"), ord("R")):
                        self.active_object.reset_position()
                        print(f"[Info] Reset {self.active_object.name} position.")
                    elif key in (ord("h"), ord("H")):
                        self.hud.toggle_landmarks()
                    elif key in (ord("s"), ord("S")):
                        filename = f"hologram_capture_{int(time.time())}.png"
                        cv2.imwrite(filename, frame)
                        print(f"[Info] Screenshot saved: {filename}")
                    elif ord("1") <= key <= ord("3"):
                        target_obj_id = key - ord("0")
                        _, msg = self.select_object(target_obj_id)
                        print(f"[Info] {msg}")
                    elif ord("4") <= key <= ord("9"):
                        target_index = key - ord("1")
                        if target_index < len(self.camera_selector.devices):
                            _, msg = self.camera_selector.select_device_by_index(target_index)
                            print(f"[Info] {msg}")

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
        if hasattr(self, "camera_selector") and self.camera_selector is not None:
            self.camera_selector.release()
        if hasattr(self, "tracker") and self.tracker is not None:
            self.tracker.close()
        if not self.headless:
            try:
                cv2.destroyAllWindows()
            except Exception:
                pass
        print("[Info] Holographic VFX System shutdown cleanly.")
