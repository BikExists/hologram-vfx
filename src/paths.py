"""Filesystem path utilities for user-writable data and screenshots.

Ensures that standalone installations (e.g. in C:\\Program Files or /Applications)
always direct user outputs to a reliable, user-writable directory without
relying on current working directory permissions or repository paths.
"""

import os
from pathlib import Path
import time
from typing import Optional
import cv2
import numpy as np


def get_user_capture_dir() -> Path:
    """Returns the dedicated user-writable directory for application screenshots.

    Resolution Strategy:
    1. Standard user 'Pictures/HolographicVFX' directory.
    2. Fallback to user home '.holographic_vfx/captures' if Pictures is unavailable.
    3. Safe last-resort fallback to system temp directory.
    """
    try:
        pictures_dir = Path.home() / "Pictures" / "HolographicVFX"
        pictures_dir.mkdir(parents=True, exist_ok=True)
        return pictures_dir
    except Exception:
        pass

    try:
        app_data_dir = Path.home() / ".holographic_vfx" / "captures"
        app_data_dir.mkdir(parents=True, exist_ok=True)
        return app_data_dir
    except Exception:
        pass

    import tempfile
    fallback = Path(tempfile.gettempdir()) / "HolographicVFX" / "captures"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def generate_screenshot_path(prefix: str = "hologram_capture") -> Path:
    """Generates a timestamped screenshot file path with collision avoidance.

    If a file with the timestamp already exists, appends an incrementing counter
    suffix (_1, _2, etc.) to prevent overwriting rapid consecutive captures.
    """
    capture_dir = get_user_capture_dir()
    timestamp = int(time.time())
    candidate = capture_dir / f"{prefix}_{timestamp}.png"
    if not candidate.exists():
        return candidate

    counter = 1
    while True:
        candidate = capture_dir / f"{prefix}_{timestamp}_{counter}.png"
        if not candidate.exists():
            return candidate
        counter += 1


def save_screenshot(
    frame: np.ndarray,
    prefix: str = "hologram_capture",
    target_path: Optional[Path] = None,
) -> Optional[str]:
    """Safely writes a video frame to disk in the user capture directory.

    Uses Unicode-safe image encoding and byte-writing to guarantee compatibility
    with non-ASCII / Unicode paths (accented characters, Cyrillic, CJK) on Windows.

    Returns:
        The absolute path to the saved screenshot file as a string, or None if failed.
    """
    if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
        return None

    try:
        dest_path = target_path if target_path is not None else generate_screenshot_path(prefix=prefix)
        dest_path = Path(dest_path)
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        success, encoded = cv2.imencode(".png", frame)
        if not success or encoded is None:
            return None

        dest_path.write_bytes(encoded.tobytes())
        return str(dest_path.resolve())
    except Exception as e:
        print(f"[Warning] Failed to save screenshot: {e}")
        return None


def get_crash_log_path() -> Path:
    """Returns the dedicated path for writing fatal crash reports."""
    capture_dir = get_user_capture_dir()
    return capture_dir / "crash_log.txt"


def write_crash_log(report_text: str) -> Optional[Path]:
    """Writes a fatal error diagnostic log to a reliable user-writable location."""
    try:
        log_path = get_crash_log_path()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(report_text, encoding="utf-8", errors="replace")
        return log_path
    except Exception:
        try:
            import tempfile
            fallback = Path(tempfile.gettempdir()) / "HolographicVFX_crash_log.txt"
            fallback.write_text(report_text, encoding="utf-8", errors="replace")
            return fallback
        except Exception:
            return None
