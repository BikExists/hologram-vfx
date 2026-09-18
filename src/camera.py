"""Camera capture management, device detection, and camera selection.

Provides robust cross-platform OpenCV webcam acquisition with Windows DirectShow,
Linux V4L2, and macOS AVFoundation backend support, device enumeration, clean
runtime camera switching, multi-camera fallback, mid-stream disconnect recovery,
and synthetic test feeds for automated testing and CI.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import math
import sys
import time
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np


def get_preferred_backend() -> int:
    """Returns the optimal OpenCV VideoCapture backend for the current operating system."""
    if sys.platform.startswith("win"):
        return cv2.CAP_DSHOW
    elif sys.platform.startswith("linux"):
        return cv2.CAP_V4L2
    elif sys.platform == "darwin":
        return cv2.CAP_AVFOUNDATION
    return cv2.CAP_ANY


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
    is_physical: bool = True  # True for native physical hardware, False for virtual/software devices


VIRTUAL_CAMERA_KEYWORDS = (
    "virtual",
    "phone link",
    "obs",
    "broadcast",
    "droidcam",
    "manycam",
    "epoccam",
    "xsplit",
    "iriun",
    "snap camera",
    "vcam",
    "camo",
    "loopback",
    "software device",
    "generic software",
)


def inspect_windows_camera_devices() -> List[Dict[str, Any]]:
    """Inspects Windows PnP and DirectShow registry to classify physical vs virtual cameras."""
    results: List[Dict[str, Any]] = []
    try:
        import winreg
    except ImportError:
        return results

    # 1. PnP Video Cameras from DeviceClasses (KSCATEGORY_VIDEO_CAMERA)
    guid_video = r"SYSTEM\CurrentControlSet\Control\DeviceClasses\{e5323777-f976-4f5b-9b55-b94699c46e44}"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, guid_video) as k:
            n_sub, _, _ = winreg.QueryInfoKey(k)
            for i in range(n_sub):
                sub_name = winreg.EnumKey(k, i)
                if not sub_name.startswith("##?#"):
                    continue

                raw_id = sub_name[4:].split("#{")[0].replace("#", "\\")
                raw_upper = raw_id.upper()
                is_software_bus = (
                    raw_upper.startswith("SWD")
                    or raw_upper.startswith("ROOT")
                    or "VCAM" in raw_upper
                )

                name = ""
                enum_path = f"SYSTEM\\CurrentControlSet\\Enum\\{raw_id}"
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, enum_path) as ek:
                        num_v, _, _ = winreg.QueryInfoKey(ek)
                        for v in range(num_v):
                            vn, vv, _ = winreg.EnumValue(ek, v)
                            if vn == "FriendlyName":
                                name = vv
                                break
                            elif vn == "DeviceDesc" and not name:
                                name = vv.split(";")[-1] if ";" in vv else vv
                except Exception:
                    pass

                if not name or name == "Generic software device":
                    if "VCAMDEVAPI" in raw_upper:
                        name = "Phone Link / Connected Camera"
                    elif not name:
                        name = "Camera" if not is_software_bus else "Virtual Camera"

                name_lower = name.lower()
                is_virtual_by_name = any(kw in name_lower for kw in VIRTUAL_CAMERA_KEYWORDS)
                is_physical = (not is_software_bus) and (not is_virtual_by_name)

                results.append({
                    "name": name,
                    "bus_id": raw_id,
                    "is_physical": is_physical,
                })
    except Exception:
        pass

    # 2. DirectShow Software Filters (HKCR CLSID\{860BB310-5D01-11d0-BD3B-00A0C911CE86}\Instance)
    dshow_path = r"CLSID\{860BB310-5D01-11d0-BD3B-00A0C911CE86}\Instance"
    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, dshow_path) as k:
            n_sub, _, _ = winreg.QueryInfoKey(k)
            for i in range(n_sub):
                sub_name = winreg.EnumKey(k, i)
                try:
                    with winreg.OpenKey(k, sub_name) as subk:
                        fname = ""
                        try:
                            fname, _ = winreg.QueryValueEx(subk, "FriendlyName")
                        except Exception:
                            fname = sub_name
                        dpath = ""
                        try:
                            dpath, _ = winreg.QueryValueEx(subk, "DevicePath")
                        except Exception:
                            dpath = ""

                        dpath_lower = dpath.lower()
                        is_phys = bool(
                            dpath
                            and (
                                dpath_lower.startswith(r"\\?\usb")
                                or dpath_lower.startswith(r"\\?\pci")
                                or dpath_lower.startswith(r"\\?\acpi")
                            )
                        )
                        if any(kw in fname.lower() for kw in VIRTUAL_CAMERA_KEYWORDS):
                            is_phys = False

                        results.append({
                            "name": fname,
                            "bus_id": dpath or sub_name,
                            "is_physical": is_phys,
                        })
                except Exception:
                    pass
    except Exception:
        pass

    return results


def inspect_linux_camera_devices() -> List[Dict[str, Any]]:
    """Inspects Linux /sys/class/video4linux to classify physical vs virtual v4l2 cameras."""
    import os
    results: List[Dict[str, Any]] = []
    base = "/sys/class/video4linux"
    if not os.path.exists(base):
        return results
    try:
        for node in sorted(os.listdir(base)):
            node_path = os.path.join(base, node)
            name_file = os.path.join(node_path, "name")
            name = node
            if os.path.exists(name_file):
                try:
                    with open(name_file, "r") as f:
                        name = f.read().strip()
                except Exception:
                    pass
            dev_link = os.path.join(node_path, "device")
            is_physical = False
            if os.path.islink(dev_link):
                try:
                    target = os.path.realpath(dev_link)
                    is_physical = ("usb" in target or "pci" in target) and ("loopback" not in name.lower())
                except Exception:
                    is_physical = False
            if any(kw in name.lower() for kw in VIRTUAL_CAMERA_KEYWORDS):
                is_physical = False
            results.append({"name": name, "bus_id": node, "is_physical": is_physical})
    except Exception:
        pass
    return results


def inspect_platform_cameras() -> List[Dict[str, Any]]:
    """Returns detected camera metadata across operating systems."""
    if sys.platform.startswith("win"):
        return inspect_windows_camera_devices()
    elif sys.platform.startswith("linux"):
        return inspect_linux_camera_devices()
    return []


def detect_available_cameras(
    max_devices: int = 4,
    include_synthetic: bool = True,
    include_virtual: bool = False,
) -> List[CameraDeviceInfo]:
    """Probes available video devices up to max_devices with platform-optimal backends.

    By default (include_virtual=False), only native physical cameras and Synthetic Feed
    are returned. Virtual software devices (such as Phone Link, OBS Virtual Camera,
    and NVIDIA Broadcast) are excluded from automated validation and test targets.
    """
    devices: List[CameraDeviceInfo] = []
    preferred_backend = get_preferred_backend()

    # 1. Query platform device metadata to identify physical vs virtual devices
    platform_meta = inspect_platform_cameras()
    phys_meta = [m for m in platform_meta if m.get("is_physical")]
    virt_meta = [m for m in platform_meta if not m.get("is_physical")]

    consecutive_probe_failures = 0

    if phys_meta:
        # Platform provided physical metadata: probe only physical device indices
        num_to_probe = min(len(phys_meta), max_devices)
        for idx in range(num_to_probe):
            cap = None
            if preferred_backend != cv2.CAP_ANY:
                try:
                    cap = cv2.VideoCapture(idx, preferred_backend)
                except Exception:
                    cap = None

            if cap is None or not cap.isOpened():
                try:
                    cap = cv2.VideoCapture(idx, cv2.CAP_ANY)
                except Exception:
                    cap = None

            if cap is not None and cap.isOpened():
                try:
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        base_name = phys_meta[idx]["name"]
                        dname = base_name + (" (Default)" if idx == 0 else "")
                        devices.append(
                            CameraDeviceInfo(
                                device_id=idx,
                                name=dname,
                                is_synthetic=False,
                                is_physical=True,
                            )
                        )
                except Exception:
                    pass
                finally:
                    cap.release()
    else:
        # Fallback probe loop when platform metadata is unavailable
        for idx in range(max_devices):
            cap = None
            if preferred_backend != cv2.CAP_ANY:
                try:
                    cap = cv2.VideoCapture(idx, preferred_backend)
                except Exception:
                    cap = None

            if cap is None or not cap.isOpened():
                try:
                    cap = cv2.VideoCapture(idx, cv2.CAP_ANY)
                except Exception:
                    cap = None

            opened = False
            if cap is not None and cap.isOpened():
                try:
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        opened = True
                        name = f"Camera {idx}" + (" (Default)" if idx == 0 else "")
                        is_virt = any(kw in name.lower() for kw in VIRTUAL_CAMERA_KEYWORDS)
                        if not is_virt or include_virtual:
                            devices.append(
                                CameraDeviceInfo(
                                    device_id=idx,
                                    name=name,
                                    is_synthetic=False,
                                    is_physical=not is_virt,
                                )
                            )
                except Exception:
                    pass
                finally:
                    cap.release()

            if opened:
                consecutive_probe_failures = 0
            else:
                consecutive_probe_failures += 1
                if idx >= 1 and consecutive_probe_failures >= 2:
                    break

    # 2. If virtual cameras are explicitly requested, append detected virtual devices
    if include_virtual and virt_meta:
        start_virt_idx = len(devices)
        for v_offset, v in enumerate(virt_meta):
            vid = start_virt_idx + v_offset
            vname = f"{v['name']} (Virtual)"
            devices.append(
                CameraDeviceInfo(
                    device_id=vid,
                    name=vname,
                    is_synthetic=False,
                    is_physical=False,
                )
            )

    # 3. If no physical camera was detected and synthetic is not requested, keep Camera 0 placeholder
    if not devices and not include_synthetic:
        devices.append(CameraDeviceInfo(device_id=0, name="Camera 0", is_synthetic=False, is_physical=True))

    # 4. Append synthetic feed as a selectable alternative source
    if include_synthetic:
        devices.append(CameraDeviceInfo(device_id=-1, name="Synthetic Feed", is_synthetic=True, is_physical=False))

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
        backend: Optional[int] = None,
    ):
        self.camera_id = camera_id
        self.target_w = width
        self.target_h = height
        self.target_fps = fps
        self.use_dshow = use_dshow
        self.backend = backend if backend is not None else (
            get_preferred_backend() if use_dshow else cv2.CAP_ANY
        )

        self.cap: Optional[cv2.VideoCapture] = None
        self.actual_w = width
        self.actual_h = height
        self.actual_fps = fps
        self._is_opened = False

    def open(self) -> bool:
        """Opens camera using optimal platform backend with universal fallback."""
        self.release()

        # Try preferred platform backend first
        if self.backend != cv2.CAP_ANY:
            try:
                self.cap = cv2.VideoCapture(self.camera_id, self.backend)
            except Exception:
                self.cap = None

        if not self.cap or not self.cap.isOpened():
            # Universal fallback to default backend
            try:
                self.cap = cv2.VideoCapture(self.camera_id, cv2.CAP_ANY)
            except Exception:
                self.cap = None

        if not self.cap or not self.cap.isOpened():
            self._is_opened = False
            return False

        # Set requested resolution and framerate
        try:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.target_w)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.target_h)
            self.cap.set(cv2.CAP_PROP_FPS, self.target_fps)
        except Exception:
            pass

        # Query actual dimensions and framerate from hardware driver
        w_val = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        h_val = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        fps_val = self.cap.get(cv2.CAP_PROP_FPS)

        self.actual_w = int(w_val) if w_val and w_val > 0 else self.target_w
        self.actual_h = int(h_val) if h_val and h_val > 0 else self.target_h
        self.actual_fps = int(fps_val) if fps_val and fps_val > 0 else self.target_fps
        self._is_opened = True
        return True

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Reads a frame and returns (success, frame)."""
        if not self._is_opened or self.cap is None:
            return False, None

        ret, frame = self.cap.read()
        if not ret or frame is None:
            return False, None

        # Dynamically ensure actual dimensions match incoming frame
        h, w = frame.shape[:2]
        self.actual_w = w
        self.actual_h = h

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
        self.actual_fps = fps
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
        ax = int((self.w * 0.5) + math.sin(t * 1.5) * (self.w * 0.15))
        ay = int((self.h * 0.5) + math.cos(t * 1.2) * (self.h * 0.12))
        cv2.circle(frame, (ax, ay), max(2, int(min(self.w, self.h) * 0.006)), (40, 50, 60), -1)

        return True, frame

    def release(self) -> None:
        self._is_opened = False


class CameraSelector:
    """Coordinates camera devices, active source instantiation, clean switching, and recovery."""

    def __init__(
        self,
        initial_camera_id: int = 0,
        width: int = 640,
        height: int = 480,
        synthetic_mode: bool = False,
        available_devices: Optional[List[CameraDeviceInfo]] = None,
        include_virtual: bool = False,
    ):
        self.width = width
        self.height = height

        # Discover or use provided devices
        if available_devices is not None:
            self.devices = list(available_devices)
        else:
            self.devices = detect_available_cameras(
                max_devices=4,
                include_synthetic=True,
                include_virtual=include_virtual,
            )

        if not self.devices:
            # Absolute fallback
            self.devices = [CameraDeviceInfo(device_id=-1, name="Synthetic Feed", is_synthetic=True, is_physical=False)]

        # Determine initial active device index
        self.current_idx = 0
        if synthetic_mode:
            for i, dev in enumerate(self.devices):
                if dev.is_synthetic:
                    self.current_idx = i
                    break
        elif initial_camera_id != 0:
            found = False
            for i, dev in enumerate(self.devices):
                if not dev.is_synthetic and dev.device_id == initial_camera_id:
                    self.current_idx = i
                    found = True
                    break
            if not found:
                # User explicitly requested an ID not present in detected physical devices.
                # Keep virtual cameras manually usable by inserting requested device.
                manual_dev = CameraDeviceInfo(
                    device_id=initial_camera_id,
                    name=f"Camera {initial_camera_id}",
                    is_synthetic=False,
                    is_physical=False,
                )
                self.devices.insert(0, manual_dev)
                self.current_idx = 0
        else:
            # initial_camera_id == 0: prefer default native physical camera (device_id == 0 and is_physical),
            # then first available physical camera, then synthetic feed
            preferred_idx = None
            first_phys_idx = None
            first_synth_idx = None
            for i, dev in enumerate(self.devices):
                if dev.is_synthetic:
                    if first_synth_idx is None:
                        first_synth_idx = i
                elif getattr(dev, "is_physical", True):
                    if dev.device_id == 0:
                        preferred_idx = i
                        break
                    elif first_phys_idx is None:
                        first_phys_idx = i
            if preferred_idx is not None:
                self.current_idx = preferred_idx
            elif first_phys_idx is not None:
                self.current_idx = first_phys_idx
            elif first_synth_idx is not None:
                self.current_idx = first_synth_idx
            else:
                self.current_idx = 0

        self.active_source: Optional[BaseCameraSource] = None
        self.status_message: Optional[str] = None
        self.status_message_time: float = 0.0
        self._consecutive_read_failures: int = 0

    @property
    def camera_id(self) -> int:
        """Compatibility property matching CameraManager.camera_id."""
        return self.get_current_device().device_id

    @property
    def actual_w(self) -> int:
        """Active capture width."""
        if self.active_source is not None and hasattr(self.active_source, "actual_w"):
            return self.active_source.actual_w
        return self.width

    @property
    def actual_h(self) -> int:
        """Active capture height."""
        if self.active_source is not None and hasattr(self.active_source, "actual_h"):
            return self.active_source.actual_h
        return self.height

    @property
    def actual_fps(self) -> int:
        """Active capture framerate."""
        if self.active_source is not None and hasattr(self.active_source, "actual_fps"):
            return self.active_source.actual_fps
        return 30

    def get_current_device(self) -> CameraDeviceInfo:
        """Returns the currently active CameraDeviceInfo."""
        return self.devices[self.current_idx]

    def get_available_devices(self) -> List[CameraDeviceInfo]:
        """Returns list of all detected camera devices."""
        return list(self.devices)

    def open(self) -> bool:
        """Opens the currently selected camera device, with intelligent fallback across devices."""
        dev = self.get_current_device()
        if self.active_source is not None:
            self.active_source.release()
            self.active_source = None

        if dev.is_synthetic:
            source: BaseCameraSource = SyntheticCamera(width=self.width, height=self.height)
            if source.open():
                self.active_source = source
                self._consecutive_read_failures = 0
                return True

        # Try opening selected physical camera
        source = CameraManager(camera_id=dev.device_id, width=self.width, height=self.height)
        if source.open():
            self.active_source = source
            self._consecutive_read_failures = 0
            return True

        # Physical camera failed: try other detected physical cameras if available
        print(f"[Warning] Failed to open {dev.name}. Checking other available cameras...")
        for i, alt_dev in enumerate(self.devices):
            if i == self.current_idx or alt_dev.is_synthetic or not getattr(alt_dev, "is_physical", True):
                continue
            alt_source = CameraManager(camera_id=alt_dev.device_id, width=self.width, height=self.height)
            if alt_source.open():
                self.current_idx = i
                self.active_source = alt_source
                self._consecutive_read_failures = 0
                msg = f"{dev.name} unavailable; using {alt_dev.name}"
                self.status_message = msg
                self.status_message_time = time.perf_counter()
                print(f"[Camera] {msg}")
                return True

        # All physical cameras failed: fallback to synthetic camera
        print(f"[Warning] No physical cameras accessible. Falling back to Synthetic feed...")
        for i, alt_dev in enumerate(self.devices):
            if alt_dev.is_synthetic:
                self.current_idx = i
                break
        fallback = SyntheticCamera(width=self.width, height=self.height)
        fallback.open()
        self.active_source = fallback
        self._consecutive_read_failures = 0
        msg = f"{dev.name} failed; using Synthetic Feed"
        self.status_message = msg
        self.status_message_time = time.perf_counter()
        return True

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Reads a frame from the active camera source, with mid-stream disconnect recovery."""
        if self.active_source is None:
            if not self.open():
                return False, None

        ret, frame = self.active_source.read_frame()
        if not ret or frame is None:
            self._consecutive_read_failures += 1
            # If a physical camera fails consecutively 5 times, attempt stream recovery
            dev = self.get_current_device()
            if self._consecutive_read_failures >= 5 and not dev.is_synthetic:
                print(f"[Warning] Stream lost on {dev.name}. Attempting recovery to Synthetic feed...")
                self._recover_stream()
                if self.active_source is not None:
                    return self.active_source.read_frame()
            return False, None

        self._consecutive_read_failures = 0
        return True, frame

    def _recover_stream(self) -> None:
        """Recovers from a dropped hardware stream by falling back to synthetic feed."""
        prev_name = self.get_current_device().name
        if self.active_source is not None:
            self.active_source.release()
            self.active_source = None

        # Find or create synthetic device
        syn_idx = -1
        for i, d in enumerate(self.devices):
            if d.is_synthetic:
                syn_idx = i
                break
        if syn_idx == -1:
            self.devices.append(CameraDeviceInfo(device_id=-1, name="Synthetic Feed", is_synthetic=True))
            syn_idx = len(self.devices) - 1

        self.current_idx = syn_idx
        fallback = SyntheticCamera(width=self.width, height=self.height)
        fallback.open()
        self.active_source = fallback
        self._consecutive_read_failures = 0
        msg = f"{prev_name} disconnected; running on Synthetic"
        self.status_message = msg
        self.status_message_time = time.perf_counter()
        print(f"[Camera Recovery] {msg}")

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
            self._consecutive_read_failures = 0
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
