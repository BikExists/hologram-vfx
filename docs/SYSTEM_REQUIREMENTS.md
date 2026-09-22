# Holographic VFX System Requirements

Detailed hardware, operating system, and software specifications for running **Holographic VFX**.

---

## 1. Windows Standalone Distribution (Installer & Portable ZIP)

These specifications apply to the packaged standalone releases (`HolographicVFX-Setup.exe` and `HolographicVFX.zip`). No Python, Git, or command-line tools are required.

> **Note on Minimum Requirements**: Formal absolute minimum hardware requirements (such as the slowest supported legacy CPU or minimum RAM threshold below 4 GB) have not been exhaustively benchmarked across older hardware generations. Instead, the specifications below reflect **tested and known working configurations**.

### Tested & Known Working Configurations

| Component | Known Working Configuration | Notes |
| :--- | :--- | :--- |
| **Operating System** | 64-bit Windows 10 (Version 22H2) or Windows 11 (Version 23H2) | 64-bit OS required. |
| **Processor (CPU)** | 64-bit x86_64 multi-core processor (Intel Core i5/i7, AMD Ryzen 5/7) | MediaPipe hand tracking utilizes CPU inference on background worker thread. |
| **Memory (RAM)** | 8 GB to 16 GB RAM (Tested) | Application runtime memory footprint is ~300–450 MB working set. |
| **Graphics (GPU)** | Integrated Graphics (Intel UHD / Iris Xe / AMD Radeon) or Dedicated GPU | OpenCV presentation uses standard 2D window rendering. |
| **Webcam** | Standard integrated 720p 30 FPS laptop camera or USB webcam | Tested with standard built-in and external USB 2.0/3.0 cameras. |
| **Storage** | ~650 MB free disk space | Installer download: ~170 MB; extracted footprint: ~615 MB. |
| **Runtime Libraries** | Microsoft Visual C++ 2015–2022 Redistributable (x64) | Bundled/standard on updated Windows installations. |
| **User Privileges** | Standard user permissions | Installs per-user into `%LOCALAPPDATA%\Programs\HolographicVFX`; no admin rights required. |

---

## 2. Windows Source Development (Running from Python)

These specifications apply if you are cloning the repository to contribute or run `main.py` directly.

### Verified Development Environment

| Component | Specification | Status |
| :--- | :--- | :--- |
| **Operating System** | 64-bit Windows 10 or Windows 11 | **VERIFIED** |
| **Python Version** | Python 3.10 or 3.11 (64-bit). *Note: Python 3.11.16 is the verified development baseline.* | **VERIFIED** |
| **Package Manager** | `pip` (standard with Python installation) | **VERIFIED** |
| **Version Control** | Git | **VERIFIED** |
| **Core Dependencies** | `opencv-python>=4.8.0`, `mediapipe>=0.10.14,<0.11.0`, `numpy>=1.24.0` | **VERIFIED** |
| **Packaging Tools** | `pyinstaller>=6.0.0`, Inno Setup 6 (optional, required only for building installer) | **VERIFIED** |

---

## 3. Platform Status & Boundaries

| Platform | Execution Mode | Current Status | Details |
| :--- | :--- | :--- | :--- |
| **Windows x64** | Standalone Installer & Portable ZIP | **Hardened Pre-Release** | Hardened standalone build. Installer and portable ZIP available. |
| **Windows x64** | Source Execution (`python main.py`) | **Supported** | Verified with automated test suite and manual testing. |
| **macOS** | Source Execution (`python main.py`) | **Tested from Source** | Source-level execution has been verified on physical Mac hardware. Video capture requires Terminal/IDE camera permissions. |
| **macOS** | Standalone App (`.app` / `.dmg`) | **Deferred** | Native standalone packaging is intentionally deferred until validated on physical Mac hardware. |
| **Linux (x86_64)** | Source Execution (`python main.py`) | **Unverified** | Platform code exists, but current standalone and support status is not verified. |

---

## 4. Hardware & Technical Clarifications

To maintain absolute technical transparency:

* **Instruction Sets**: The application uses standard pre-built wheels for NumPy, OpenCV, and MediaPipe. No hard requirement for AVX2 instructions is explicitly enforced by the application runtime.
* **Network Connectivity**: **Zero network calls**. The application contains no networking code, telemetry, cloud inference, or licensing checks. It operates completely offline.
* **Camera Refresh Rates**: Real-world visual fluidity depends on your webcam hardware. A camera running in a dark room that underexposes will drop to 15 FPS at the hardware level. Adequate room illumination is strongly recommended for 30–60 FPS tracking.
