# Holographic VFX

<p align="center">
  <img src="assets/logo.png" alt="Holographic VFX Logo" width="500">
</p>

<p align="center">
  <a href="https://github.com/BikExists/hologram-vfx/releases/tag/v1.0.1"><img src="https://img.shields.io/badge/Windows%20Standalone-v1.0.1-blue?logo=windows" alt="Windows Standalone v1.0.1"></a>
  <a href="https://github.com/BikExists/hologram-vfx"><img src="https://img.shields.io/badge/Tests-201%20Passed-brightgreen" alt="201 Tests Passing"></a>
  <a href="https://github.com/BikExists/hologram-vfx/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-orange" alt="License"></a>
  <a href="docs/SYSTEM_REQUIREMENTS.md"><img src="https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-lightgrey?logo=windows" alt="Platform"></a>
</p>

A real-time interactive computer vision application that turns any standard webcam into a touchless spatial interface. Using MediaPipe hand tracking and procedural computer graphics, Holographic VFX allows you to grab, rotate, scale, and manipulate glowing 3D holographic objects floating in mid-air.

---

## Documentation Hub

Explore the full documentation suite for guides, references, and technical details:

| Guide | Description |
| :--- | :--- |
| 📖 [**User Guide**](docs/USER_GUIDE.md) | Complete step-by-step walkthrough covering gestures, menu navigation, and modes. |
| 🎮 [**Controls & Gestures**](docs/CONTROLS.md) | Quick keyboard reference, gesture postures, and dual-hand interaction modes. |
| 🔧 [**Troubleshooting Guide**](docs/TROUBLESHOOTING.md) | Practical solutions for webcam detection, lighting, tracking jitter, and crashes. |
| ❓ [**Frequently Asked Questions (FAQ)**](docs/FAQ.md) | Common questions regarding hardware, privacy, 60 FPS, and platforms. |
| 💻 [**System Requirements**](docs/SYSTEM_REQUIREMENTS.md) | Verified hardware, OS, and software specifications for standalone and source. |
| 🏗️ [**Architecture & Development**](docs/DEVELOPMENT.md) | Technical guide covering the pipeline lifecycle, decoupled tracking, and build steps. |
| 🤝 [**Contributing Guidelines**](CONTRIBUTING.md) | Workflow for setting up your environment, running 201 tests, and pull requests. |
| 📜 [**Changelog**](CHANGELOG.md) | Historical milestones from initial prototype to Phase B runtime hardening. |
| 🔒 [**Privacy & Data Notice**](docs/PRIVACY.md) | Factual details on local frame processing, zero telemetry, and user screenshots. |
| 📄 [**Third-Party Notices**](THIRD-PARTY-NOTICES.md) | Open-source licenses, notices, and pre-trained model disclosures. |
| ⚖️ [**Terms & Disclaimer**](docs/TERMS.md) | Pre-release software terms, "as-is" disclaimer, and maintainer licensing authority. |
| 📜 [**License (Apache 2.0)**](LICENSE) | Official Apache License, Version 2.0 terms governing this project. |

---

## Key Features

* **6 Interactive Holographic Objects**:
  1. **Energy Orb** (`[1]`): Signature holographic sphere with gyroscopic rings, orbiting Keplerian particle cloud, and plasma pinch tethers.
  2. **Cyber Cube** (`[2]`): 3D wireframe cube with glowing perspective lines, depth-sorted faces, and luminous vertex corner beacons.
  3. **Holographic Planet** (`[3]`): Celestial body with atmospheric limb glow, rotating latitude bands, concentric rings, and an orbiting moon.
  4. **Ghost Orchid** (`[4]`): Organic botanical hologram with procedural bioluminescent petals that bloom based on hand openness.
  5. **Bhondu Face** (`[5]`): Stylized geometric character hologram with dynamic facial expressions.
  6. **Bioluminescent Jellyfish** (`[6]`): Undulating deep-sea hologram with dynamic procedural flowing tentacles.
* **Decoupled Asynchronous Tracking Engine**: Hand tracking runs on a dedicated background thread with single-slot "latest-frame-wins" buffering, keeping visual rendering fluid at up to 60 FPS regardless of camera latency.
* **Natural Hand Gestures**:
  * **Pinch**: Touch thumb and index finger to grab and drag holographic objects.
  * **Open Palm**: Spread fingers wide to expand an object's scale and radial energy glow.
  * **Closed Fist**: Clench fingers into a fist to compress an object down into a compact core.
* **Dual-Hand Control**:
  * **Standard Mode**: Both hands work together to rotate, scale, and reposition a single object.
  * **Independent Mode**: Primary hand moves the object; secondary hand independently scales and navigates menus.
* **Touchless Holographic Menu**: Hover an open palm over the top-right `[ MENU ]` trigger zone for 0.6s to summon a floating sci-fi glass menu; navigate with a fingertip cursor.
* **4 Sci-Fi Color Themes**: Cyber Cyan, Solar Flare, Neon Violet, and Emerald Matrix.
* **Unicode-Safe Snapshots**: Press `[S]` to save high-resolution PNG screenshots directly to `%USERPROFILE%\Pictures\HolographicVFX\`.
* **Local-First & Offline**: **Zero network requests, zero telemetry, zero cloud calls.** Camera frames are processed strictly in local volatile system RAM (see [docs/PRIVACY.md](docs/PRIVACY.md)).

---

## Downloads (Windows Standalone)

Latest Release: [**HolographicVFX v1.0.1**](https://github.com/BikExists/hologram-vfx/releases/tag/v1.0.1)

| Package | Best For | Download |
| :--- | :--- | :--- |
| **Windows Setup Installer (`.exe`)** | Most Users | [**Download Setup (.exe)**](https://github.com/BikExists/hologram-vfx/releases/download/v1.0.1/HolographicVFX-v1.0.1-Windows-x64-Setup.exe) |
| **Portable Distribution (`.zip`)** | Zero-Install / USB Drives | [**Download Portable (.zip)**](https://github.com/BikExists/hologram-vfx/releases/download/v1.0.1/HolographicVFX-v1.0.1-Windows-x64.zip) |

*Neither package requires Python, Git, or developer dependencies. All models and runtimes are fully self-contained.*

### Windows SmartScreen Notice
Because this is an open-source release (`v1.0.1`), binaries are not yet signed with a commercial Authenticode certificate. On first launch, Windows Defender SmartScreen may display:
> *"Windows protected your PC — Microsoft Defender SmartScreen prevented an unrecognized app from starting."*

**How to open**: Click **More info**, then click **Run anyway**.  
*(See [FAQ.md](docs/FAQ.md#10-why-does-windows-defender-smartscreen-display-a-warning-on-launch) for full details).*

---

## Quick Start Guide

1. **Launch**: Open **Holographic VFX** from your Desktop shortcut or double-click `HolographicVFX.exe`.
2. **Start**: Raise your hand toward the camera or press `Space` / `Enter` to dismiss the welcome screen.
3. **Grab & Move**: Pinch your thumb and index finger together over the floating holographic orb to grab it; move your hand to drag it across the screen.
4. **Scale**: Spread all 5 fingers wide to expand the hologram, or curl into a fist to shrink it.
5. **Switch Objects**: Press number keys `[1]` through `[6]` on your keyboard.
6. **Open Menu**: Move your open palm to the top-right `[ MENU ]` corner and hold for 0.6 seconds.
7. **Take a Picture**: Press `[S]` to save a screenshot to your Windows Pictures folder.
8. **Quit**: Press `[Q]` or `[ESC]`.

---

## Quick Controls Reference

| Input | Action |
| :--- | :--- |
| **`[Pinch]`** | Grab & move holographic object / Pinch-to-click on menu buttons |
| **`[Open Palm]`** | Expand object scale and energy aura intensity |
| **`[Closed Fist]`** | Shrink object down to a dense core |
| **`[Top-Right Dwell]`** | Hold open palm in top-right corner for 0.6s to toggle menu |
| **`[1]` .. `[6]`** | Switch object (Orb, Cube, Planet, Orchid, Bhondu, Jellyfish) |
| **`[Tab]` / `[I]`** | Cycle interaction mode (Standard 2-Hand vs Independent Dual-Hand) |
| **`[C]`** | Cycle color theme (Cyan $\rightarrow$ Solar Flare $\rightarrow$ Violet $\rightarrow$ Emerald) |
| **`[V]`** | Switch active camera device |
| **`[R]`** | Reset object to center of viewport |
| **`[H]`** | Toggle 21-joint MediaPipe skeleton overlay |
| **`[S]`** | Save high-resolution screenshot to Pictures folder |
| **`[M]`** | Toggle touchless holographic menu |
| **`[Space]` / `[Enter]`** | Dismiss welcome tutorial overlay |
| **`[Q]` / `[ESC]`** | Close menu / Quit application |

*(For the complete guide, see [CONTROLS.md](docs/CONTROLS.md)).*

---

## System Requirements Summary (Tested Configurations)

* **OS**: 64-bit Windows 10 (22H2) or Windows 11 (23H2).
* **CPU**: 64-bit x86_64 multi-core processor (Intel Core i5/i7, AMD Ryzen 5/7).
* **RAM**: 8 GB to 16 GB RAM tested (runtime working set is ~300–450 MB).
* **Webcam**: Standard integrated laptop camera or USB webcam (720p 30 FPS / 1080p 60 FPS).
* **Disk Space**: ~650 MB free space (~170 MB download, ~615 MB installed footprint).
* **Permissions**: Standard user account with Windows Camera Privacy access enabled.

*(For full hardware and platform details, see [SYSTEM_REQUIREMENTS.md](docs/SYSTEM_REQUIREMENTS.md)).*

---

## Running from Source (Developers)

```powershell
# 1. Clone the repository
git clone https://github.com/BikExists/hologram-vfx.git
cd hologram-vfx

# 2. Set up virtual environment (Python 3.10 or 3.11 64-bit)
python -m venv .venv
.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run application
python main.py

# 5. Run tests (197 automated tests)
pytest -v
```

*(For architecture, pipeline diagrams, and packaging instructions, see [DEVELOPMENT.md](docs/DEVELOPMENT.md)).*

---

## Performance & FPS Metrics

* **Real-World Webcam Experience**: In normal usage, frame rate is governed by your physical webcam's hardware capabilities (typically **30–60 FPS**). The decoupled tracking worker ensures visual rendering and animations remain fluid without stalling on inference latency.
* **Synthetic Benchmark Mode**: Running `python main.py --synthetic --headless --benchmark 120` bypasses physical sensor delays to measure internal rendering and tracking throughput. Synthetic benchmark rates can reach **200–300+ FPS**. This figure represents pipeline headroom rather than expected webcam performance.

---

## Platform Status & Boundaries

| Platform | Mode | Status | Notes |
| :--- | :--- | :--- | :--- |
| **Windows (x64)** | Standalone (Installer & ZIP) | **Hardened Pre-Release** | Hardened standalone build. Installer and portable ZIP available. |
| **Windows (x64)** | Source Execution | **Supported** | Tested on Windows 10 and 11 with full automated test suite. |
| **macOS** | Source Execution | **Tested from Source** | Source-level execution has been verified on physical Mac hardware via `python main.py`. Native standalone packaging is deferred. |
| **Linux (x86_64)** | Source Execution | **Unverified** | Platform code exists, but current standalone and support status is not verified. |

---

## Known Limitations

* **Unsigned Binaries**: Pre-release builds show the Windows SmartScreen "Unknown Publisher" dialog on first run until code-signing certificates are provisioned.
* **Low-Light Drop**: Consumer webcams automatically lower their physical sensor frame rate in dim rooms. Adequate room lighting is recommended for 30–60 FPS tracking.
* **macOS Standalone**: Standalone `.app` or `.dmg` packages are not yet available; run from source on macOS.

---

## Project Status, Licensing & Credits

* **Author & Maintainer**: Created and maintained by **BikExists**.
* **Project License**: Holographic VFX is licensed under the [Apache License, Version 2.0](LICENSE). Copyright 2026 BikExists.
* **Third-Party Open Source**: Built with [Google MediaPipe](https://github.com/google/mediapipe) (Apache 2.0), [OpenCV](https://opencv.org/) (Apache 2.0), and [NumPy](https://numpy.org/) (BSD 3-Clause). For a complete list of third-party dependencies, model disclosures, and license notices, see [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).
* **Privacy & Terms**: See [docs/PRIVACY.md](docs/PRIVACY.md) and [docs/TERMS.md](docs/TERMS.md).
