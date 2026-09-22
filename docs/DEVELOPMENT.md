# Holographic VFX Architecture & Developer Guide

A technical reference guide to the architecture, pipeline lifecycle, subsystem design, and build processes of the **Holographic VFX System**.

---

## 1. High-Level Architecture Overview

Holographic VFX is structured as a decoupled multi-threaded spatial computing pipeline built on Python, MediaPipe, NumPy, and OpenCV.

```
                  ┌──────────────────────────────────────────────┐
                  │                 main.py                      │
                  │   Entry point, CLI args, crash interceptor   │
                  └──────────────────────┬───────────────────────┘
                                         │ instantiates & runs
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │             HolographicVFXApp                │
                  │        (src/app.py - Master Pipeline)        │
                  └───────┬──────────────┬──────────────┬────────┘
                          │              │              │
           ┌──────────────┘              │              └──────────────┐
           ▼                             ▼                             ▼
┌────────────────────┐        ┌────────────────────┐        ┌────────────────────┐
│   CameraSelector   │        │  AsyncHandTracker  │        │ HolographicObject- │
│  (src/camera.py)   │        │(src/tracking_      │        │      Manager       │
│ Physical/Synthetic │        │     worker.py)     │        │(src/objects/       │
│ camera discovery & │        │ Decoupled worker   │        │    manager.py)     │
│ device abstraction │        │ latest-frame-wins  │        │ 6 Procedural 3D    │
└────────────────────┘        └──────────┬─────────┘        │ object interfaces  │
                                         │                  └──────────┬─────────┘
                                         ▼                             │
                              ┌────────────────────┐                   │
                              │    HandTracker     │                   │
                              │(src/hand_tracker.py│                   │
                              │ 21-point MediaPipe │                   │
                              │ inference & joints │                   │
                              └──────────┬─────────┘                   │
                                         │                             │
                                         ▼                             ▼
                              ┌──────────────────────────────────────────────┐
                              │            Interaction Subsystems            │
                              │  • src/gestures.py (Pinch, Dwell, Openness)  │
                              │  • src/interaction.py (Single & Dual Hand)   │
                              │  • src/ui/manager.py (Cursor, Menu, Welcome) │
                              └──────────────────────┬───────────────────────┘
                                                     │
                                                     ▼
                              ┌──────────────────────────────────────────────┐
                              │             Rendering & VFX Stage            │
                              │  • src/vfx/orb_renderer.py (Core procedural) │
                              │  • src/vfx/aura.py (Quantized radial cache)  │
                              │  • src/vfx/particles.py (Keplerian orbits)   │
                              │  • src/vfx/hud.py (Sci-Fi HUD & Gauges)      │
                              │  • src/vfx/presenter.py (HighGUI Display)    │
                              └──────────────────────────────────────────────┘
```

---

## 2. Application Lifecycle

The core loop in `HolographicVFXApp.run()` operates through well-defined sequential stages per tick:

1. **Capture Stage**:
   * `CameraSelector.read()` retrieves the raw BGR video frame from the active hardware or synthetic feed.
2. **Tracking Submission Stage**:
   * If running in decoupled mode (default), a thread-safe copy of the frame is submitted to `AsyncHandTracker.submit_frame()`. The background thread picks up the frame using a single-slot buffer policy.
3. **Tracking Consumption Stage**:
   * `AsyncHandTracker.get_latest_result()` retrieves the most recently completed hand landmarks without blocking. If landmarks exceed `max_stale_ms=200.0`, they are decayed to avoid frozen ghost hands.
4. **Interaction Stage**:
   * Hand landmarks are mapped into viewport coordinates.
   * `GestureEstimator` calculates pinch distance and openness metrics with hysteresis.
   * If both hands are present, `compute_two_hand_distance`, `compute_two_hand_angle`, and `compute_two_hand_midpoint` derive two-hand spatial transforms in `OrbController`.
   * `UIManager` updates the dwell timer in the top-right trigger zone. If the menu is open, object transforms are locked and hand inputs are routed to UI button cursors.
5. **Rendering & Compositing Stage**:
   * The active object (Orb, Cube, Planet, Orchid, Bhondu, or Jellyfish) draws its geometry, scanlines, and beacons.
   * Prebaked aura layers (`AuraCache`) blend glows efficiently using in-place integer arithmetic.
   * Particles update their physical velocities and life counters.
   * `HUD` composites telemetry text, theme badges, and skeleton joint lines.
6. **Presentation Stage**:
   * The composite frame is passed to `cv2.imshow()`.
   * `cv2.waitKey(1)` polls for keyboard events (`Q`, `ESC`, `1`..`6`, `C`, `V`, `S`, `M`, `Tab`, `I`, `R`, `H`).
7. **Clean Shutdown Stage**:
   * `app.close()` releases camera handles, signals the tracking worker thread to shut down, joins the thread within a 1.0s timeout, and destroys OpenCV display windows.

---

## 3. Subsystem Breakdown

### 3.1. Camera Subsystem (`src/camera.py`)
* **`CameraSelector`**: Provides unified device discovery, validation, and hot-switching.
* **DirectShow & Media Foundation**: On Windows, scans video indices `0..5`. Filters out software drivers (e.g., Windows Phone Link virtual cameras) to prevent application hangs.
* **`SyntheticCamera`**: Generates procedural animated test frames for CI, headless benchmarks, and camera-less environments.

### 3.2. Asynchronous Hand Tracking (`src/tracking_worker.py` & `src/hand_tracker.py`)
* **`HandTracker`**: Low-level MediaPipe wrapper configured with `min_detection_confidence=0.6` and `min_tracking_confidence=0.6`. Uses a 4-frame grace period filter to smooth out momentary camera dropouts.
* **`AsyncHandTracker`**:
  * **Dedicated Worker Thread**: Isolates CPU-heavy MediaPipe inference onto a dedicated background thread.
  * **Single-Slot 'Latest-Frame-Wins'**: Eliminates FIFO queues and backlogs. If the camera captures faster than MediaPipe infers, newer frames overwrite older pending frames without queuing latency.
  * **Exception Resilience**: MediaPipe calls are wrapped in `try ... except Exception:` with a 2.0s logging cooldown to prevent worker thread termination on malformed camera frames.
  * **Staleness Protection**: Flags landmarks older than 200 ms as stale.

### 3.3. Interaction & Gesture Engine (`src/gestures.py` & `src/interaction.py`)
* **`GestureEstimator`**:
  * **Pinch Detection**: Normalized Euclidean distance between landmark 4 (`THUMB_TIP`) and landmark 8 (`INDEX_FINGER_TIP`). Grab threshold: `0.38`; Release threshold: `0.52` (hysteresis prevents jitter).
  * **Hand Openness**: Normalized perimeter and finger-spread calculation mapping from `0.0` (fist) to `1.0` (wide palm).
* **`OrbController`**:
  * **Standard Mode**: Midpoint anchor position, inter-hand distance scaling, and tilt-angle rotation.
  * **Independent Mode**: Primary hand moves; secondary hand controls scale and background UI parameters.

### 3.4. Procedural Objects System (`src/objects/`)
* **`BaseHolographicObject`**: Abstract interface defining contract methods: `update()`, `render()`, `set_scale()`, `set_rotation()`, `set_theme()`, `reset_position()`.
* **Current Objects**:
  1. `HolographicOrb`: Gyroscopic rings, plasma tethers, particle burst shockwaves.
  2. `HolographicCube`: 3D rotation matrix projection, depth-sorted wireframe, glowing vertex nodes.
  3. `HolographicPlanet`: Limb atmospheric glow, latitude bands, tilted rings, orbiting moon.
  4. `GhostOrchid`: Procedural petal curves scaling dynamically with hand openness.
  5. `BhonduFace`: Stylized geometric face hologram with animated eyes and reactive expressions.
  6. `BioluminescentJellyfish`: Undulating umbrella dome with sinusoidal tentacle physics.
* **`HolographicObjectManager`**: Manages state transfer (position, scale, rotation) seamlessly when switching objects.

### 3.5. Touchless Holographic UI (`src/ui/`)
* **`TriggerZone`**: Top-right corner bounding box with dwell charging. An open palm held for 0.6s toggles the menu.
* **`HolographicMenu`**: Translucent glass pane with glowing action items (objects, themes, cameras).
* **`HandCursor`**: Reticle tracking index finger tip with pinch-to-click detection.
* **Input Isolation**: Strict state machine prevents gestures from moving the background object while manipulating UI items.

### 3.6. Filesystem & User Paths (`src/paths.py`)
* **`get_user_capture_dir()`**: Resolves `%USERPROFILE%\Pictures\HolographicVFX\`. Falls back to `~/.holographic_vfx/captures/` and system `%TEMP%`.
* **Unicode-Safe Persistence**: Uses `cv2.imencode('.png', frame)` and `Path.write_bytes()` to guarantee wide-character UTF-16 path safety on Windows.
* **Collision Avoidance**: Appends `_1`, `_2` counter suffixes when multiple captures occur within the same second.
* **Crash Reporting**: `write_crash_log()` persists unhandled fatal exception traces to disk.

---

## 4. Testing & Verification Guide

The project includes an automated regression test suite covering all modules:

```powershell
# Run the complete test suite (197 tests)
pytest -v

# Run a targeted test module
pytest tests/test_async_tracking.py -v
pytest tests/test_paths.py -v
pytest tests/test_holographic_ui.py -v

# Run headless performance benchmark for 120 frames
python main.py --synthetic --headless --benchmark 120
```

### Test Suite Organization:
* `tests/test_objects.py` & `test_expanded_objects.py`: Object interface contracts and rendering bounds.
* `tests/test_async_tracking.py`: Thread lifecycle, latest-frame-wins, and exception resilience.
* `tests/test_paths.py`: Unicode path persistence, collision avoidance, and directory resolution.
* `tests/test_crash_handling.py`: Fatal crash reporting and headless isolation.
* `tests/test_menu_trigger_zone.py` & `test_holographic_ui.py`: Dwell gestures, menu states, and cursor clicks.
* `tests/test_two_hand_interaction.py` & `test_dual_hand_mode.py`: Multi-hand transformations and mode transitions.
* `tests/test_camera_selector.py` & `test_camera_robustness.py`: Device discovery and virtual camera filtering.

---

## 5. Standalone Packaging Workflow (Windows)

The Windows standalone application is built using PyInstaller (`--onedir + --windowed`) and Inno Setup 6.

### Prerequisites:
1. Python 3.10 or 3.11 (64-bit).
2. Virtual environment with dependencies installed: `pip install -r requirements.txt`.
3. [Inno Setup 6](https://jrsoftware.org/isdl.php) installed (for compiling the installer).

### Clean Build Execution:
```powershell
# Compiles PyInstaller executable, generates Portable ZIP, and compiles Inno Setup Installer:
python packaging\build_windows.py --all
```

### Build Artifacts:
Build outputs are placed in `dist/` (which is excluded from Git via `.gitignore`):
* `dist\HolographicVFX\`: Standalone application folder.
* `dist\HolographicVFX-v0.1.1-dev-Windows-x64.zip`: Portable distribution archive.
* `dist\HolographicVFX-v0.1.1-dev-Windows-x64-Setup.exe`: Inno Setup installer.

> **Important**: Never commit `dist/`, `build/`, `.exe`, or `.zip` files to the Git repository.
