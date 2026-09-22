# Holographic VFX System Requirements

Detailed hardware, operating system, and software specifications for running **Holographic VFX**.

---

## 1. Windows Standalone Distribution (Installer & Portable ZIP)

These specifications apply to the packaged standalone releases (`HolographicVFX-Setup.exe` and `HolographicVFX.zip`). No Python, Git, or command-line tools are required.

### Supported & Verified Specifications

| Component | Minimum Specification | Recommended Specification | Status |
| :--- | :--- | :--- | :--- |
| **Operating System** | 64-bit Windows 10 (Version 1909 or later) or Windows 11 | 64-bit Windows 11 (Latest build) | **VERIFIED** |
| **Processor (CPU)** | 64-bit x86_64 Dual-Core (Intel Core i3 6th Gen / AMD Ryzen 3 or equivalent) | 64-bit x86_64 Quad-Core (Intel Core i5 8th Gen+ / AMD Ryzen 5+) | **VERIFIED** |
| **Memory (RAM)** | 4 GB RAM | 8 GB RAM or higher | **VERIFIED** |
| **Graphics (GPU)** | Integrated Graphics supporting DirectX 11 / OpenGL 3.3 (Intel HD 520 / AMD Radeon Vega) | Dedicated GPU (NVIDIA GeForce / AMD Radeon) | **VERIFIED** |
| **Webcam** | Standard integrated 720p 30 FPS laptop camera or USB webcam | 1080p 30/60 FPS external webcam with good low-light sensor | **VERIFIED** |
| **Storage** | ~650 MB free disk space (Installer: ~170 MB download, extracted footprint: ~615 MB) | Solid-State Drive (SSD) | **VERIFIED** |
| **Runtime Libraries** | Microsoft Visual C++ 2015–2022 Redistributable (x64) | Included in standard Windows updates | **VERIFIED** |
| **Administrative Rights** | None required (Installs per-user into `%LOCALAPPDATA%\Programs\`) | None required | **VERIFIED** |

---

## 2. Windows Source Development (Running from Python)

These specifications apply if you are cloning the repository to contribute or run `main.py` directly.

### Supported & Verified Specifications

| Component | Specification | Status |
| :--- | :--- | :--- |
| **Operating System** | 64-bit Windows 10 or Windows 11 | **VERIFIED** |
| **Python Version** | Python 3.10 or 3.11 (64-bit). *Note: Python 3.11.16 is the verified development baseline.* | **VERIFIED** |
| **Package Manager** | `pip` (standard with Python installation) | **VERIFIED** |
| **Version Control** | Git | **VERIFIED** |
| **Core Dependencies** | `opencv-python>=4.8.0`, `mediapipe>=0.10.14,<0.11.0`, `numpy>=1.24.0` | **VERIFIED** |
| **Packaging Tools** | `pyinstaller>=6.0.0`, Inno Setup 6 (optional, required only for building the setup installer) | **VERIFIED** |

---

## 3. Experimental & Non-Windows Platforms

| Platform | Mode | Status | Current Reality & Details |
| :--- | :--- | :--- | :--- |
| **macOS (Apple Silicon / Intel)** | Source Execution (`python main.py`) | **EXPERIMENTAL** | Source execution has been verified on a secondary physical Mac machine running `main.py`. Video capture requires granting Terminal/IDE camera permissions in macOS Security & Privacy. |
| **macOS Standalone (`.app` / `.dmg`)** | Native Packaged App | **NOT AVAILABLE YET** | Standalone packaging for macOS is intentionally deferred and will be implemented in a dedicated milestone once validated on physical Mac hardware. |
| **Linux (x86_64)** | Source Execution (`python main.py`) | **NOT FULLY VERIFIED** | Linux source execution depends on standard V4L2 webcam drivers and X11/Wayland OpenCV backends. Standalone packaging is not yet provided. |

---

## 4. Hardware Verification Distinctions

To maintain absolute technical transparency:

* **Instruction Sets**: The application uses pre-built wheels for NumPy, OpenCV, and MediaPipe. While modern CPUs include AVX2 instructions, AVX2 is not explicitly enforced as a strict launch barrier.
* **Network Connectivity**: **0 internet connection required**. The application does not require online verification, telemetry, cloud inference, or licensing servers. It functions completely offline.
* **Camera Refresh Rates**: Real-world visual fluidity depends on your webcam hardware. A camera running in a dark room that underexposes will drop to 15 FPS at the hardware level. Adequate room illumination is strongly recommended for 30–60 FPS tracking.
