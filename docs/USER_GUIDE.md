# Holographic VFX User Guide

A step-by-step practical guide to using the **Hand-Tracked Holographic VFX System**.

---

## Table of Contents
1. [First Launch](#1-first-launch)
2. [Camera Setup & Permissions](#2-camera-setup--permissions)
3. [Starting the Experience](#3-starting-the-experience)
4. [Hand Tracking Basics](#4-hand-tracking-basics)
5. [Gesture Controls](#5-gesture-controls)
6. [Moving, Rotating, and Scaling Objects](#6-moving-rotating-and-scaling-objects)
7. [Dual-Hand Interaction](#7-dual-hand-interaction)
8. [Switching Objects](#8-switching-objects)
9. [Color Themes](#9-color-themes)
10. [Opening the Holographic Menu](#10-opening-the-holographic-menu)
11. [Menu Navigation](#11-menu-navigation)
12. [Taking Screenshots](#12-taking-screenshots)
13. [Window Behavior & Display](#13-window-behavior--display)
14. [Camera Fallback & Synthetic Mode](#14-camera-fallback--synthetic-mode)
15. [Performance & Lighting Tips](#15-performance--lighting-tips)
16. [Troubleshooting Common Issues](#16-troubleshooting-common-issues)
17. [Current Limitations](#17-current-limitations)

---

## 1. First Launch

### If you installed via the Windows Installer:
1. Open your **Start Menu** or look on your **Desktop** for the **Holographic VFX** shortcut.
2. Click the icon to launch the application.

### If you downloaded the Portable ZIP:
1. Right-click the downloaded `.zip` file and choose **Extract All...**.
2. Open the extracted folder and double-click `HolographicVFX.exe`.
   > **Note**: Do not launch `HolographicVFX.exe` directly from inside the compressed zip archive. It must be fully extracted to run properly.

### Windows SmartScreen Note:
Because this is an open-source development release without an expensive commercial code-signing certificate, Windows SmartScreen may show a blue dialog saying *"Windows protected your PC"*.
* Click **More info**.
* Click **Run anyway**.

---

## 2. Camera Setup & Permissions

Holographic VFX requires a standard webcam (integrated laptop camera or external USB webcam) to track hand movements.

### Enabling Camera Permissions in Windows 10 & 11:
1. Open Windows **Settings** (press `Win + I`).
2. Navigate to **Privacy & security** $\rightarrow$ **Camera**.
3. Verify that **Camera access** is set to **On**.
4. Scroll down and verify that **Let desktop apps access your camera** is set to **On**.

### Camera Conflicts:
If another app (such as Zoom, Microsoft Teams, Discord, OBS Studio, or a web browser) is using your webcam, Windows will lock the camera. Close those apps before starting Holographic VFX.

---

## 3. Starting the Experience

When the application opens, you will see your webcam video feed overlaid with a futuristic sci-fi welcome screen and HUD gauges.

1. **Dismiss the Welcome Screen**:
   * Raise your hand in front of the camera, or
   * Press `Space` or `Enter` on your keyboard.
2. The welcome screen will fade, revealing the default holographic object (the **Energy Orb**) floating in the center of your screen.

---

## 4. Hand Tracking Basics

Holographic VFX uses MediaPipe to track 21 3D joint landmarks across each hand.

* **Camera Framing**: Position yourself roughly 1.5 to 3 feet (0.5 to 1 meter) away from the webcam.
* **Visibility**: Keep your hands within the camera frame, with your palms facing generally toward the camera.
* **Lighting**: Ensure your room has adequate front-facing light. Strong backlighting (like sitting directly in front of a bright window) makes your hands appear as dark silhouettes and reduces tracking accuracy.
* **Skeleton Overlay**: Press `H` at any time to toggle the visual skeleton joint lines on or off.

---

## 5. Gesture Controls

The application uses intuitive physical hand postures:

| Posture | Physical Action | Interaction |
| :--- | :--- | :--- |
| **Pinch** | Touch tips of thumb and index finger together | **Grabs** the active object to move it; **Clicks** menu buttons |
| **Open Palm** | Spread all 5 fingers wide outward | **Expands** the object's radius and increases glow intensity |
| **Closed Fist** | Curl all fingers into a tight fist | **Shrinks** the object down to a compact, dense core |
| **Palm Dwell** | Hold an open palm over the top-right `[ MENU ]` zone | **Charges and toggles** the touchless holographic menu |
| **Two Hands** | Bring both hands into camera view | Enables dual-hand rotation, distance-scaling, or independent control |

---

## 6. Moving, Rotating, and Scaling Objects

### Moving an Object:
1. Move your primary hand over the holographic object.
2. **Pinch** your thumb and index finger together. A glowing tether or halo indicates you have grabbed the object.
3. Move your pinched hand across the frame to drag the object.
4. Separate your thumb and index finger to **release** the object in place.

### Scaling an Object:
* **Single Hand**: While controlling an object, spread your fingers wide open to increase its scale and aura power. Curl your fingers to reduce scale.
* **Reset**: Press `R` on the keyboard at any time to snap the object back to the center of the screen at its default scale.

---

## 7. Dual-Hand Interaction

When both hands are visible to the camera, Holographic VFX unlocks multi-hand spatial controls. You can switch between two modes by pressing `Tab` or `I`:

### Mode 1: Standard Two-Hand Transform (Default)
Both hands work together cooperatively to control a single object:
* **Two-Hand Rotation**: The angle between your two hands dynamically tilts and rotates the object in 3D space.
* **Two-Hand Scale**: Moving your hands farther apart stretches the object larger; bringing your hands close together shrinks it.
* **Centering**: The midpoint between your two hands becomes the spatial anchor.

### Mode 2: Independent Dual-Hand Control
Each hand is assigned separate responsibilities:
* **Primary Hand**: Controls position and grab-and-drag.
* **Secondary Hand**: Controls object scale independently based on openness, and allows cycling color themes or scrolling menus.

---

## 8. Switching Objects

Holographic VFX includes **6 procedural 3D holographic objects**. You can switch objects at any time using number keys `1` through `6` or via the touchless menu:

1. **`[1]` Energy Orb**: The signature holographic sphere with tri-axial gyroscopic orbital rings, orbiting particle clouds, plasma tethers, and shockwaves.
2. **`[2]` Cyber Cube**: A rotating 3D wireframe cube with glowing perspective lines, depth-sorted faces, and luminous vertex corner beacons.
3. **`[3]` Holographic Planet**: A celestial sphere with atmospheric limb glow, rotating latitude bands, concentric planetary rings, and an orbiting moon.
4. **`[4]` Ghost Orchid**: An organic holographic botanical structure with procedural bioluminescent petals that open and close based on hand openness.
5. **`[5]` Bhondu Face**: A stylized geometric character hologram with animated expressions and luminous eyes.
6. **`[6]` Bioluminescent Jellyfish**: An undulating deep-sea hologram with dynamic procedural flowing tentacles that pulse in rhythm.

---

## 9. Color Themes

Press `C` on your keyboard (or use the menu) to cycle through the **4 sci-fi color themes**:

* **Cyber Cyan** (Default): High-tech, clean electric cyan and deep blue.
* **Solar Flare**: Warm amber, orange, and radiant gold.
* **Neon Violet**: Vivid purple, magenta, and fluorescent violet.
* **Emerald Matrix**: Terminal green, mint, and deep forest emerald.

---

## 10. Opening the Holographic Menu

You can open the touchless menu using your hand or keyboard:

### Method A: Touchless Hand Dwell (Recommended)
1. Look at the top-right corner of the screen where the `[ MENU ]` trigger zone is located.
2. Raise your open palm into that top-right corner.
3. A circular energy charge gauge will begin filling around the trigger zone.
4. Hold your open palm steadily in the zone for approximately **0.6 seconds** until the charge completes.
5. The holographic menu will expand smoothly on the right side of the screen.
6. To close the menu with your hand, hold your open palm in the top-right corner again until the dwell completes.

### Method B: Keyboard Shortcut
* Press `M` to toggle the menu open or closed instantly.
* Press `ESC` or `Q` while the menu is open to dismiss it.

---

## 11. Menu Navigation

While the menu is open, the holographic object is temporarily locked in position so you can interact with UI buttons:

1. **Move the Hand Cursor**: Move your primary hand across the screen. A glowing holographic cursor tracks your index finger tip.
2. **Clicking Buttons**: Hover the cursor over an item (such as an object name, theme, or camera) and perform a quick **pinch** gesture with your thumb and index finger.
3. **Scrolling Items**: If the menu contains more items than fit on screen:
   * **Secondary Hand Vertical Movement**: Raise or lower your secondary hand vertically to scroll the menu list smoothly up or down.

---

## 12. Taking Screenshots

Capture high-resolution images of your interactions at any moment:

1. Press `S` on your keyboard.
2. A status message appears in the HUD confirming the screenshot was saved.
3. **Where are screenshots saved?**
   Screenshots are saved directly to your personal Windows Pictures folder:
   ```text
   %USERPROFILE%\Pictures\HolographicVFX\
   ```
4. **Collision Safe**: If you take multiple screenshots rapidly within the same second, the application appends an incrementing counter (`_1`, `_2`, etc.) so no screenshot is ever overwritten.
5. **Uninstall Safe**: Screenshots are stored separately from the program files. Uninstalling the app will never delete your saved pictures.

---

## 13. Window Behavior & Display

* **Window Resizing**: You can drag the borders of the Holographic VFX window to resize it. The internal rendering engine automatically conforms to your window's dimensions while preserving proper aspect ratio.
* **Exiting**: Press `Q` or `ESC` (when the menu is closed) to quit the application cleanly. You can also click the standard Windows `[X]` close button in the top-right corner of the window.

---

## 14. Camera Fallback & Synthetic Mode

If no physical webcam is connected, or if your camera is blocked:
* The application logs a notification in the console and automatically switches to an internal **synthetic test feed** with an animated procedural background.
* You can test holographic objects, UI navigation, and color themes even without a physical webcam connected.
* Press `V` at any time to switch to the next available video capture device.

---

## 15. Performance & Lighting Tips

To get the smoothest possible experience:
* **Maintain Good Lighting**: Webcams drop their capture frame rate from 30 FPS down to 15 or 10 FPS in dim lighting because they increase sensor exposure time. Using a desk lamp or sitting facing a light source dramatically improves hand tracking smoothness.
* **Use Asynchronous Tracking (Default)**: By default, Holographic VFX decouples hand tracking from visual rendering. Rendering runs smoothly at 60 FPS while MediaPipe tracking processes in the background.
* **Plain Backgrounds**: Extremely busy backgrounds with posters, hanging clothes, or other people moving behind you can occasionally cause MediaPipe to hesitate. A clean backdrop gives optimal tracking reliability.

---

## 16. Troubleshooting Common Issues

| Symptom | Probable Cause | Action |
| :--- | :--- | :--- |
| **Black screen or "Failed to open camera"** | Camera in use by another app or Windows permissions disabled | Close Zoom/Teams/Discord; check Windows Camera Privacy settings (see Section 2). |
| **Hands not detected** | Dim room lighting or hands too close/far from camera | Turn on a desk lamp facing you; position hands 1.5–3 ft from webcam. |
| **Low FPS / Stuttering** | Camera sensor underexposure in dark room | Improve room lighting to force webcam into 30/60 FPS mode. |
| **SmartScreen warning on launch** | Unsigned development build | Click **More info** $\rightarrow$ **Run anyway** (see Section 1). |
| **Menu won't open with dwell** | Hand closed or moved out of corner too quickly | Keep all 5 fingers spread open and hold still in the top-right corner for 0.6 seconds. |

*For in-depth troubleshooting instructions, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).*

---

## 17. Current Limitations

* **Code Signing**: Binaries are currently unsigned (`v1.0.1`), triggering the one-time Windows SmartScreen prompt on initial launch.
* **Platform**: The standalone installer and portable ZIP are for 64-bit Windows 10 and 11. Native macOS standalone packaging is in development and will be released in a future milestone.
* **Hardware Dependence**: Real-world capture resolution and frame rates are governed by your webcam's physical hardware capabilities.
