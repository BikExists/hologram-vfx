# Holographic VFX Privacy & Data Processing Notice

This document describes how data is handled and processed by **Holographic VFX**. It reflects the actual observable implementation of the application as of the current codebase.

This notice is purely informational and describes technical behavior; it does not constitute a formal legal agreement or regulatory certification.

---

## 1. Camera Input & Video Stream

Holographic VFX requires video capture input to detect hand positions and gestures.

* **Purpose**: Video frames are captured solely to perform real-time hand tracking and gesture detection (via Google MediaPipe).
* **Local In-Memory Processing**: Video frames are captured directly from the connected webcam into local volatile system RAM (NumPy BGR image arrays).
* **No Video Persistence**: Raw webcam frames and video feeds are never saved to disk, encoded into video files, or cached in temporary storage.
* **No Network Transmission**: Video frames never leave your computer. The application contains no code to transmit video data over local networks, the internet, or to external cloud servers.
* **Camera Fallback**: If no physical webcam is connected, or if camera initialization fails, the application switches to an internal synthetic test generator (`SyntheticCamera`). The synthetic generator generates mathematical procedural patterns entirely in memory without accessing camera hardware.

---

## 2. Screenshots

The application allows users to capture visual snapshots during runtime.

* **User-Initiated Only**: Screenshots are created **only** when the user explicitly triggers the capture action by pressing the `[S]` key on the keyboard.
* **Storage Location**: By default, screenshots are saved to the user's personal Windows Pictures directory:
  ```text
  %USERPROFILE%\Pictures\HolographicVFX\
  ```
* **Fallback Locations**: If the primary Pictures folder is unavailable or lacks write permissions, the application attempts to save to:
  1. `%USERPROFILE%\.holographic_vfx\captures\`
  2. The system temporary directory: `%TEMP%\HolographicVFX\captures\`
* **Naming & Collision Avoidance**: Screenshot filenames follow the format `HolographicVFX_YYYYMMDD_HHMMSS.png`. If multiple screenshots are captured within the same second, an incrementing counter suffix (`_1`, `_2`, etc.) is appended to avoid overwriting existing files.
* **No Automatic Upload**: Screenshots are stored strictly on the local filesystem and are never automatically transmitted, synchronized, or uploaded to any remote service.

---

## 3. Crash Diagnostics & Error Logs

The application includes basic local crash diagnostic handling to aid in debugging runtime faults.

* **Trigger Condition**: A crash log is generated **only** if an unhandled fatal exception causes the application to terminate unexpectedly.
* **Storage Location**: The diagnostic log is written to:
  ```text
  %USERPROFILE%\Pictures\HolographicVFX\crash_log.txt
  ```
  *(With a secondary fallback to `%TEMP%\HolographicVFX_crash_log.txt` if Pictures is inaccessible).*
* **Log Contents**: The crash report records only diagnostic execution metadata:
  * Local system timestamp
  * Operating system platform (`sys.platform`)
  * Python runtime version
  * Exception type and message
  * Standard Python traceback
* **No Sensitive Data**: Crash logs do not record camera frames, image data, facial features, or hand landmark coordinates.
* **No Telemetry Transmission**: Crash reports are saved purely as local text files. The application has no automated crash-reporting telemetry (such as Sentry or Crashlytics). Crash information is shared only if the user manually inspects the file and pastes its contents into a GitHub issue report.

---

## 4. Network Behavior & Telemetry

* **Zero Network Requests**: Based on code inspection, the application contains no networking implementation, socket clients, HTTP request libraries, or web service connections.
* **Zero Telemetry & Analytics**: The application contains no usage tracking, event analytics, telemetry beacons, or advertising identifiers.
* **Fully Offline Operation**: The software functions completely disconnected from the internet. An active internet connection is neither required nor utilized during operation.

---

## 5. Third-Party Machine Learning Models

* Hand tracking relies on pre-trained machine learning models distributed by Google MediaPipe.
* In the standalone package, model weights (`.tflite`, `.binarypb`, `.task`) are bundled locally within the application distribution directory.
* Model inference executes locally on the user's CPU using the bundled TensorFlow Lite / MediaPipe runtime.
* No data is transmitted to Google or any third-party infrastructure during model execution.

---

## 6. Data Retention & Uninstallation

* The application does not maintain a database, user configuration registry, or tracking profile.
* User-created screenshots and crash logs in `%USERPROFILE%\Pictures\HolographicVFX\` remain on the user's system until the user decides to delete them manually.
* Running the application uninstaller (`unins000.exe`) removes the program binaries and shortcuts from `%LOCALAPPDATA%\Programs\HolographicVFX` but preserves user-created screenshots and crash logs in the Pictures directory.

---

## 7. Changes to this Document

This document reflects the data handling practices of the current codebase. As the project evolves, this document will be updated to reflect any changes in functionality or data handling.
