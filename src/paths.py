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
    """Generates a timestamped screenshot file path in the user-writable directory."""
    capture_dir = get_user_capture_dir()
    timestamp = int(time.time())
    return capture_dir / f"{prefix}_{timestamp}.png"


def save_screenshot(frame: np.ndarray, prefix: str = "hologram_capture") -> Optional[str]:
    """Safely writes a video frame to disk in the user capture directory.

    Returns:
        The absolute path to the saved screenshot file, or None if save failed.
    """
    try:
        target_path = generate_screenshot_path(prefix=prefix)
        success = cv2.imwrite(str(target_path), frame)
        if success:
            return str(target_path)
        return None
    except Exception as e:
        print(f"[Warning] Failed to save screenshot: {e}")
        return None
