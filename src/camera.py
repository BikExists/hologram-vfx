"""Camera capture management, device detection, and camera selection.

Provides robust OpenCV webcam acquisition with Windows DirectShow support,
device enumeration, clean runtime camera switching, graceful fallback,
and synthetic test feeds for automated testing and CI.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import math
import time
from typing import List, Optional, Tuple
import cv2
import numpy as np


class BaseCameraSource(ABC):
    """Abstract interface for video frame providers."""

    @abstractmethod
    def open(self) -> bool:
        """Initialize and open the video stream."""
        pass

    @abstractmethod
    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Read next video frame. Returns (success, bgr_frame)."""
        pass

    @abstractmethod
    def is_opened(self) -> bool:
        """Check if video stream is actively open."""
        pass

    @abstractmethod
    def release(self) -> None:
        """Safely release underlying hardware or stream resources."""
        pass


@dataclass
class CameraDeviceInfo:
    """Metadata describing an available camera or video device."""

    device_id: int  # 0, 1, 2... or -1 for synthetic
    name: str  # Human-readable name
    is_synthetic: bool = False


def detect_available_cameras(
    max_devices: int = 4,
    include_synthetic: bool = True,
) -> List[CameraDeviceInfo]:
    """Probes available video devices up to max_devices."""
    devices: List[CameraDeviceInfo] = []

    for idx in range(max_devices):
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(idx)

        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                name = f"Camera {idx}" + (" (Default)" if idx == 0 else "")
                devices.append(CameraDeviceInfo(device_id=idx, name=name, is_synthetic=False))
            cap.release()

    # If no physical camera was detected, provide Camera 0 placeholder if requested
    if not devices and not include_synthetic:
        devices.append(CameraDeviceInfo(device_id=0, name="Camera 0", is_synthetic=False))

    # Append synthetic feed as a selectable alternative source
    if include_synthetic:
        devices.append(CameraDeviceInfo(device_id=-1, name="Synthetic Feed", is_synthetic=True))

    return devices


class CameraManager(BaseCameraSource):
    """Manages webcam capture lifecycle, backend selection, and frame acquisition."""

    def __init__(
        self,
        camera_id: int = 0,
        width: int = 640,
        height: int = 480,
        fps: int = 30,
        use_dshow: bool = True,
    ):
        self.camera_id = camera_id
        self.target_w = width
        self.target_h = height
        self.target_fps = fps
        self.use_dshow = use_dshow

        self.cap: Optional[cv2.VideoCapture] = None
        self.actual_w = width
        self.actual_h = height
        self._is_opened = False

    def open(self) -> bool:
        """Opens camera using optimal backend on Windows."""
        self.release()

        # Try DirectShow on Windows first for fast startup
        if self.use_dshow:
            self.cap = cv2.VideoCapture(self.camera_id, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                # Fallback to default
                self.cap = cv2.VideoCapture(self.camera_id)
        else:
            self.cap = cv2.VideoCapture(self.camera_id)

        if not self.cap or not self.cap.isOpened():
            self._is_opened = False
            return False

        # Set requested resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.target_w)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.target_h)
        self.cap.set(cv2.CAP_PROP_FPS, self.target_fps)

        self.actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or self.target_w
        self.actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or self.target_h
        self._is_opened = True
        return True

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Reads a frame and returns (success, frame)."""
        if not self._is_opened or self.cap is None:
            return False, None

        ret, frame = self.cap.read()
        if not ret or frame is None:
            return False, None

        return True, frame

    def is_opened(self) -> bool:
        return self._is_opened and (self.cap is not None and self.cap.isOpened())

    def release(self) -> None:
        """Safely release webcam device."""
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        self._is_opened = False

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


class SyntheticCamera(BaseCameraSource):
    """Generates procedural video frames for headless testing and benchmark verification."""

    def __init__(self, width: int = 640, height: int = 480, fps: int = 30):
        self.w = width
        self.h = height
        self.actual_w = width
        self.actual_h = height
        self.fps = fps
        self.start_time = time.perf_counter()
        self.frame_idx = 0
        self._is_opened = True

    def open(self) -> bool:
        self._is_opened = True
        return True

    def is_opened(self) -> bool:
        return self._is_opened

    def read_frame(self) -> Tuple[bool, np.ndarray]:
        """Generates a dark sci-fi gradient background frame."""
        if not self._is_opened:
            return False, None

        t = (self.frame_idx / float(self.fps))
        self.frame_idx += 1

        # Dark subtle vignette background
        frame = np.zeros((self.h, self.w, 3), dtype=np.uint8)

        # Subtle dark ambient grid
        grid_spacing = 40
        grid_color = (18, 22, 28)
        for x in range(0, self.w, grid_spacing):
            cv2.line(frame, (x, 0), (x, self.h), grid_color, 1)
        for y in range(0, self.h, grid_spacing):
            cv2.line(frame, (0, y), (self.w, y), grid_color, 1)

        # Subtle moving ambient particle
        ax = int((self.w * 0.5) + math.sin(t * 1.5) * 100)
        ay = int((self.h * 0.5) + math.cos(t * 1.2) * 60)
        cv2.circle(frame, (ax, ay), 3, (40, 50, 60), -1)

        return True, frame

    def release(self) -> None:
        self._is_opened = False


class CameraSelector:
    """Coordinates camera devices, active source instantiation, and clean switching."""

    def __init__(
        self,
        initial_camera_id: int = 0,
        width: int = 640,
        height: int = 480,
        synthetic_mode: bool = False,
        available_devices: Optional[List[CameraDeviceInfo]] = None,
    ):
        self.width = width
        self.height = height

        # Discover or use provided devices
        if available_devices is not None:
            self.devices = list(available_devices)
        else:
            self.devices = detect_available_cameras(max_devices=4, include_synthetic=True)

        if not self.devices:
            # Absolute fallback
            self.devices = [CameraDeviceInfo(device_id=-1, name="Synthetic Feed", is_synthetic=True)]

        # Determine initial active device index
        self.current_idx = 0
        if synthetic_mode:
            for i, dev in enumerate(self.devices):
                if dev.is_synthetic:
                    self.current_idx = i
                    break
        elif initial_camera_id != 0:
            for i, dev in enumerate(self.devices):
                if not dev.is_synthetic and dev.device_id == initial_camera_id:
                    self.current_idx = i
                    break

        self.active_source: Optional[BaseCameraSource] = None
        self.status_message: Optional[str] = None
        self.status_message_time: float = 0.0

    @property
    def camera_id(self) -> int:
        """Compatibility property matching CameraManager.camera_id."""
        return self.get_current_device().device_id

    def get_current_device(self) -> CameraDeviceInfo:
        """Returns the currently active CameraDeviceInfo."""
        return self.devices[self.current_idx]

    def get_available_devices(self) -> List[CameraDeviceInfo]:
        """Returns list of all detected camera devices."""
        return list(self.devices)

    def open(self) -> bool:
        """Opens the currently selected camera device."""
        dev = self.get_current_device()
        if self.active_source is not None:
            self.active_source.release()
            self.active_source = None

        if dev.is_synthetic:
            source = SyntheticCamera(width=self.width, height=self.height)
        else:
            source = CameraManager(camera_id=dev.device_id, width=self.width, height=self.height)

        if source.open():
            self.active_source = source
            return True

        # Fallback to synthetic if physical camera failed
        print(f"[Warning] Failed to open {dev.name}, falling back to Synthetic...")
        fallback = SyntheticCamera(width=self.width, height=self.height)
        fallback.open()
        self.active_source = fallback
        return False

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Reads a frame from the currently active camera source."""
        if self.active_source is None:
            if not self.open():
                return False, None
        return self.active_source.read_frame()

    def switch_to_next(self) -> Tuple[bool, str]:
        """Switches to the next camera in the detected devices list."""
        if len(self.devices) <= 1:
            msg = f"Only 1 camera source available ({self.devices[0].name})"
            return True, msg
        next_idx = (self.current_idx + 1) % len(self.devices)
        return self.select_device_by_index(next_idx)

    def switch_to_previous(self) -> Tuple[bool, str]:
        """Switches to the previous camera in the detected devices list."""
        if len(self.devices) <= 1:
            msg = f"Only 1 camera source available ({self.devices[0].name})"
            return True, msg
        prev_idx = (self.current_idx - 1) % len(self.devices)
        return self.select_device_by_index(prev_idx)

    def select_device_by_index(self, index: int) -> Tuple[bool, str]:
        """Switches to a device by index in self.devices."""
        if not (0 <= index < len(self.devices)):
            return False, f"Invalid camera index {index}"

        prev_idx = self.current_idx
        old_source = self.active_source

        self.current_idx = index
        target_dev = self.devices[self.current_idx]

        # Attempt to create and open new camera safely
        try:
            if target_dev.is_synthetic:
                new_source: BaseCameraSource = SyntheticCamera(width=self.width, height=self.height)
            else:
                new_source = CameraManager(camera_id=target_dev.device_id, width=self.width, height=self.height)

            opened_ok = new_source.open()
        except Exception as e:
            print(f"[Camera Error] Exception while opening {target_dev.name}: {e}")
            opened_ok = False
            new_source = None

        if opened_ok and new_source is not None:
            # Release old source cleanly now that new source succeeded
            if old_source is not None:
                old_source.release()
            self.active_source = new_source
            msg = f"Switched to {target_dev.name}"
            self.status_message = msg
            self.status_message_time = time.perf_counter()
            print(f"[Camera] {msg}")
            return True, msg
        else:
            # Release failed new source if it was created
            if new_source is not None:
                new_source.release()
            # Revert index
            print(f"[Camera Error] Failed to open {target_dev.name}. Reverting to {self.devices[prev_idx].name}...")
            self.current_idx = prev_idx
            if self.active_source is None or not self.active_source.is_opened():
                fallback_dev = self.devices[prev_idx]
                if fallback_dev.is_synthetic:
                    self.active_source = SyntheticCamera(width=self.width, height=self.height)
                else:
                    self.active_source = CameraManager(
                        camera_id=fallback_dev.device_id,
                        width=self.width,
                        height=self.height,
                    )
                self.active_source.open()
            msg = f"Failed to open {target_dev.name}; reverted"
            self.status_message = msg
            self.status_message_time = time.perf_counter()
            return False, msg

    def select_camera_by_id(self, device_id: int) -> Tuple[bool, str]:
        """Switches to a camera by hardware device_id or -1 for synthetic."""
        for idx, dev in enumerate(self.devices):
            if dev.device_id == device_id:
                return self.select_device_by_index(idx)
        return False, f"Camera device {device_id} not found"

    def is_opened(self) -> bool:
        return self.active_source is not None and self.active_source.is_opened()

    def release(self) -> None:
        """Safely release the active camera."""
        if self.active_source is not None:
            self.active_source.release()
            self.active_source = None
