"""Main Application Engine for Hand-Tracked Holographic VFX.

Orchestrates webcam capture, device switching, hand tracking, gesture estimation,
physics simulation, holographic rendering, and interactive UI.
"""

import math
import time
from typing import List, Optional, Tuple
import cv2
import numpy as np

from src.camera import CameraSelector, CameraDeviceInfo
from src.hand_tracker import HandTracker, HandData
from src.objects import HolographicObjectManager, BaseHolographicObject
from src.ui import UIManager, UIState
from src.vfx.color_themes import THEME_KEYS, get_theme
from src.vfx.hud import HUD
from src.vfx.presenter import AspectPreservingPresenter


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
        include_virtual: bool = False,
        skip_welcome: bool = False,
    ):
        self.width = width
        self.height = height
        self.aspect_ratio: float = width / float(height) if height > 0 else 4.0 / 3.0
        self.synthetic_mode = synthetic_mode
        self.headless = headless
        self._camera_resolution_changed: bool = True

        # Aspect-ratio-preserving window presentation subsystem
        self.presenter = AspectPreservingPresenter()

        # Camera selection subsystem
        self.camera_selector = CameraSelector(
            initial_camera_id=camera_id,
            width=width,
            height=height,
            synthetic_mode=synthetic_mode,
            available_devices=available_cameras,
            include_virtual=include_virtual,
        )
        # Expose self.camera for backward compatibility
        self.camera = self.camera_selector

        self.tracker = HandTracker()
        self.hud = HUD()

        # Universal holographic object management system (Orb=1..6)
        self.object_manager = HolographicObjectManager(
            frame_width=width,
            frame_height=height,
            theme_name=theme_name,
            initial_object_id=1,
            on_grab=self._on_object_grabbed,
            on_release=self._on_object_released,
        )

        # Holographic Touchless UI Subsystem (Welcome, Menu, Cursor, State Machine)
        self.ui = UIManager(
            on_select_object=self.select_object,
            on_cycle_mode=self.cycle_interaction_mode,
            on_cycle_theme=self.cycle_theme,
            on_set_theme=self.object_manager.set_theme,
            on_switch_camera=self.switch_camera,
            on_switch_camera_idx=self.select_camera,
        )
        if skip_welcome:
            self.ui.dismiss_welcome()

        # Theme cycling
        self.theme_idx = THEME_KEYS.index(theme_name) if theme_name in THEME_KEYS else 0

        # Performance monitoring
        self.fps: float = 30.0
        self.frame_time_ms: float = 33.3
        self._fps_history = [30.0] * 10
        self._prev_frame_time = time.perf_counter()
        self.running: bool = False
        self._last_menu_close_time: float = 0.0
        self._window_close_counter: int = 0

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
        ok, msg = self.camera_selector.switch_to_next()
        if ok:
            self._camera_resolution_changed = True
        return ok, msg

    def select_camera(self, index: int) -> Tuple[bool, str]:
        """Switches to a camera by index in the detected devices list."""
        ok, msg = self.camera_selector.select_device_by_index(index)
        if ok:
            self._camera_resolution_changed = True
        return ok, msg

    def cycle_interaction_mode(self) -> Tuple[object, str]:
        """Cycles between STANDARD and INDEPENDENT interaction modes."""
        return self.object_manager.cycle_interaction_mode()

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
            self.aspect_ratio = w / float(h) if h > 0 else 4.0 / 3.0
            self.object_manager.resize_viewport(w, h)
            self._camera_resolution_changed = True

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

        # 2. Hand Tracking (Multi-Hand detection up to 2 hands)
        detected_hands: List[HandData] = self.tracker.process_frame_multi(frame, timestamp=now)
        hand_data: Optional[HandData] = self.tracker.last_valid_hand
        hand_detected = len(detected_hands) > 0

        # 3. Holographic UI Update (Coordinates gestures, welcome dismiss, menu hit-tests, actions)
        cur_dev = self.camera_selector.get_current_device()
        self.ui.update(
            detected_hands=detected_hands,
            active_object_id=self.object_manager.active_object_id,
            active_mode_name=self.active_object.get_mode_display_name(),
            active_theme_name=self.active_object.theme.name,
            active_camera_name=cur_dev.name,
            available_cameras=self.camera_selector.get_available_devices(),
            frame_width=self.width,
            frame_height=self.height,
            dt=dt,
        )

        # 4. Update Active Holographic Object Kinematics (Passes hands unless UI owns input)
        obj = self.active_object
        if self.ui.owns_hand_input:
            obj_x, obj_y, obj_radius = obj.x, obj.y, obj.current_radius
        else:
            obj_x, obj_y, obj_radius = obj.update(detected_hands, dt=dt)

        # 5. Render Holographic Landmarks for all detected hands (if toggled and not in menu)
        if hand_detected and self.hud.show_landmarks and not self.ui.is_menu_open:
            self.tracker.draw_holographic_landmarks(frame, detected_hands, obj.theme.ring_primary)

        # 6. Render Active Holographic Object VFX Stack
        pinch_pt = None
        render_dt = 0.0 if self.ui.owns_hand_input else dt
        if not self.ui.owns_hand_input:
            pinch_pt = hand_data.pinch_point_px if (hand_data and hand_data.is_pinching) else (detected_hands[0].pinch_point_px if detected_hands else None)

        obj.render(
            frame=frame,
            pinch_pt=pinch_pt,
            dt=render_dt,
        )

        # 7. Render Sci-Fi HUD Overlay (suppressed during welcome)
        state_str = obj.get_state_label(hand_detected)
        openness_val = hand_data.openness if hand_data else (detected_hands[0].openness if detected_hands else None)
        is_pinching = hand_data.is_pinching if hand_data else any(h.is_pinching for h in detected_hands)

        # Active camera and object switch notifications
        cam_notif = None
        if self.camera_selector.status_message and (now - self.camera_selector.status_message_time) < 2.5:
            cam_notif = self.camera_selector.status_message

        obj_notif = None
        if self.object_manager.status_message and (now - self.object_manager.status_message_time) < 2.5:
            obj_notif = self.object_manager.status_message

        # Synchronize theme index if object theme changed via gesture
        curr_theme_k = getattr(obj.controller, "current_theme_key", None)
        if curr_theme_k and curr_theme_k in THEME_KEYS:
            self.theme_idx = THEME_KEYS.index(curr_theme_k)

        rot_deg = math.degrees(obj.rotation)
        if not self.ui.is_welcome_active:
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
                interaction_mode=obj.interaction_mode,
                two_hand_scale=obj.two_hand_scale,
                rotation_deg=rot_deg,
                selected_mode_name=obj.get_mode_display_name(),
            )

        # 8. Render Holographic UI Layer (Welcome screen, Menu, Cursor, Gesture Reticle)
        self.ui.render(frame, obj.theme)

        telemetry = {
            "fps": self.fps,
            "frame_time_ms": self.frame_time_ms,
            "object_type": obj.name,
            "object_x": obj_x,
            "object_y": obj_y,
            "object_radius": obj_radius,
            "rotation_rad": obj.rotation,
            "rotation_deg": rot_deg,
            "interaction_mode": obj.interaction_mode,
            "two_hand_scale": obj.two_hand_scale,
            "selected_mode": obj.selected_mode.value,
            "selected_mode_name": obj.get_mode_display_name(),
            "num_hands_detected": len(detected_hands),
            "ui_state": self.ui.current_state.value,
            "is_menu_open": self.ui.is_menu_open,
            "is_welcome_active": self.ui.is_welcome_active,
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
            "aspect_ratio": self.aspect_ratio,
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
            self._camera_resolution_changed = False

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
                    # Dynamically resize window only when camera resolution or device changes
                    if self._camera_resolution_changed:
                        cv2.resizeWindow(window_name, self.width, self.height)
                        self._camera_resolution_changed = False

                    # Query window client rectangle
                    try:
                        rect = cv2.getWindowImageRect(window_name)
                        win_w, win_h = rect[2], rect[3]
                    except Exception:
                        win_w, win_h = self.width, self.height

                    # Present frame with aspect-ratio preservation (direct or letterbox)
                    display_frame = self.presenter.prepare_presentation(frame, win_w, win_h)
                    cv2.imshow(window_name, display_frame)
                    key = cv2.waitKey(1) & 0xFF

                    if key in (27, ord("q"), ord("Q")):
                        cur_dev = self.camera_selector.get_current_device()
                        if self.ui.is_menu_open:
                            self.ui.close_menu(
                                active_object_id=self.object_manager.active_object_id,
                                active_mode_name=self.active_object.get_mode_display_name(),
                                active_theme_name=self.active_object.theme.name,
                                active_camera_name=cur_dev.name,
                                active_camera_idx=self.camera_selector.current_idx,
                                force=True,
                            )
                            self._last_menu_close_time = now
                            print("[Info] Closed holographic menu.")
                        elif self.ui.is_welcome_active:
                            self.ui.dismiss_welcome()
                            self._last_menu_close_time = now
                            print("[Info] Dismissed welcome screen.")
                        elif (now - self._last_menu_close_time) < 0.40:
                            # Debounce: user just dismissed menu/welcome with this physical keypress
                            pass
                        else:
                            print("\n[Info] Exit requested by user.")
                            break
                    elif key in (32, 13):  # Space or Enter
                        if self.ui.is_welcome_active:
                            self.ui.dismiss_welcome()
                            print("[Info] Welcome screen dismissed.")
                    elif key in (ord("m"), ord("M")):
                        cur_dev = self.camera_selector.get_current_device()
                        self.ui.toggle_menu(
                            active_object_id=self.object_manager.active_object_id,
                            active_mode_name=self.active_object.get_mode_display_name(),
                            active_theme_name=self.active_object.theme.name,
                            active_camera_name=cur_dev.name,
                            active_camera_idx=self.camera_selector.current_idx,
                        )
                        print(f"[Info] Holographic menu {'opened' if self.ui.is_menu_open else 'closed'}.")
                    elif key in (ord("\t"), ord("i"), ord("I")):
                        _, msg = self.cycle_interaction_mode()
                        print(f"[Info] {msg}")
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
                    elif ord("1") <= key <= ord("6"):
                        target_obj_id = key - ord("0")
                        _, msg = self.select_object(target_obj_id)
                        print(f"[Info] {msg}")
                    elif ord("7") <= key <= ord("9"):
                        target_index = key - ord("1")
                        if target_index < len(self.camera_selector.devices):
                            ok, msg = self.camera_selector.select_device_by_index(target_index)
                            if ok:
                                self._camera_resolution_changed = True
                            print(f"[Info] {msg}")

                    # Handle window close [X] button with debounce against transient window message glitches
                    try:
                        prop_visible = cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE)
                    except Exception:
                        prop_visible = 1.0

                    if prop_visible < 1:
                        self._window_close_counter += 1
                        if self._window_close_counter >= 5:
                            print("\n[Info] Window closed by user.")
                            break
                    else:
                        self._window_close_counter = 0

        except KeyboardInterrupt:
            print("\n[Info] Interrupted by user.")
        except Exception as e:
            import traceback
            print(f"\n[Error] Unhandled exception in main loop: {e}")
            traceback.print_exc()
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
