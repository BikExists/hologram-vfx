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
    get_crash_log_path,
    write_crash_log,
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
    empty_frame = np.zeros((0, 0, 3), dtype=np.uint8)
    assert save_screenshot(empty_frame) is None


def test_save_screenshot_unicode_paths(tmp_path):
    """Verify screenshot saving succeeds across various non-ASCII and Unicode paths.

    Tests accented characters, German umlauts, Cyrillic, and CJK characters.
    """
    dummy_frame = np.zeros((64, 64, 3), dtype=np.uint8)
    dummy_frame[:, :] = (128, 64, 255)

    test_cases = [
        "café_au_lait_éèê",
        "münchen_grüße_äöüß",
        "Скриншот_тест_123",
        "日本語_中文_한국어",
    ]

    for dirname in test_cases:
        target_dir = tmp_path / dirname
        target_file = target_dir / "capture_test.png"

        saved_path = save_screenshot(dummy_frame, target_path=target_file)
        assert saved_path is not None, f"Failed to save screenshot in Unicode dir: {dirname}"
        saved_file = Path(saved_path)
        assert saved_file.exists()
        assert saved_file.stat().st_size > 0

        # Verify readability via byte stream decoding
        file_bytes = saved_file.read_bytes()
        nparr = np.frombuffer(file_bytes, np.uint8)
        decoded = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        assert decoded is not None
        assert decoded.shape == (64, 64, 3)


def test_generate_screenshot_path_collision_avoidance(tmp_path, monkeypatch):
    """Verify collision avoidance appends incrementing counter suffix on duplicate timestamps."""
    monkeypatch.setattr("src.paths.get_user_capture_dir", lambda: tmp_path)

    # First generation creates base name
    p1 = generate_screenshot_path(prefix="collision_test")
    p1.touch()
    assert p1.exists()

    # Second generation detects collision and appends _1
    p2 = generate_screenshot_path(prefix="collision_test")
    assert p2 != p1
    assert p2.name.endswith("_1.png")
    p2.touch()

    # Third generation detects collision and appends _2
    p3 = generate_screenshot_path(prefix="collision_test")
    assert p3 != p1
    assert p3 != p2
    assert p3.name.endswith("_2.png")


def test_crash_log_writing_and_path(tmp_path, monkeypatch):
    """Verify crash log path resolution and safe UTF-8 file writing."""
    monkeypatch.setattr("src.paths.get_user_capture_dir", lambda: tmp_path)

    log_path = get_crash_log_path()
    assert log_path == tmp_path / "crash_log.txt"

    test_report = "Error: TestException: something failed\nTraceback: line 42\nUnicode: 測試_тест"
    written_path = write_crash_log(test_report)

    assert written_path is not None
    assert written_path.exists()
    content = written_path.read_text(encoding="utf-8")
    assert content == test_report
