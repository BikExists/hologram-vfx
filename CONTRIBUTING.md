# Contributing to Holographic VFX

Thank you for your interest in contributing to **Holographic VFX**! This document provides guidelines and workflows for setting up your development environment, running tests, writing code, and building releases safely.

---

## 1. Development Setup

### Prerequisites
* **Python**: 64-bit Python 3.10 or 3.11 (Python 3.11.16 is the verified baseline).
* **Git**: Installed and configured.
* **OS**: Windows 10/11 is the primary standalone target platform; macOS and Linux source execution is supported for testing.

### Setup Instructions
```powershell
# 1. Clone the repository
git clone https://github.com/BikExists/hologram-vfx.git
cd hologram-vfx

# 2. Create a virtual environment
python -m venv .venv

# 3. Activate the virtual environment
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On Windows (Command Prompt):
.venv\Scripts\activate.bat
# On macOS / Linux:
source .venv/bin/activate

# 4. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 2. Running the Application

```powershell
# Run with default settings (Camera 0, 640x480, Cyan theme)
python main.py

# Run in synthetic mode (no physical webcam required)
python main.py --synthetic

# Run with a specific theme and resolution
python main.py --theme violet --width 1280 --height 720

# Run a headless performance benchmark for 60 frames
python main.py --synthetic --headless --benchmark 60
```

---

## 3. Running Automated Tests

All pull requests and changes must pass the complete test suite:

```powershell
# Run all unit tests
pytest -v

# Run a specific test file
pytest tests/test_async_tracking.py -v

# Run tests with short summary output
pytest -q
```

### Writing New Tests
* Place new tests under `tests/test_<feature>.py`.
* Avoid requiring physical hardware in automated tests: use `synthetic_mode=True` or `headless=True` for tests that instantiate `HolographicVFXApp`.
* Always clean up temporary files using `tmp_path` fixtures.

---

## 4. Coding & Architecture Guidelines

1. **Decoupled Architecture**:
   * Never introduce blocking or synchronous operations (such as disk I/O, network requests, or long sleep loops) into the visual rendering loop in `src/app.py`.
   * CPU-intensive inference must be delegated to the background worker (`src/tracking_worker.py`).
2. **Local-First & Privacy Standards**:
   * Holographic VFX is designed as a local-first application.
   * **Do not add network calls, telemetry, cloud services, or external analytics.**
   * Camera frames must only reside in volatile memory (NumPy arrays). See [docs/PRIVACY.md](docs/PRIVACY.md).
3. **Filesystem Safety**:
   * Never write user files or screenshots directly to the repository or current working directory.
   * Always route user outputs through `src/paths.py` (`get_user_capture_dir()`).
   * When writing files on Windows, use Unicode-safe byte writing (`Path.write_bytes()`) rather than narrow C runtime calls.
4. **Third-Party Licenses & Project Status**:
   * New dependencies must be compatible with existing third-party licenses (see [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md)).
   * The repository currently has no explicit project license committed; formal license adoption is reserved for the maintainer.
5. **Platform Boundaries**:
   * Windows standalone packaging is the current hardened release target.
   * macOS standalone packaging is currently paused pending physical Apple Silicon validation; do not commit speculative macOS packaging scripts.

---

## 5. Building the Windows Standalone Package

To verify standalone packaging locally:

### Requirements:
* Inno Setup 6 installed (for compiling `Setup.exe`).

### Build Command:
```powershell
# Compiles PyInstaller bundle, portable ZIP, and Inno Setup installer:
python packaging\build_windows.py --all
```

### Repository Hygiene (Do NOT Commit Artifacts):
* Build artifacts are output to `dist/` and `build/`.
* These folders, along with `.exe` and `.zip` files, are strictly ignored by `.gitignore`.
* **Never force-add or commit binaries to Git.**

---

## 6. Reporting Issues & Proposing Features

* **Bug Reports**: If you find a bug, please check [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) first. If unresolved, open a GitHub Issue using the **Bug Report** template and include your `crash_log.txt`.
* **Feature Requests**: Open an issue using the **Feature Request** template describing the proposed capability and user interaction.
