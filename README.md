# Hand-Tracked Holographic VFX System

A high-performance real-time interactive computer vision application that tracks a user's hand via webcam to manipulate a virtual glowing holographic energy orb.

---

## Features

- **Live Webcam Pipeline**: Real-time camera feed capture with horizontal mirroring for an intuitive mirror-like interaction experience. Includes automatic fallback to DirectShow backend on Windows.
- **Robust 21-Landmark Hand Tracking**: Uses MediaPipe to track the wrist, knuckles, and all 5 fingertips in 3D. Includes a lost-tracking grace period to prevent flickering during rapid hand motions.
- **Scale-Invariant Pinch-to-Grab**: Calculates pinch distance normalized by the rigid anatomical palm scale (Wrist to Middle MCP span). Features Schmitt-trigger hysteresis to eliminate grab/release boundary jitter.
- **Dynamic Hand Openness Sizing**: Evaluates normalized fingertip extension across all fingers. Curling your hand into a fist shrinks the orb down to a compact core, while spreading fingers wide expands it into a massive celestial energy sphere.
- **Multi-Tier Holographic VFX Engine**:
  - **Radial Glow**: Vectorized exponential falloff with white-hot core, inner glowing mantle, and diffuse atmospheric halo.
  - **3D Rotating Gyroscopic Rings**: Tri-axial orbital rings with elliptical 3D perspective projection, orbital tick marks, and rotating dashed sci-fi reticles.
  - **Orbiting 3D Particle Cloud**: 60+ sparkles orbiting in 3D space with depth-based perspective scaling, alpha modulation, and transient radial burst explosions on grab/release.
  - **Electric Plasma Tether**: Fractal lightning arcs dynamically connecting the pinch point (thumb & index fingertips) to the orb center when grabbed.
  - **Shockwave Ripples**: Expanding holographic energy ripples triggered upon grabbing or releasing the orb.
  - **Scanlines & Hologram Flicker**: Subtle holographic interference pattern for a physical sci-fi aesthetic.
- **One-Euro & EMA Jitter Filtering**: High precision and zero jitter when holding the hand still, with adaptive low latency during rapid movement.
- **Sci-Fi Heads-Up Display (HUD)**: Glass-morphic UI showing live FPS, frame latency, tracking status, hand openness gauge bar, and keyboard shortcuts.
- **Universal Cross-Platform Camera Architecture**:
  - **Platform-Optimal Backends**: Dynamic backend selection using DirectShow (`CAP_DSHOW`) on Windows, Video4Linux (`CAP_V4L2`) on Linux, and AVFoundation (`CAP_AVFOUNDATION`) on macOS, with universal `CAP_ANY` fallback.
  - **Dynamic Resolution Adaptation**: Viewport boundary margins, orb physics, and HUD scale automatically to native camera capabilities (e.g. 720p, 1080p, 480p).
  - **Multi-Camera Device Fallback**: Automatically tries alternative physical cameras if Camera 0 is absent or busy, gracefully falling back to procedural Synthetic mode if no hardware is available.
  - **Mid-Stream Disconnection Recovery**: Transparently recovers and transitions to synthetic feed if a physical USB webcam is disconnected while running.
  - **Seamless Camera Switching**: Switch input sources at runtime via key `[V]` or direct jump `[1-9]`.
- **Universal Holographic Object System**:
  - **1 → Energy Orb**: The reference holographic celestial sphere featuring multi-layer exponential radial glow, tri-axial rotating gyroscopic rings, Keplerian orbital sparkles, electric plasma tethers, and shockwaves.
  - **2 → Cyber Cube**: A high-tech 3D rotating wireframe cube featuring perspective projection, glowing edges, 6 depth-sorted translucent faceted faces with scanlines, luminous vertex node beacons, 3D orbital particles, and pinch tethers.
  - **3 → Holographic Planet**: A planetary body with atmospheric limb-darkening glow, rotating latitude bands and wireframe meridians, tilted concentric Saturn-like rings with depth-sorted front/back occlusion, and an orbiting moon with a particle dust trail.
  - **Seamless State Transfer**: Preserves spatial position, velocity, openness scale, and theme when switching between objects at runtime.
  - **Unified Object Contract**: Extensible base class ensuring all current and future holographic objects operate in unified pixel coordinates with full pinch-grab, spring physics, and openness scaling support.
- **Multiple Color Themes**:
  - **Cyber Cyan** (Classic electric hologram)
  - **Solar Flare** (Warm golden amber star)
  - **Neon Violet** (Synthwave cyberpunk magenta)
  - **Emerald Matrix** (Digital phosphor green)

---

## Project Structure

```
antigravity/
├── src/
│   ├── __init__.py
│   ├── filters.py          # OneEuroFilter, LowPassFilter, PointFilter, EMAFilter
│   ├── gestures.py         # Scale-invariant pinch hysteresis and openness estimation
│   ├── hand_tracker.py     # MediaPipe Hands integration, landmark extraction & skeleton overlay
│   ├── interaction.py      # OrbController state machine, spring-damper kinematics, boundaries
│   ├── camera.py           # Cross-platform VideoCapture manager, selector, and SyntheticCamera
│   ├── app.py              # Main HolographicVFXApp loop orchestrating all subsystems
│   ├── objects/            # Extensible Universal Holographic Object System
│   │   ├── __init__.py     # Module exports
│   │   ├── base.py         # Common BaseHolographicObject contract in pixel coordinates
│   │   ├── orb.py          # HolographicOrb (multi-layer glow, 3D rings, particles, tethers)
│   │   ├── cube.py         # HolographicCube (3D rotation, wireframe edges, scanlines, faces)
│   │   ├── planet.py       # HolographicPlanet (limb glow, bands, rings, orbiting moon)
│   │   └── manager.py      # HolographicObjectManager & runtime object switcher
│   └── vfx/
│       ├── __init__.py
│       ├── color_themes.py # 4 holographic color themes and palette definitions
│       ├── particles.py    # 3D Keplerian orbital particles and burst physics
│       ├── orb_renderer.py # Multi-layer exponential glow, rotating rings, tethers, shockwaves
│       └── hud.py          # Sci-fi glass panels, FPS counter, openness gauge, object HUD
├── tests/
│   ├── __init__.py
│   ├── test_camera_robustness.py # Cross-platform backend, fallback, and disconnect tests
│   ├── test_camera_selector.py   # Camera detection, cycling, and device indexing tests
│   ├── test_filters.py     # Smoothing filter verification
│   ├── test_gestures.py    # Gesture math, pinch hysteresis, and openness tests
│   ├── test_vfx.py         # VFX rendering, particles, color themes, and ROI clipping tests
│   ├── test_interaction.py # Orb kinematics, grab/release states, and viewport boundaries
│   ├── test_objects.py     # Holographic object contract, switching, and rendering tests
│   └── test_integration.py # Headless end-to-end synthetic pipeline integration test
├── main.py                 # CLI entry point supporting live camera, synthetic, and benchmark modes
├── requirements.txt        # Frozen package dependencies
└── README.md               # Documentation and user manual
```

---

## Installation

Ensure Python 3.10 or 3.11 is available (or use `uv`):

```bash
# Create virtual environment
uv venv .venv --python 3.11
# Or: python -m venv .venv

# Activate environment
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## How to Run

### 1. Interactive Webcam Mode (Default)
Launch the application with your default webcam:

```bash
python main.py
```

To specify camera ID or color theme:
```bash
python main.py --camera-id 0 --theme cyan
python main.py --theme solar
python main.py --theme violet
python main.py --theme matrix
```

### 2. Synthetic Test Mode (No Webcam Required)
To run the full visual application without needing a webcam:

```bash
python main.py --synthetic --theme cyan
```

### 3. Automated Performance Benchmark Mode
Runs for $N$ frames, records average FPS and min/max frame latencies, and cleanly exits:

```bash
python main.py --benchmark 120 --synthetic --headless
```

---

## Interactive Controls

| Key / Gesture | Action |
|---|---|
| **Pinch (Thumb + Index)** | Grab and control the active holographic object |
| **Move Hand** | Move the object smoothly across the viewport |
| **Open Hand** | Expand the object's size up to maximum diameter |
| **Close Hand (Fist)** | Shrink the object down to a compact core |
| **1 / 2 / 3** | Switch active object: `1 = Energy Orb`, `2 = Cyber Cube`, `3 = Planet` |
| **V** | Cycle to the next available camera source |
| **4-9** | Jump directly to camera device index 4-9 |
| **C** | Cycle color themes (Cyan $\rightarrow$ Solar $\rightarrow$ Violet $\rightarrow$ Matrix) |
| **R** | Reset active object to the center of the screen |
| **H** | Toggle holographic hand skeleton joints overlay |
| **S** | Save high-resolution screenshot |
| **Q / ESC** | Exit the application cleanly |

---

## Running the Automated Test Suite

Execute the full automated test suite with pytest:

```bash
pytest -v
```
