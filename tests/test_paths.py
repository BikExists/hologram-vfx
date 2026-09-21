"""Tests for user-writable path resolution and screenshot persistence."""

import os
from pathlib import Path
import cv2
import numpy as np
import pytest

from src.paths import (
    get_user_capture_dir,
    generate_screenshot_path,
    save_screenshot,
)


def test_get_user_capture_dir_exists_and_is_dir():
    """Verify that get_user_capture_dir returns an existing, writable directory."""
    capture_dir = get_user_capture_dir()
    assert isinstance(capture_dir, Path)
    assert capture_dir.exists()
    assert capture_dir.is_dir()


def test_generate_screenshot_path_structure():
    """Verify filename format and placement in the user capture directory."""
    custom_prefix = "test_capture"
    path = generate_screenshot_path(prefix=custom_prefix)

    assert isinstance(path, Path)
    assert path.parent == get_user_capture_dir()
    assert path.name.startswith(custom_prefix)
    assert path.suffix == ".png"


def test_save_screenshot_writes_valid_image():
    """Verify end-to-end screenshot writing and OpenCV image readability."""
    dummy_frame = np.zeros((120, 160, 3), dtype=np.uint8)
    dummy_frame[30:90, 40:120] = (0, 255, 255)  # Yellow rectangle

    saved_path = save_screenshot(dummy_frame, prefix="pytest_temp_capture")
    assert saved_path is not None
    assert os.path.exists(saved_path)

    try:
        # Verify written image can be read back and has identical dimensions
        loaded = cv2.imread(saved_path)
        assert loaded is not None
        assert loaded.shape == (120, 160, 3)
    finally:
        # Clean up temporary test file
        if os.path.exists(saved_path):
            try:
                os.remove(saved_path)
            except OSError:
                pass


def test_save_screenshot_handles_invalid_frame_gracefully():
    """Verify that invalid frames return None without raising unhandled exceptions."""
    result = save_screenshot(None)
    assert result is None
