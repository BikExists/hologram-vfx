"""Unit and integration tests for camera selection and device management."""

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
    devices = detect_available_cameras(max_devices=2, include_synthetic=True)
    assert len(devices) >= 1
    # Check structure
    for dev in devices:
        assert isinstance(dev, CameraDeviceInfo)
        assert isinstance(dev.name, str)
        assert isinstance(dev.device_id, int)
        assert isinstance(dev.is_synthetic, bool)

    # Synthetic should be present when requested
    assert any(d.is_synthetic for d in devices)


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
