# Holographic VFX Troubleshooting Guide

A symptom-based guide to resolving hardware, performance, and environment issues with **Holographic VFX**.

---

## Table of Contents
1. [Application Does Not Start](#1-application-does-not-start)
2. [Windows Shows "Windows Protected Your PC" (SmartScreen)](#2-windows-shows-windows-protected-your-pc-smartscreen)
3. [Webcam Is Not Detected or Shows a Black Screen](#3-webcam-is-not-detected-or-shows-a-black-screen)
4. [Hands Are Not Being Detected](#4-hands-are-not-being-detected)
5. [Hand Tracking Feels Laggy or Delayed](#5-hand-tracking-feels-laggy-or-delayed)
6. [Object Movement Glitches or Jumps Erratically](#6-object-movement-glitches-or-jumps-erratically)
7. [Frame Rate (FPS) Is Low](#7-frame-rate-fps-is-low)
8. [Screenshots Are Missing or Not Saving](#8-screenshots-are-missing-or-not-saving)
9. [Application Closed Unexpectedly (Crashed)](#9-application-closed-unexpectedly-crashed)
10. [How to Collect Crash Information](#10-how-to-collect-crash-information)
11. [How to File an Effective Bug Report](#11-how-to-file-an-effective-bug-report)

---

## 1. Application Does Not Start

### Symptoms:
Double-clicking `HolographicVFX.exe` does nothing, flashes briefly, or closes instantly.

### Causes & Solutions:
1. **Running directly inside a ZIP file**:
   * **Cause**: Double-clicking `HolographicVFX.exe` inside Windows File Explorer without extracting prevents the executable from loading its bundled libraries and model weights in `_internal/`.
   * **Solution**: Right-click `HolographicVFX-v1.0.1-Windows-x64.zip`, select **Extract All...**, and run the executable from the extracted folder.
2. **Missing Visual C++ Redistributable**:
   * **Cause**: On bare-bones or fresh Windows installations, the Microsoft Visual C++ 2015–2022 Runtime libraries may be missing.
   * **Solution**: Download and install the official Microsoft [vc_redist.x64.exe](https://aka.ms/vs/17/release/vc_redist.x64.exe).
3. **Antivirus Quarantined Files**:
   * **Cause**: Aggressive third-party antivirus software may have quarantined an internal `.pyd` or `.dll` file from the extracted folder.
   * **Solution**: Check your antivirus quarantine history. If `HolographicVFX.exe` was flagged, restore it and add the extraction folder to your exclusions.

---

## 2. Windows Shows "Windows Protected Your PC" (SmartScreen)

### Symptoms:
Windows Defender SmartScreen displays a blue warning dialog saying:  
> *"Microsoft Defender SmartScreen prevented an unrecognized app from starting. Running this app might put your PC at risk."*

### Cause:
Holographic VFX is an open-source development project. The executable has not yet been signed with an expensive commercial Authenticode certificate from a Certificate Authority. Windows SmartScreen displays this prompt for any newly downloaded unsigned executable that has not yet accumulated wide global download reputation.

### Solution:
1. Click **More info** on the SmartScreen dialog.
2. Verify that the application name says `HolographicVFX.exe` or `HolographicVFX-v1.0.1-Windows-x64-Setup.exe`.
3. Click **Run anyway**.
*(This is a one-time prompt; once confirmed, Windows remembers your preference for that install).*

---

## 3. Webcam Is Not Detected or Shows a Black Screen

### Symptoms:
The application launches into a procedural synthetic grid instead of your camera feed, or displays a *"Failed to open camera"* notification.

### Causes & Solutions:
1. **Camera in use by another application**:
   * **Cause**: Under Windows, webcams are opened exclusively via DirectShow or Media Foundation. If Zoom, Microsoft Teams, OBS Studio, Discord, Skype, or Chrome is accessing your camera, Holographic VFX cannot access the video stream.
   * **Solution**: Close all other applications that might be using your webcam, then press `[V]` to re-probe cameras, or restart Holographic VFX.
2. **Windows Camera Privacy Permissions Disabled**:
   * **Cause**: Windows 10/11 privacy controls block desktop apps from camera hardware.
   * **Solution**:
     * Open Windows **Settings** (`Win + I`).
     * Go to **Privacy & security** $\rightarrow$ **Camera**.
     * Ensure **Camera access** is toggled **On**.
     * Ensure **Let desktop apps access your camera** is toggled **On**.
3. **Multiple Cameras Connected**:
   * **Cause**: You have an external webcam, an integrated camera, or a virtual camera (like OBS Virtual Camera or Windows Phone Link), and the default device index `0` points to the wrong device.
   * **Solution**: Press `[V]` on your keyboard to cycle through available cameras until your active webcam feed appears.

---

## 4. Hands Are Not Being Detected

### Symptoms:
The camera video displays properly, but no skeleton joints appear, no holographic orb follows your hand, and gesture controls do not respond.

### Causes & Solutions:
1. **Inadequate Room Lighting**:
   * **Cause**: MediaPipe needs sufficient contrast to locate finger joints. If the room is dark or your hands are cast in shadow, landmark confidence drops below the detection threshold (`0.6`).
   * **Solution**: Ensure your room has adequate front-facing light. Face toward a lamp or window. Avoid strong backlighting (e.g., sitting with your back to a sunny window).
2. **Distance / Camera Framing**:
   * **Cause**: Your hand is too close (filling the whole lens) or too far away.
   * **Solution**: Keep your hands between 1.5 and 3 feet (0.5 to 1 meter) from the camera lens.
3. **Skeleton Overlay Disabled**:
   * **Cause**: Hand tracking is functioning, but the visual joints overlay is hidden.
   * **Solution**: Press `[H]` to toggle the green/cyan joint landmark skeleton overlay on.

---

## 5. Hand Tracking Feels Laggy or Delayed

### Symptoms:
The holographic object follows your hand, but trails noticeably behind your physical movement.

### Causes & Solutions:
1. **Webcam Auto-Exposure Drop (Most Common)**:
   * **Cause**: When room lighting is dim, consumer webcams automatically increase sensor exposure time to compensate, dropping their physical capture frame rate from 30 FPS down to 15 or 10 FPS. Even though rendering runs at 60 FPS, the tracking updates only as fast as the webcam delivers frames.
   * **Solution**: Brighten the lighting in front of your face and hands. Your webcam hardware will automatically snap back to 30 or 60 FPS capture.
2. **Synchronous Tracking Enabled**:
   * **Cause**: If launched with `--sync-tracking`, rendering waits for CPU hand inference on every frame.
   * **Solution**: Launch the application normally without `--sync-tracking` so the asynchronous decoupled worker handles inference on a separate thread.

---

## 6. Object Movement Glitches or Jumps Erratically

### Symptoms:
The object jitters, snaps across the screen, or unexpectedly drops while moving.

### Causes & Solutions:
1. **Edge-of-Frame Loss**:
   * **Cause**: When your hand moves past the boundary of the camera frame, MediaPipe loses sight of your finger joints.
   * **Solution**: Keep your hand within the visible video boundary. Holographic VFX includes a built-in 4-frame grace period tolerance, but moving completely out of view will release the object.
2. **Hand Occlusion**:
   * **Cause**: Turning your hand sideways so fingers block the camera's line-of-sight to your thumb tip causes the pinch distance calculation to fluctuate.
   * **Solution**: Keep your palm facing generally toward the camera lens while pinching and moving.

---

## 7. Frame Rate (FPS) Is Low

### Symptoms:
The on-screen HUD shows an FPS counter significantly below 30 FPS.

### Causes & Solutions:
1. **High Resolution on Low-Powered Laptop**:
   * **Cause**: Running at 1080p or 4K on low-voltage integrated graphics (e.g., Intel UHD).
   * **Solution**: Launch with standard resolution (`--width 640 --height 480`).
2. **Heavy Background CPU Load**:
   * **Cause**: Other background processes (game downloads, video encoding, software compiling) consuming all CPU cores.
   * **Solution**: MediaPipe CPU inference requires 1–2 available CPU cores. Close heavy background tasks.

---

## 8. Screenshots Are Missing or Not Saving

### Symptoms:
Pressing `[S]` does not produce an image file.

### Causes & Solutions:
1. **Incorrect Folder Checked**:
   * **Cause**: Screenshots are NOT stored in the installation directory or on the Desktop.
   * **Solution**: Open File Explorer and navigate to your personal Pictures directory:
     ```text
     %USERPROFILE%\Pictures\HolographicVFX\
     ```
2. **Restricted Windows Permissions**:
   * **Cause**: Highly restricted user permissions on the Pictures directory.
   * **Solution**: Holographic VFX automatically falls back to `%USERPROFILE%\.holographic_vfx\captures\` or the Windows system `%TEMP%\HolographicVFX\captures\` folder if Pictures is inaccessible.

---

## 9. Application Closed Unexpectedly (Crashed)

### Symptoms:
The application window abruptly vanished, or an error dialog titled *"Holographic VFX - Application Error"* popped up.

### Cause:
An unhandled runtime failure occurred (such as a video capture driver fault or DirectX/DirectShow crash).

### Solution:
1. In the error dialog, note the crash log location.
2. Holographic VFX automatically writes a complete diagnostic report upon fatal crashes:
   ```text
   %USERPROFILE%\Pictures\HolographicVFX\crash_log.txt
   ```
3. Open `crash_log.txt` to view the timestamp and traceback details.

---

## 10. How to Collect Crash Information

When reporting an issue, please collect:

1. **Crash Log**: Open `%USERPROFILE%\Pictures\HolographicVFX\crash_log.txt` (or `%TEMP%\HolographicVFX_crash_log.txt`).
2. **System Information**:
   * Windows version (e.g., Windows 11 Home 23H2).
   * CPU model (e.g., AMD Ryzen 7 5800H / Intel Core i7-11800H).
   * Webcam model (e.g., Integrated HD Webcam / Logitech C920).
3. **Application Mode**:
   * Standalone Installer, Portable ZIP, or Source Python execution.

---

## 11. How to File an Effective Bug Report

If you encountered a persistent bug that was not resolved by the steps above:

1. Visit the project's GitHub Issues page:  
   [https://github.com/BikExists/hologram-vfx/issues](https://github.com/BikExists/hologram-vfx/issues)
2. Click **New Issue** and select the **Bug Report** template.
3. Paste the contents of your `crash_log.txt` into the issue.
4. Describe what physical action you were performing right before the crash occurred.
