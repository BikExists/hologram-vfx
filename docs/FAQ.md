# Holographic VFX Frequently Asked Questions (FAQ)

Answers to common questions about capabilities, hardware, privacy, performance, and platform support.

---

## General & Concepts

### 1. Is this "real" physical holography projected into thin air?
No. Holographic VFX is a computer vision software application that renders procedural 3D visual effects on your computer screen. It creates the illusion of mid-air holographic manipulation by tracking your physical hands in real time and projecting interactive 3D objects that react naturally to your finger motions.

### 2. Does it require special sensors (like Leap Motion, Kinect, or VR headsets)?
No. It works with standard consumer 2D webcams (including built-in laptop cameras and standard USB webcams). No specialized depth sensors or wearable gear are required.

### 3. Does it work without a webcam connected?
Yes. If no physical webcam is detected, the application automatically falls back to an internal **synthetic camera feed** that generates an animated procedural background. You can test all 6 holographic objects, navigate the menu, test keyboard shortcuts, and capture screenshots in synthetic mode.

---

## Privacy & Security

### 4. Does Holographic VFX upload my webcam video to the cloud?
No. All video frame processing and machine learning inference occurs locally on your computer's CPU in volatile system RAM (NumPy arrays). Based on the codebase, no video frames, images, or biometric hand data are ever transmitted to any external server or network endpoint. *(See [PRIVACY.md](PRIVACY.md) for full details).*

### 5. Does the application require an internet connection?
No. Holographic VFX is designed as a local-first application. It requires zero network access, contains no analytics or telemetry code, and operates completely disconnected from the internet. *(See [PRIVACY.md](PRIVACY.md)).*

### 6. When does it save files to my hard drive?
The application writes to your disk in only two situations:
1. When you explicitly press `[S]` to take a screenshot.
2. If an unhandled fatal crash occurs, it writes a diagnostic `crash_log.txt` to help identify the failure.

---

## Interaction & Features

### 7. Can I use both hands at the same time?
Yes! Bringing two hands into view unlocks dual-hand interaction. Pressing `[Tab]` or `[I]` toggles between:
* **Standard Mode**: Both hands work together to rotate, scale, and reposition a single object.
* **Independent Mode**: Your primary hand grabs and moves the object, while your secondary hand controls scale and background parameters.

### 8. How many holographic objects are included?
There are **6 procedural objects**:
1. Energy Orb
2. Cyber Cube
3. Holographic Planet
4. Ghost Orchid
5. Bhondu Face
6. Bioluminescent Jellyfish  
Switch between them using keys `1` through `6` or via the touchless holographic menu.

### 9. Where are my screenshots stored?
Screenshots are saved directly to your personal Windows Pictures folder:
```text
%USERPROFILE%\Pictures\HolographicVFX\
```
Uninstalling the app will **never** delete your screenshots.

---

## Windows & Installation

### 10. Why does Windows Defender SmartScreen display a warning on launch?
Holographic VFX is an open-source development project (`v0.1.1-dev`). Because commercial code-signing certificates cost hundreds of dollars annually, development builds are unsigned. Windows SmartScreen displays a warning on any newly downloaded unsigned executable until it establishes global download reputation.
* To proceed: Click **More info**, then click **Run anyway**.

### 11. Does the installer require Administrator permissions?
No. The Windows installer is configured with `PrivilegesRequired=lowest` and installs per-user into `%LOCALAPPDATA%\Programs\HolographicVFX`. It does not require administrative elevation or UAC prompts.

---

## Performance & Hardware

### 12. Can I run Holographic VFX at 60 FPS?
Yes, provided two conditions are met:
1. **Adequate Room Lighting**: In dim lighting, webcams automatically lower their hardware capture rate to 15–20 FPS to compensate for dark sensors. A well-lit room allows your webcam to output full 30 or 60 FPS.
2. **Decoupled Asynchronous Tracking Engine**: By default, visual rendering runs decoupled from hand tracking. Visual animations and particle systems render smoothly up to 60 FPS while tracking updates on a background worker thread.

### 13. Can I use a 4K webcam?
Yes. The application automatically detects higher camera resolutions and preserves your camera's native aspect ratio. However, for computer vision efficiency, hand landmark inference is processed at an optimized sub-resolution (640x480) before mapping coordinates back to your high-resolution display, ensuring high FPS regardless of camera sensor resolution.

---

## Platform Support

### 14. Does it work on macOS?
* **From Source**: Source-level testing has been performed on physical Mac hardware running directly from source (`python main.py`).
* **Standalone App (`.app` / `.dmg`)**: Native macOS standalone packaging is intentionally deferred and will be developed and validated in a future milestone on physical Mac hardware.

### 15. Does it work on Linux?
Platform code exists, but current standalone and support status is not verified. Pre-built Linux standalone packages are not currently provided.

---

## Licensing & Legal

### 16. What is the license for Holographic VFX?
The repository currently contains no explicit project license file committed. Formal adoption of a project license is an administrative decision reserved for the repository maintainer (`BikExists`). All third-party libraries (OpenCV, Google MediaPipe, NumPy, etc.) are utilized under their respective open-source licenses. For complete details, see [THIRD-PARTY-NOTICES.md](../THIRD-PARTY-NOTICES.md) and [TERMS.md](TERMS.md).
