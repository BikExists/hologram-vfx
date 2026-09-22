"""Tests for fatal crash report generation and crash dialog handling."""

import os
from pathlib import Path
import sys
import pytest

from main import _handle_fatal_exception
from src.paths import get_crash_log_path


def test_handle_fatal_exception_creates_crash_log(tmp_path, monkeypatch):
    """Verify that _handle_fatal_exception persists crash details to disk in headless mode."""
    monkeypatch.setattr("src.paths.get_user_capture_dir", lambda: tmp_path)

    test_exc = ValueError("Intentional unit test crash error")

    # Run handler in headless mode so no GUI popup is displayed
    _handle_fatal_exception(test_exc, headless=True)

    log_path = tmp_path / "crash_log.txt"
    assert log_path.exists()

    content = log_path.read_text(encoding="utf-8")
    assert "Holographic VFX - Fatal Application Crash Report" in content
    assert "ValueError" in content
    assert "Intentional unit test crash error" in content
    assert sys.platform in content
