# Changelog

All notable changes and architectural milestones for **Holographic VFX** are documented here based on repository commit history.

The project follows semantic versioning principles with development pre-releases (`v0.x.x-dev`).

---

## [v0.1.1-dev] - 2026-09-22

### Phase B: Windows Standalone Release Hardening
* **Unicode Screenshot Path Safety**: Replaced OpenCV `cv2.imwrite()` narrow-character calls with in-memory `cv2.imencode()` + Python's wide-character UTF-16 `Path.write_bytes()`. Verified on paths containing French accents, German umlauts, Cyrillic, and CJK characters.
* **Screenshot Collision Avoidance**: Implemented automatic incrementing counter suffixes (`_1`, `_2`, ...) in `generate_screenshot_path()` to prevent overwriting rapid captures taken within the same second.
* **Windowed Crash Interception & Native Dialog**: Added `_handle_fatal_exception()` in `main.py`. Writes diagnostic crash reports to `%USERPROFILE%\Pictures\HolographicVFX\crash_log.txt` (with `%TEMP%` fallback) and displays native Win32 `MessageBoxW` error dialogs in windowed mode while cleanly suppressing them in headless mode.
* **Tracking Worker Resilience**: Guarded MediaPipe CPU inference in `_worker_loop()` with exception containment. Transient inference glitches no longer kill the background worker thread; tracking self-heals immediately on the next frame with a 2.0s error logging cooldown.
* **Dependency Footprint Optimization**: Excluded `tkinter` from PyInstaller packaging in `HolographicVFX.spec`.
* **Automated Regression Suite**: Expanded test coverage from 191 to 197 unit tests passing cleanly.

### Mission 14.1: Windows Standalone UX Hardening
* **Welcome Screen Dismissal**: Enhanced welcome tutorial overlay to dismiss either by presenting a hand to the camera or by pressing `[Space]` / `[Enter]`.
* **Window Close Debounce**: Implemented debounce logic for window property queries to prevent spurious shutdowns during rapid mouse movement over the window frame.
* **Per-User Installer**: Configured Inno Setup installer with `PrivilegesRequired=lowest` for seamless non-elevated installation into `%LOCALAPPDATA%\Programs\HolographicVFX`.

---

## [v0.1.0-dev] - 2026-09-21

### Mission 14: Windows Standalone Distribution & Packaging
* **Inno Setup Installer**: Created `packaging/installer.iss` compiling a standalone installer with Start Menu shortcuts, optional Desktop shortcut, and clean uninstaller (`unins000.exe`).
* **Portable Distribution Archive**: Automated compilation of standalone `.zip` archives.
* **App Branding**: Embedded custom high-resolution application icon (`assets/icon.ico`) into the executable and installer.
* **Build Automation**: Created `packaging/build_windows.py` for reproducible one-step compilation.

### Mission 13: Windows Standalone Packaging Foundation
* **PyInstaller Integration**: Established `HolographicVFX.spec` in `--onedir + --windowed` mode (`console=False`).
* **Model Bundling**: Bundled all MediaPipe hand tracking `.tflite`, `.binarypb`, and `.task` files into standalone package.
* **User-Writable Path Resolution**: Created `src/paths.py` ensuring screenshots are saved to `%USERPROFILE%\Pictures\HolographicVFX\` regardless of working directory permissions.

---

## [pre-standalone-v1] - 2026-09-21

### Pre-Standalone Development Milestones (ae6b7c5)

#### Mission 12: Decoupled / Asynchronous Hand Tracking (`7ed09de`)
* Created `AsyncHandTracker` isolating MediaPipe inference onto a dedicated background worker thread (`HandTrackingWorker`).
* Implemented single-slot "latest-frame-wins" handoff policy, eliminating FIFO latency backlogs.
* Added staleness detection (`max_stale_ms=200.0`) to avoid frozen ghost tracking.

#### Mission 11: Touchless Holographic Menu & Expanded Objects (`1b808eb`)
* Added touchless holographic menu triggered by open-palm dwell (0.6s) in the top-right corner zone.
* Implemented holographic fingertip cursor with pinch-to-click detection.
* Expanded object library to 6 procedural holograms: Energy Orb, Cyber Cube, Holographic Planet, Ghost Orchid, Bhondu Face, and Bioluminescent Jellyfish.

#### Mission 10: Aspect-Ratio Aware Presentation (`1033432`)
* Added dynamic aspect-ratio support conforming cleanly to 16:9 widescreen and 4:3 standard camera streams.
* Added viewport boundary confinement preventing objects from clipping outside the visible frame.

#### Mission 9: Tracking & Rendering Performance Optimizations (`1fd5460`, `735e28a`)
* Subsampled tracking resolution to 640x480 while preserving native display presentation.
* Implemented `AuraCache` with quantized integer prebaking for radial glow shaders.

#### Mission 6–7: Multi-Hand Interaction (`55aeef1`, `8ae0890`)
* Added two-hand spatial transforms: midpoint anchoring, distance-based scaling, and tilt-angle rotation.
* Introduced **Standard Two-Hand Mode** vs **Independent Dual-Hand Mode** (cycled via `[Tab]` / `[I]`).

#### Mission 2–5: Multi-Camera Architecture & Hardware Robustness (`06941b4` – `4e4ab18`)
* Implemented `CameraSelector` with device discovery, DirectShow/MSMF filtering, and runtime hot-switching (`[V]`).
* Added `SyntheticCamera` procedural test generator for automated testing and camera-less environments.
* Filtered out virtual devices (Windows Phone Link) to prevent camera hang-ups.

#### Mission 1: Core Holographic VFX Prototype (`7d98989`)
* Initial real-time MediaPipe hand tracking pipeline with 21 3D joint landmarks.
* Procedural Energy Orb with gyroscopic rings, Keplerian particle cloud, and plasma pinch tethers.
* Pinch-to-grab gesture and open-palm scale expansion.
