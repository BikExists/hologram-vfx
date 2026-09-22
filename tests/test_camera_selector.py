"""Unit and integration tests for camera selection and device management."""

import cv2
import numpy as np
import pytest
from src.camera import (
    BaseCameraSource,
    CameraDeviceInfo,
    CameraManager,
    CameraSelector,
    SyntheticCamera,
    detect_available_cameras,
)


class MockFailingCamera(BaseCameraSource):
    """Mock camera that fails to open, for testing graceful error fallback."""

    def __init__(self, camera_id: int = 99, *args, **kwargs):
        self.camera_id = camera_id
        self.released = False

    def open(self) -> bool:
        return False

    def read_frame(self):
        return False, None

    def is_opened(self) -> bool:
        return False

    def release(self) -> None:
        self.released = True


def test_detect_available_cameras():
    devices = detect_available_cameras(max_devices=2, include_synthetic=True, include_virtual=False)
    assert len(devices) >= 1
    # Check structure
    for dev in devices:
        assert isinstance(dev, CameraDeviceInfo)
        assert isinstance(dev.name, str)
        assert isinstance(dev.device_id, int)
        assert isinstance(dev.is_synthetic, bool)
        assert hasattr(dev, "is_physical")
        assert isinstance(dev.is_physical, bool)
        # In default automated mode, any non-synthetic camera must be physical
        if not dev.is_synthetic:
            assert dev.is_physical is True
            # Virtual camera signatures must be excluded
            name_lower = dev.name.lower()
            for kw in ("phone link", "obs", "droidcam", "manycam"):
                assert kw not in name_lower

    # Synthetic should be present when requested
    assert any(d.is_synthetic for d in devices)


def test_virtual_cameras_excluded_from_automated_validation(monkeypatch):
    """Verifies that virtual cameras (Phone Link, OBS, etc.) are excluded from default automated detection."""
    # Mock inspect_platform_cameras to return 1 physical and 2 virtual cameras
    mock_meta = [
        {"name": "USB HD Webcam", "bus_id": r"USB\VID_1234&PID_5678", "is_physical": True},
        {"name": "Phone Link Virtual Camera", "bus_id": r"SWD\VCAMDEVAPI\123", "is_physical": False},
        {"name": "OBS Virtual Camera", "bus_id": "{ABC-123}", "is_physical": False},
    ]
    monkeypatch.setattr("src.camera.inspect_platform_cameras", lambda: mock_meta)

    # Mock cv2.VideoCapture to succeed for physical index 0
    class MockCap:
        def isOpened(self):
            return True
        def read(self):
            return True, np.zeros((480, 640, 3), dtype=np.uint8)
        def release(self):
            pass

    monkeypatch.setattr(cv2, "VideoCapture", lambda *a, **k: MockCap())

    # 1. Default detection (automated validation mode)
    default_devs = detect_available_cameras(include_synthetic=True, include_virtual=False)
    # Must only contain the physical camera and synthetic feed
    dev_names = [d.name for d in default_devs]
    assert "USB HD Webcam (Default)" in dev_names
    assert "Synthetic Feed" in dev_names
    assert not any("phone link" in name.lower() for name in dev_names)
    assert not any("obs" in name.lower() for name in dev_names)
    assert all(d.is_physical for d in default_devs if not d.is_synthetic)

    # 2. Explicit include_virtual=True mode
    all_devs = detect_available_cameras(include_synthetic=True, include_virtual=True)
    all_names = [d.name for d in all_devs]
    assert any("phone link" in name.lower() for name in all_names)
    assert any("obs" in name.lower() for name in all_names)
    # Virtual devices must have is_physical=False
    for d in all_devs:
        if "phone link" in d.name.lower() or "obs" in d.name.lower():
            assert d.is_physical is False


def test_manual_virtual_camera_selection():
    """Verifies that an explicitly requested camera ID (e.g. virtual camera) is manually usable."""
    # List containing only physical and synthetic
    devices = [
        CameraDeviceInfo(device_id=0, name="Integrated Camera", is_synthetic=False, is_physical=True),
        CameraDeviceInfo(device_id=-1, name="Synthetic Feed", is_synthetic=True, is_physical=False),
    ]
    # User requests camera_id=3 which is not in default physical list
    selector = CameraSelector(initial_camera_id=3, available_devices=devices)
    # Device should be manually added and selected
    assert selector.get_current_device().device_id == 3
    assert selector.get_current_device().is_physical is False
    assert selector.camera_id == 3



def test_camera_selector_synthetic_init():
    devices = [
        CameraDeviceInfo(device_id=0, name="Camera 0"),
        CameraDeviceInfo(device_id=-1, name="Synthetic Feed", is_synthetic=True),
    ]
    selector = CameraSelector(synthetic_mode=True, available_devices=devices)
    assert selector.get_current_device().is_synthetic
    assert selector.open()
    ret, frame = selector.read_frame()
    assert ret is True
    assert frame is not None
    assert frame.shape == (480, 640, 3)
    selector.release()


def test_camera_selector_cycling():
    devices = [
        CameraDeviceInfo(device_id=-1, name="Synthetic 1", is_synthetic=True),
        CameraDeviceInfo(device_id=-1, name="Synthetic 2", is_synthetic=True),
    ]
    selector = CameraSelector(available_devices=devices)
    assert selector.get_current_device().name == "Synthetic 1"

    # Cycle next
    ok, msg = selector.switch_to_next()
    assert ok is True
    assert selector.get_current_device().name == "Synthetic 2"

    # Cycle next again (wraps around)
    ok, msg = selector.switch_to_next()
    assert ok is True
    assert selector.get_current_device().name == "Synthetic 1"

    # Cycle previous
    ok, msg = selector.switch_to_previous()
    assert ok is True
    assert selector.get_current_device().name == "Synthetic 2"

    selector.release()


def test_camera_selector_graceful_fallback(monkeypatch):
    """Verifies that selecting an unopenable camera reverts safely to the previous source."""
    devices = [
        CameraDeviceInfo(device_id=-1, name="Working Synthetic", is_synthetic=True),
        CameraDeviceInfo(device_id=99, name="Broken Camera", is_synthetic=False),
    ]
    selector = CameraSelector(available_devices=devices)
    assert selector.open()
    assert selector.get_current_device().name == "Working Synthetic"

    # Monkeypatch CameraManager to use MockFailingCamera
    monkeypatch.setattr("src.camera.CameraManager", MockFailingCamera)

    # Try switching to the broken camera
    ok, msg = selector.select_device_by_index(1)
    assert ok is False
    assert "Failed to open" in msg

    # Selector should have safely reverted to the working synthetic source
    assert selector.get_current_device().name == "Working Synthetic"
    assert selector.is_opened()
    ret, frame = selector.read_frame()
    assert ret is True
    assert frame is not None

    selector.release()


def test_camera_selector_select_by_id():
    devices = [
        CameraDeviceInfo(device_id=0, name="Camera 0"),
        CameraDeviceInfo(device_id=1, name="Camera 1"),
        CameraDeviceInfo(device_id=-1, name="Synthetic Feed", is_synthetic=True),
    ]
    selector = CameraSelector(available_devices=devices)
    # Select synthetic by id -1
    ok, msg = selector.select_camera_by_id(-1)
    assert ok is True
    assert selector.get_current_device().is_synthetic

    # Select nonexistent id 99
    ok, msg = selector.select_camera_by_id(99)
    assert ok is False
    assert "not found" in msg

    selector.release()


def test_multiple_physical_cameras_enumerated_and_selectable(monkeypatch):
    """Verifies that multiple physical cameras (e.g. integrated webcam and external USB camera)
    are both discovered, retained as physical devices, and selectable."""
    mock_meta = [
        {"device_id": 0, "name": "Integrated Camera", "bus_id": r"\\?\acpi#...", "is_physical": True},
        {"device_id": 1, "name": "USB FHD Webcam", "bus_id": r"\\?\usb#...", "is_physical": True},
    ]
    monkeypatch.setattr("src.camera.inspect_platform_cameras", lambda: mock_meta)

    class MockCap:
        def __init__(self, idx, *args, **kwargs):
            self.idx = idx

        def isOpened(self):
            return True

        def read(self):
            return True, np.zeros((480, 640, 3), dtype=np.uint8)

        def get(self, prop):
            if prop == cv2.CAP_PROP_FRAME_WIDTH:
                return 640.0
            if prop == cv2.CAP_PROP_FRAME_HEIGHT:
                return 480.0
            if prop == cv2.CAP_PROP_FPS:
                return 30.0
            return 0.0

        def set(self, prop, val):
            return True

        def release(self):
            pass

    monkeypatch.setattr(cv2, "VideoCapture", lambda idx, *a, **k: MockCap(idx))

    devices = detect_available_cameras(max_devices=6, include_synthetic=True, include_virtual=False)
    # Both physical cameras should be detected
    dev_names = [d.name for d in devices]
    assert any("Integrated Camera" in name for name in dev_names)
    assert any("USB FHD Webcam" in name for name in dev_names)
    assert any("Synthetic Feed" in name for name in dev_names)

    # Both physical devices must have is_physical=True
    for d in devices:
        if not d.is_synthetic:
            assert d.is_physical is True

    # Test CameraSelector switching between them
    selector = CameraSelector(available_devices=devices)
    assert selector.get_current_device().device_id == 0
    ok, msg = selector.switch_to_next()
    assert ok is True
    assert selector.get_current_device().device_id == 1
    selector.release()


def test_physical_camera_at_non_zero_index_when_index_0_is_virtual(monkeypatch):
    """Verifies that when index 0 is a virtual camera (e.g. Phone Link) and index 1 is a physical camera,
    the physical camera at index 1 is discovered and selectable even when virtual cameras are excluded."""
    mock_meta = [
        {"device_id": 0, "name": "Phone Link Virtual Camera", "bus_id": r"SWD\VCAMDEVAPI", "is_physical": False},
        {"device_id": 1, "name": "External USB Camera", "bus_id": r"\\?\usb#...", "is_physical": True},
    ]
    monkeypatch.setattr("src.camera.inspect_platform_cameras", lambda: mock_meta)

    opened_indices = []

    class MockCap:
        def __init__(self, idx, *args, **kwargs):
            self.idx = idx
            opened_indices.append(idx)

        def isOpened(self):
            return True

        def read(self):
            return True, np.zeros((480, 640, 3), dtype=np.uint8)

        def release(self):
            pass

    monkeypatch.setattr(cv2, "VideoCapture", lambda idx, *a, **k: MockCap(idx))

    # In default mode (include_virtual=False), virtual camera at idx 0 is not candidate for probing,
    # but physical camera at idx 1 MUST be probed and found.
    devices = detect_available_cameras(max_devices=6, include_synthetic=True, include_virtual=False)
    dev_names = [d.name for d in devices]
    assert not any("Phone Link" in name for name in dev_names)
    assert any("External USB Camera" in name for name in dev_names)
    assert any("Synthetic Feed" in name for name in dev_names)

    phys_dev = next(d for d in devices if "External USB Camera" in d.name)
    assert phys_dev.device_id == 1
    assert phys_dev.is_physical is True
    assert 1 in opened_indices


def test_probe_failure_on_unavailable_physical_camera_handled_gracefully(monkeypatch):
    """Verifies that if a physical camera candidate fails to open during probing,
    it is gracefully omitted without raising exceptions or breaking other detections."""
    mock_meta = [
        {"device_id": 0, "name": "Working Camera", "bus_id": r"\\?\usb#1", "is_physical": True},
        {"device_id": 1, "name": "Busy or Disconnected Camera", "bus_id": r"\\?\usb#2", "is_physical": True},
    ]
    monkeypatch.setattr("src.camera.inspect_platform_cameras", lambda: mock_meta)

    class MockCap:
        def __init__(self, idx, *args, **kwargs):
            self.idx = idx

        def isOpened(self):
            return self.idx == 0

        def read(self):
            if self.idx == 0:
                return True, np.zeros((480, 640, 3), dtype=np.uint8)
            return False, None

        def release(self):
            pass

    monkeypatch.setattr(cv2, "VideoCapture", lambda idx, *a, **k: MockCap(idx))

    devices = detect_available_cameras(max_devices=6, include_synthetic=True, include_virtual=False)
    dev_names = [d.name for d in devices]
    assert any("Working Camera" in name for name in dev_names)
    assert not any("Busy" in name for name in dev_names)
    assert any("Synthetic Feed" in name for name in dev_names)


def test_directshow_com_enumeration_contract():
    """Verifies that enumerate_windows_dshow_devices returns the expected structure on Windows."""
    import sys
    from src.camera import enumerate_windows_dshow_devices

    devices = enumerate_windows_dshow_devices()
    assert isinstance(devices, list)
    if sys.platform.startswith("win"):
        # On Windows host, verify dict structure if any DirectShow devices are present
        for d in devices:
            assert "device_id" in d
            assert isinstance(d["device_id"], int)
            assert "name" in d
            assert isinstance(d["name"], str)
            assert "is_physical" in d
            assert isinstance(d["is_physical"], bool)

