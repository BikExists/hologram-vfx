# Holographic VFX Controls & Gesture Reference

A complete, verified quick-reference guide to all keyboard shortcuts, hand gestures, and dual-hand interaction modes in **Holographic VFX**.

---

## 1. Keyboard Shortcuts Reference

All keyboard shortcuts are active during runtime. Single key presses trigger instant reactions:

| Key | Action | Description |
| :--- | :--- | :--- |
| **`[1]`** | **Switch to Energy Orb** | Selects Object 1: Holographic energy sphere with gyroscopic rings and particle cloud. |
| **`[2]`** | **Switch to Cyber Cube** | Selects Object 2: Rotating 3D wireframe cube with luminous vertex beacons. |
| **`[3]`** | **Switch to Planet** | Selects Object 3: Celestial sphere with atmospheric glow, rings, and orbiting moon. |
| **`[4]`** | **Switch to Ghost Orchid** | Selects Object 4: Organic botanical hologram with bioluminescent opening petals. |
| **`[5]`** | **Switch to Bhondu Face** | Selects Object 5: Stylized geometric character hologram with dynamic expressions. |
| **`[6]`** | **Switch to Jellyfish** | Selects Object 6: Undulating bioluminescent sea creature with flowing tentacles. |
| **`[Tab]`** or **`[I]`** | **Cycle Interaction Mode** | Toggles between **Standard 2-Hand Mode** and **Independent Dual-Hand Mode**. |
| **`[C]`** | **Cycle Color Theme** | Steps through: **Cyber Cyan** $\rightarrow$ **Solar Flare** $\rightarrow$ **Neon Violet** $\rightarrow$ **Emerald Matrix**. |
| **`[V]`** | **Switch Camera Device** | Hot-switches the active video capture input to the next detected webcam. |
| **`[R]`** | **Reset Object Position** | Snaps the active holographic object back to the center of the viewport. |
| **`[H]`** | **Toggle Skeleton Overlay** | Shows or hides the 21-joint MediaPipe hand landmark skeleton overlay. |
| **`[S]`** | **Save Screenshot** | Captures a high-resolution PNG image directly to `%USERPROFILE%\Pictures\HolographicVFX\`. |
| **`[M]`** | **Toggle Holographic Menu** | Opens or closes the floating touchless menu. |
| **`[Space]`** / **`[Enter]`** | **Dismiss Welcome Screen** | Dismisses the startup welcome and tutorial overlay. |
| **`[Q]`** / **`[ESC]`** | **Close Menu / Quit** | If the menu is open, closes the menu. If the menu is closed, quits the application. |

---

## 2. Hand Gesture Reference

Holographic VFX recognizes natural hand postures using 21 3D landmarks per hand.

| Gesture | Physical Hand Action | Interaction Effect | Notes |
| :--- | :--- | :--- | :--- |
| **Pinch** | Touch the tip of your thumb (`THUMB_TIP`) to your index finger (`INDEX_FINGER_TIP`) | **Grab & Move Object** (or **Click Menu Button**) | A grab threshold of `0.38` activates grab; release threshold of `0.52` drops the object. |
| **Open Palm** | Spread all 5 fingers fully outward | **Expand Object Scale & Energy** | Normalized finger distance increases object radius and aura intensity. |
| **Closed Fist** | Curl all 4 fingers into your palm with thumb folded | **Shrink Object Scale** | Compresses the object down into a compact, dense core. |
| **Top-Right Dwell** | Hold an open palm steadily within the top-right `[ MENU ]` corner box | **Charge and Toggle Menu** | Requires **0.6 seconds** of continuous open-palm presence to open or close menu. |
| **Cursor Tracking** | Point or move index finger across screen while menu is open | **Move Holographic Cursor** | A glowing sci-fi reticle follows your fingertip to highlight menu buttons. |
| **Secondary Hand Vertical Motion** | Move your secondary hand up or down vertically while the menu is open | **Scroll Menu Items** | Relative vertical displacement smoothly scrolls through available objects, themes, and camera devices. |

---

## 3. Dual-Hand Interaction Modes

Pressing `[Tab]` or `[I]` toggles between two distinct multi-hand interaction philosophies:

```
                  ┌──────────────────────────────────────────────┐
                  │          Dual-Hand Interaction Modes         │
                  └──────────────────────┬───────────────────────┘
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼                                               ▼
   ┌───────────────────────────┐                   ┌───────────────────────────┐
   │       STANDARD MODE       │                   │     INDEPENDENT MODE      │
   ├───────────────────────────┤                   ├───────────────────────────┤
   │ Hands cooperate together: │                   │ Hands act independently:  │
   │ • Midpoint sets position  │                   │ • Primary hand grabs &    │
   │ • Distance sets scale     │                   │   moves object            │
   │ • Hand angle sets 3D roll │                   │ • Secondary hand scales   │
   │   and yaw orientation     │                   │   and controls themes/UI  │
   └───────────────────────────┘                   └───────────────────────────┘
```

### Mode 1: Standard Mode (Cooperative Transform)
Designed for collaborative, two-handed manipulation of a single holographic entity:
* **Position**: The object moves to the exact spatial midpoint between both hands.
* **Scale**: The physical distance separating your two hands directly controls the object's size. Moving your hands apart enlarges the object; bringing them together shrinks it.
* **Rotation**: The tilt angle between your two hands rotates the object in 3D space, giving natural tactile control over orientation.
* **Seamless Handoff**: If you pull one hand away, the system preserves the existing transform state smoothly without jumping or snapping.

### Mode 2: Independent Mode (Dedicated Hands)
Designed for multi-tasking workflows:
* **Primary Hand (First detected or grabbed)**:
  * Manages object position and spatial movement.
  * Controls pinch grab and release.
* **Secondary Hand (Second hand in view)**:
  * Controls object scale purely through its own finger openness.
  * Can interact with background parameters, scroll menus, or cycle color themes without interrupting the primary hand's grip on the object.

---

## 4. Command-Line Launch Flags (Developers & Power Users)

When running from the command line (either via source or `HolographicVFX.exe`), the following startup arguments are supported:

| Flag | Argument | Default | Description |
| :--- | :--- | :--- | :--- |
| `--camera-id` | `INTEGER` | `0` | Device index of the physical webcam to open. |
| `--list-cameras` | *None* | `False` | Scans for available video capture devices, prints them to stdout, and exits. |
| `--width` | `INTEGER` | `640` | Video frame width in pixels. |
| `--height` | `INTEGER` | `480` | Video frame height in pixels. |
| `--theme` | `STRING` | `cyan` | Initial color theme: `cyan`, `amber`, `violet`, or `emerald`. |
| `--synthetic` | *None* | `False` | Uses an internal synthetic test video generator instead of physical hardware. |
| `--headless` | *None* | `False` | Runs without opening a GUI window (for automated testing or CI). |
| `--include-virtual` | *None* | `False` | Includes virtual/software video devices in camera enumeration. |
| `--skip-welcome` | *None* | `False` | Skips the holographic welcome and gesture guide screen on launch. |
| `--sync-tracking` | *None* | `False` | Forces MediaPipe inference to run synchronously on the main thread. |
| `--benchmark` | `FRAMES` | *None* | Runs the application for $N$ frames, prints latency/FPS performance stats, and exits. |
| `--save-sample` | `PATH` | *None* | Saves a single rendered frame image to the specified path before exit. |
