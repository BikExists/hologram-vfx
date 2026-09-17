"""Tests for cross-platform camera robustness, multi-device fallback, and dynamic resolution adaptation."""

from typing import Optional, Tuple
import cv2
import numpy as np
import pytest

from src.app import HolographicVFXApp
from src.camera import (
    BaseCameraSource,
    CameraDeviceInfo,
    CameraManager,
    CameraSelector,
    SyntheticCamera,
    detect_available_cameras,
    get_preferred_backend,
)


class MockCustomCamera(BaseCameraSource):
    """Configurable mock camera for testing error paths and mid-stream disconnects."""

    def __init__(self, camera_id: int = 0, should_open: bool = True, frames_to_yield: int = -1):
        self.camera_id = camera_id
        self.should_open = should_open
        self.frames_to_yield = frames_to_yield
        self.frames_read = 0
        self.released = False
        self._is_opened = False
        self.actual_w = 640
        self.actual_h = 480
        self.actual_fps = 30

    def open(self) -> bool:
        self._is_opened = self.should_open
        return self.should_open

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        if not self._is_opened:
            return False, None
        if self.frames_to_yield >= 0 and self.frames_read >= self.frames_to_yield:
            # Simulate stream disconnection / EOF
            return False, None
        self.frames_read += 1
        frame = np.full((self.actual_h, self.actual_w, 3), 50, dtype=np.uint8)
        return True, frame

    def is_opened(self) -> bool:
        return self._is_opened

    def release(self) -> None:
        self.released = True
        self._is_opened = False


def test_get_preferred_backend():
    backend = get_preferred_backend()
    assert isinstance(backend, int)
    # Check expected backend constants
    assert backend in (cv2.CAP_DSHOW, cv2.CAP_V4L2, cv2.CAP_AVFOUNDATION, cv2.CAP_ANY)


def test_detect_available_cameras_zero_physical(monkeypatch):
    """When no physical cameras are found, returns synthetic feed."""
    def mock_video_capture(*args, **kwargs):
        class FakeCap:
            def isOpened(self):
                return False
            def release(self):
                pass
        return FakeCap()

    monkeypatch.setattr(cv2, "VideoCapture", mock_video_capture)
    devices = detect_available_cameras(max_devices=2, include_synthetic=True)
    assert len(devices) == 1
    assert devices[0].is_synthetic
    assert devices[0].name == "Synthetic Feed"


def test_camera_fallback_when_camera_0_unavailable():
    """When Camera 0 fails to open, selector automatically falls back to Camera 1."""
    devices = [
        CameraDeviceInfo(device_id=0, name="Camera 0 (Broken)", is_synthetic=False),
        CameraDeviceInfo(device_id=1, name="Camera 1 (Working)", is_synthetic=False),
        CameraDeviceInfo(device_id=-1, name="Synthetic Feed", is_synthetic=True),
    ]

    class CustomCameraManager(BaseCameraSource):
        def __init__(self, camera_id: int, *args, **kwargs):
            self.camera_id = camera_id
            self._is_opened = False
            self.actual_w = 640
            self.actual_h = 480
            self.actual_fps = 30

        def open(self) -> bool:
            # Device 0 fails, Device 1 succeeds
            if self.camera_id == 0:
                self._is_opened = False
                return False
            self._is_opened = True
            return True

        def read_frame(self):
            if not self._is_opened:
                return False, None
            return True, np.zeros((480, 640, 3), dtype=np.uint8)

        def is_opened(self):
            return self._is_opened

        def release(self):
            self._is_opened = False

    selector = CameraSelector(available_devices=devices)
    # Monkeypatch source creation in selector
    selector_devices = selector.devices
    assert selector_devices[0].device_id == 0

    # Patch CameraManager
    import src.camera
    orig_cm = src.camera.CameraManager
    src.camera.CameraManager = CustomCameraManager
    try:
        ok = selector.open()
        assert ok is True
        # Current device should now be Camera 1
        assert selector.get_current_device().device_id == 1
        assert "Camera 1" in selector.get_current_device().name
        ret, frame = selector.read_frame()
        assert ret is True
        assert frame is not None
    finally:
        src.camera.CameraManager = orig_cm
        selector.release()


def test_camera_fallback_to_synthetic_when_all_physical_fail():
    """When all physical cameras fail, selector falls back to synthetic feed."""
    devices = [
        CameraDeviceInfo(device_id=0, name="Camera 0", is_synthetic=False),
        CameraDeviceInfo(device_id=1, name="Camera 1", is_synthetic=False),
        CameraDeviceInfo(device_id=-1, name="Synthetic Feed", is_synthetic=True),
    ]

    import src.camera
    orig_cm = src.camera.CameraManager
    # All physical open calls fail
    src.camera.CameraManager = lambda *a, **k: MockCustomCamera(should_open=False)
    try:
        selector = CameraSelector(available_devices=devices)
        ok = selector.open()
        assert ok is True
        assert selector.get_current_device().is_synthetic
        ret, frame = selector.read_frame()
        assert ret is True
        assert frame is not None
    finally:
        src.camera.CameraManager = orig_cm
        selector.release()


def test_camera_stream_disconnect_recovery():
    """When a physical camera stream disconnects mid-stream (5 consecutive failures), it recovers to synthetic."""
    devices = [
        CameraDeviceInfo(device_id=0, name="Camera 0", is_synthetic=False),
        CameraDeviceInfo(device_id=-1, name="Synthetic Feed", is_synthetic=True),
    ]

    import src.camera
    orig_cm = src.camera.CameraManager
    # Camera yields 2 frames then disconnects
    mock_cam = MockCustomCamera(camera_id=0, should_open=True, frames_to_yield=2)
    src.camera.CameraManager = lambda *a, **k: mock_cam

    try:
        selector = CameraSelector(available_devices=devices)
        assert selector.open()
        assert selector.get_current_device().device_id == 0

        # Read 2 successful frames
        ret1, f1 = selector.read_frame()
        assert ret1 is True
        ret2, f2 = selector.read_frame()
        assert ret2 is True

        # Now mock camera will return False, None
        # Consecutive failures 1, 2, 3, 4
        for _ in range(4):
            ret, f = selector.read_frame()
            assert ret is False

        # 5th failure triggers _recover_stream() which switches to Synthetic
        ret5, f5 = selector.read_frame()
        assert ret5 is True
        assert f5 is not None
        assert selector.get_current_device().is_synthetic
        assert "disconnected" in selector.status_message
    finally:
        src.camera.CameraManager = orig_cm
        selector.release()


def test_dynamic_resolution_adaptation():
    """Verifies that app.step_frame() dynamically adapts when camera delivers non-default resolution."""
    class HDCamera(BaseCameraSource):
        def __init__(self):
            self.actual_w = 1280
            self.actual_h = 720
            self.actual_fps = 30
            self._opened = True

        def open(self):
            return True

        def read_frame(self):
            return True, np.zeros((720, 1280, 3), dtype=np.uint8)

        def is_opened(self):
            return self._opened

        def release(self):
            self._opened = False

    devices = [CameraDeviceInfo(device_id=0, name="HD Camera", is_synthetic=False)]
    app = HolographicVFXApp(width=640, height=480, headless=True, available_cameras=devices)
    app.camera_selector.active_source = HDCamera()

    ret, frame, telemetry = app.step_frame()
    assert ret is True
    assert frame.shape == (720, 1280, 3)
    assert app.width == 1280
    assert app.height == 720
    assert app.orb.w == 1280
    assert app.orb.h == 720
    assert telemetry["width"] == 1280
    assert telemetry["height"] == 720
    app.close()


def test_platform_camera_classification(monkeypatch):
    """Verifies that platform camera inspection accurately detects and classifies physical vs virtual devices."""
    from src.camera import (
        inspect_platform_cameras,
        inspect_windows_camera_devices,
        inspect_linux_camera_devices,
    )

    # 1. Native platform inspection should return a list without error
    plat_cams = inspect_platform_cameras()
    assert isinstance(plat_cams, list)
    for cam in plat_cams:
        assert "name" in cam
        assert "is_physical" in cam
        assert isinstance(cam["is_physical"], bool)

    # 2. Test Linux /sys/class/video4linux classification logic
    import os

    def fake_exists(path):
        if path == "/sys/class/video4linux":
            return True
        if "name" in path:
            return True
        return False

    def fake_listdir(path):
        if path == "/sys/class/video4linux":
            return ["video0", "video1", "video2"]
        return []

    def fake_islink(path):
        return True

    def fake_realpath(path):
        if "video0" in path:
            return "/sys/devices/pci0000:00/0000:00:14.0/usb1/1-3/1-3:1.0/video4linux/video0"
        if "video1" in path:
            return "/sys/devices/virtual/video4linux/video1"
        return "/sys/devices/virtual/v4l2loopback/video2"

    import builtins
    orig_open = builtins.open

    def fake_open(file, *args, **kwargs):
        class FakeFile:
            def __init__(self, content):
                self.content = content
            def read(self):
                return self.content
            def __enter__(self):
                return self
            def __exit__(self, *a):
                pass

        if "video0" in str(file):
            return FakeFile("Integrated Webcam\n")
        if "video1" in str(file):
            return FakeFile("OBS Virtual Camera\n")
        if "video2" in str(file):
            return FakeFile("v4l2loopback Device\n")
        return orig_open(file, *args, **kwargs)

    monkeypatch.setattr(os.path, "exists", fake_exists)
    monkeypatch.setattr(os, "listdir", fake_listdir)
    monkeypatch.setattr(os.path, "islink", fake_islink)
    monkeypatch.setattr(os.path, "realpath", fake_realpath)
    monkeypatch.setattr(builtins, "open", fake_open)

    linux_cams = inspect_linux_camera_devices()
    assert len(linux_cams) == 3
    # video0 is USB -> physical
    assert linux_cams[0]["is_physical"] is True
    assert "Integrated Webcam" in linux_cams[0]["name"]
    # video1 has "OBS Virtual Camera" -> virtual
    assert linux_cams[1]["is_physical"] is False
    # video2 is virtual/loopback -> virtual
    assert linux_cams[2]["is_physical"] is False


def test_camera_fallback_skips_virtual_devices():
    """Verifies that CameraSelector automatic fallback skips virtual devices and only tries physical devices."""
    devices = [
        CameraDeviceInfo(device_id=0, name="Camera 0 (Physical, Broken)", is_physical=True, is_synthetic=False),
        CameraDeviceInfo(device_id=1, name="Phone Link (Virtual)", is_physical=False, is_synthetic=False),
        CameraDeviceInfo(device_id=2, name="Camera 2 (Physical, Working)", is_physical=True, is_synthetic=False),
        CameraDeviceInfo(device_id=-1, name="Synthetic Feed", is_physical=False, is_synthetic=True),
    ]

    attempted_opens = []

    class TrackedCameraManager(BaseCameraSource):
        def __init__(self, camera_id: int, *args, **kwargs):
            self.camera_id = camera_id
            self._is_opened = False
            self.actual_w = 640
            self.actual_h = 480
            self.actual_fps = 30

        def open(self) -> bool:
            attempted_opens.append(self.camera_id)
            if self.camera_id == 0:
                self._is_opened = False
                return False
            if self.camera_id == 2:
                self._is_opened = True
                return True
            return False

        def read_frame(self):
            if not self._is_opened:
                return False, None
            return True, np.zeros((480, 640, 3), dtype=np.uint8)

        def is_opened(self):
            return self._is_opened

        def release(self):
            self._is_opened = False

    import src.camera
    orig_cm = src.camera.CameraManager
    src.camera.CameraManager = TrackedCameraManager
    try:
        selector = CameraSelector(available_devices=devices)
        ok = selector.open()
        assert ok is True
        # Selector should have tried 0, skipped virtual device 1, and opened physical device 2
        assert attempted_opens == [0, 2]
        assert selector.get_current_device().device_id == 2
        assert selector.get_current_device().is_physical is True
    finally:
        src.camera.CameraManager = orig_cm
        selector.release()

