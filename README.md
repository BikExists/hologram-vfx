# Hand-Tracked Holographic VFX System

[![Windows Standalone](https://img.shields.io/badge/Windows-v0.1.1--dev-blue?logo=windows)](https://github.com/BikExists/hologram-vfx/releases/tag/v0.1.1-dev)
[![Python Tests](https://img.shields.io/badge/Tests-197%20Passed-brightgreen)](https://github.com/BikExists/hologram-vfx)

A real-time interactive computer vision application that tracks your hands via webcam to manipulate virtual 3D holographic objects and visual effects in mid-air.

---

## What Holographic VFX Does

Holographic VFX turns your standard webcam into an interactive touchless spatial interface. By tracking your hand joints in real time, you can:

- **Grab and Move**: Pinch your thumb and index finger together to grab virtual 3D objects and move them through space.
- **Dynamic Scale**: Open your hand wide to expand objects into massive glowing energy structures, or close your fingers into a fist to compress them down into a compact core.
- **Dual-Hand Control**: Use two hands simultaneously to manipulate orientation, distance-based scaling, or independently control scale and color themes.
- **Touchless Holographic Menu**: Hover your open palm in the top-right corner to summon a floating sci-fi menu, then pinch to select objects and settings.
- **Instant Snapshots**: Capture high-resolution screenshots of your holographic interactions directly to your Windows Pictures library.

---

## Feature Overview

- **Asynchronous Decoupled Tracking Engine**: Hand tracking and rendering run on separate threads. The render engine updates smoothly without being locked to webcam capture latency.
- **6 Interactive Holographic Objects**:
  1. **Energy Orb** (`[1]`): The signature holographic sphere with tri-axial rotating gyroscopic rings, orbiting Keplerian particle cloud, electric plasma pinch tethers, and shockwaves.
  2. **Cyber Cube** (`[2]`): A rotating 3D wireframe cube with glowing perspective edges, depth-sorted scanline faces, and luminous vertex beacons.
  3. **Holographic Planet** (`[3]`): A celestial planet with atmospheric limb glow, rotating latitude bands, concentric Saturn-like rings, and an orbiting moon with a dust trail.
  4. **Ghost Orchid** (`[4]`): An organic holographic botanical structure with procedural bioluminescent petals.
  5. **Bhondu Face** (`[5]`): A stylized geometric character hologram.
  6. **Jellyfish** (`[6]`): An undulating bioluminescent deep-sea creature with dynamic flowing tentacles.
- **4 Holographic Color Themes**: Cyber Cyan, Solar Flare, Neon Violet, and Emerald Matrix.
- **Aspect-Ratio Aware Presentation**: Automatically conforms to any camera resolution (16:9, 4:3, widescreen) with viewport boundary confinement.
- **Multi-Camera Support**: Seamlessly discovers and hot-switches between available camera devices at runtime.

---

## Supported Platform Status

| Platform | Status | Current Version | Notes |
| :--- | :--- | :--- | :--- |
| **Windows (x64)** | **Available** | `v0.1.1-dev` | Standalone Installer and Portable ZIP available. |
| **macOS** | *In Development* | — | macOS packaging is currently paused and will be validated on physical Mac hardware in a future release. |
| **Linux** | *Source Only* | — | Can be run from Python source with V4L2. |

---

## Downloads (Windows Standalone)

Latest Release: [**HolographicVFX v0.1.1-dev**](https://github.com/BikExists/hologram-vfx/releases/tag/v0.1.1-dev)

| Package | Recommended For | Direct Download Link |
| :--- | :--- | :--- |
| **Windows Installer (`.exe`)** | Most Users | [Download Setup (.exe)](https://github.com/BikExists/hologram-vfx/releases/download/v0.1.1-dev/HolographicVFX-v0.1.1-dev-Windows-x64-Setup.exe) |
| **Portable Distribution (`.zip`)** | Zero-install / USB drives | [Download Portable (.zip)](https://github.com/BikExists/hologram-vfx/releases/download/v0.1.1-dev/HolographicVFX-v0.1.1-dev-Windows-x64.zip) |

*Neither package requires Python, Git, or command-line setup. All runtimes, models, and dependencies are self-contained.*

### Verification Checksums (SHA-256)

| Artifact | File Size | SHA-256 Checksum |
| :--- | :--- | :--- |
| `HolographicVFX-v0.1.1-dev-Windows-x64-Setup.exe` | 171.40 MB (179,724,183 bytes) | `65E57E6EFE74106FAAB5CC5A68A781C62EB36C12111AAEAA82AC16BF39C741A5` |
| `HolographicVFX-v0.1.1-dev-Windows-x64.zip` | 244.36 MB (256,230,181 bytes) | `0BB08E172F4FFE0197BACA12B5E34A196F7A79B04B216F49752C9AE37F9B93EE` |

---

## Performance Expectations

- **Real-World Webcam Experience**: In normal usage with a webcam, the application runs smoothly at real-time speeds (typically 30–60 FPS, matching your webcam hardware capabilities). The asynchronous tracking engine decouples visual rendering from computer-vision inference, preventing frame stutter during rapid hand motions.
- **Synthetic Benchmark Mode**: An internal diagnostic tool used during automated testing and CI. Because it does not wait for a physical camera sensor, benchmark results can reach 200–300+ FPS in synthetic/headless environments. This reflects engine throughput rather than expected webcam frame rates.

---

## System Requirements

- **Operating System**: 64-bit Windows 10 or Windows 11.
- **Processor**: 64-bit x86_64 CPU (Intel Core or AMD Ryzen).
- **Webcam**: Any standard integrated laptop camera or external USB webcam.
- **Graphics**: Any standard integrated or dedicated graphics processor supporting modern desktop display.
- **Storage**: ~500 MB free disk space for installation.

---

## Installation & First Run

### Option A: Windows Installer (Recommended)
1. Download `HolographicVFX-v0.1.1-dev-Windows-x64-Setup.exe`.
2. Run the installer. It installs per-user into `%LOCALAPPDATA%\Programs\HolographicVFX` (no administrator privileges or UAC prompts required).
3. Choose whether to place a shortcut on your Desktop.
4. Launch **Holographic VFX** from your Desktop or Start Menu.

### Option B: Portable ZIP
1. Download `HolographicVFX-v0.1.1-dev-Windows-x64.zip`.
2. Right-click the `.zip` file and select **Extract All...**.
3. Open the extracted folder and double-click `HolographicVFX.exe`.

---

## Windows SmartScreen Notice

Because this is a pre-release development build (`v0.1.1-dev`), the binaries have not yet been signed with an expensive commercial Authenticode certificate. When you run the installer or portable executable for the first time, Windows Defender SmartScreen may display:

> **"Windows protected your PC"**  
> *Microsoft Defender SmartScreen prevented an unrecognized app from starting. Running this app might put your PC at risk.*  
> *Publisher: Unknown publisher*

### How to Proceed:
1. Click **More info** on the SmartScreen dialog.
2. Confirm that the application name shows `HolographicVFX.exe` or `HolographicVFX-v0.1.1-dev-Windows-x64-Setup.exe`.
3. Click **Run anyway**.

*Commercial code signing will be added in a future production release milestone once formal distribution certificates are provisioned.*

---

## Interactive Controls & Gestures

| Gesture / Key | Action | Details |
| :--- | :--- | :--- |
| **Pinch (Thumb + Index)** | **Grab & Move / Click** | Pinch to grab the holographic object; pinch-to-click on menu buttons. |
| **Open Hand** | **Expand Scale** | Spreading fingers wide increases object radius and energy intensity. |
| **Closed Fist** | **Shrink Scale** | Clenching fingers shrinks the object down to a dense core. |
| **Top-Right Palm Dwell** | **Toggle Menu** | Move your open palm to the `[ MENU ]` trigger zone at top-right to open the menu. |
| **Secondary Hand (Open/Close)** | **Scroll Menu** | While the menu is open, open or close your other hand to scroll through items. |
| **`[1]` .. `[6]`** | **Switch Object** | `1` = Orb, `2` = Cube, `3` = Planet, `4` = Ghost Orchid, `5` = Bhondu, `6` = Jellyfish. |
| **`[Tab]` / `[I]`** | **Toggle Interaction Mode** | Cycles between **Standard 2-Hand Transform** and **Independent Dual-Hand Control**. |
| **`[C]`** | **Cycle Color Themes** | Steps through Cyber Cyan $\rightarrow$ Solar Flare $\rightarrow$ Neon Violet $\rightarrow$ Emerald Matrix. |
| **`[V]`** | **Switch Camera Source** | Switches to the next available connected webcam. |
| **`[R]`** | **Reset Position** | Re-centers the holographic object to the middle of your screen. |
| **`[H]`** | **Toggle Skeleton Overlay** | Shows or hides the 21-point MediaPipe hand skeleton joints overlay. |
| **`[S]`** | **Save Screenshot** | Saves a timestamped PNG image to your Pictures folder. |
| **`[Space]` / `[Enter]`** | **Dismiss Welcome Screen** | Dismisses the startup tutorial overlay (showing your hand also dismisses it). |
| **`[M]`** | **Keyboard Menu Toggle** | Opens or closes the touchless holographic menu. |
| **`[Q]` / `[ESC]`** | **Close Menu / Quit** | Closes the open menu, or exits the application cleanly. |

---

## Screenshot Storage & User Data

When you press `[S]`, Holographic VFX captures a high-resolution screenshot and saves it directly to:

```text
%USERPROFILE%\Pictures\HolographicVFX\
```
*(Typically: `C:\Users\<YourUsername>\Pictures\HolographicVFX\`)*

**User Data Safety**: Your screenshots are stored in your personal Pictures library, completely separate from the application installation directory. Uninstalling or updating the application will **never** delete or alter your screenshots.

---

## Uninstallation

If you installed Holographic VFX using the Windows Installer, you can remove it cleanly at any time using any of these methods:

- **Start Menu**: Open the Start Menu, locate **Uninstall Holographic VFX**, and click it.
- **Windows Settings**: Go to **Settings** $\rightarrow$ **Apps** $\rightarrow$ **Installed apps**, search for **Holographic VFX**, click the `...` menu, and select **Uninstall**.
- **Control Panel**: Open **Control Panel** $\rightarrow$ **Programs and Features**, select **Holographic VFX**, and click **Uninstall**.

The uninstaller cleanly removes all application files, shortcuts, and registry entries. As noted above, your captured screenshots are safely preserved in your Pictures folder.

*(If you used the Portable ZIP version, simply delete the extracted folder).*

---

## Troubleshooting

### Camera Not Detected or Black Screen
1. **Check Camera Connections**: Verify your webcam is plugged in and recognized in Windows Device Manager.
2. **Windows Privacy Settings**: Ensure camera permissions are enabled:
   - Go to **Windows Settings** $\rightarrow$ **Privacy & security** $\rightarrow$ **Camera**.
   - Make sure **Camera access** is toggled **On**.
   - Make sure **Let desktop apps access your camera** is toggled **On**.
3. **Camera Already in Use**: Close any other applications that might have exclusive lock on your camera (such as Zoom, Microsoft Teams, Discord, OBS Studio, Skype, or web browsers).
4. **Switch Cameras**: If you have multiple cameras (such as a virtual camera or secondary webcam), press `[V]` to cycle to the next camera source.

### Application Shows SmartScreen Warning on Startup
This is normal for pre-release unsigned development builds. See the [Windows SmartScreen Notice](#windows-smartscreen-notice) section above for instructions.

### Application Closes Immediately on Launch
- If using the **Portable ZIP**, ensure you extracted the archive fully rather than launching `HolographicVFX.exe` from inside the Windows zip viewer.
- Ensure your system meets the [System Requirements](#system-requirements).

---

## Known Limitations

- **Unsigned Binaries**: Pre-release builds show the Windows SmartScreen "Unknown Publisher" dialog on first run.
- **OpenCV Window Title Bar Icon**: The HighGUI window on Windows displays standard operating system window decorations; custom branding appears on the executable, shortcuts, installer, and taskbar.
- **macOS Build**: Standalone packaging for macOS is currently in development and intentionally paused until verified on physical Apple Silicon hardware.

---

## Building from Source (Developers)

If you wish to contribute to the project or build the application from source:

### Prerequisites
- Python 3.10 or 3.11 (64-bit)
- Git

### Setup & Run
```powershell
# Clone the repository
git clone https://github.com/BikExists/hologram-vfx.git
cd hologram-vfx

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

### Running Tests
```powershell
pytest -v
```

### Building the Windows Standalone Packages
```powershell
# Compiles PyInstaller standalone, creates Portable ZIP, and builds Inno Setup Installer:
python packaging\build_windows.py --all
```
*(Requires [Inno Setup 6](https://jrsoftware.org/isdl.php) installed for the installer package).*

---

## Project Information & Legal

- **Repository**: [https://github.com/BikExists/hologram-vfx](https://github.com/BikExists/hologram-vfx)
- **Issues & Support**: [https://github.com/BikExists/hologram-vfx/issues](https://github.com/BikExists/hologram-vfx/issues)
- **Author / Publisher**: BikExists
- **Third-Party Open Source**: Built with [MediaPipe](https://github.com/google/mediapipe), [OpenCV](https://opencv.org/), [NumPy](https://numpy.org/), and [Pillow](https://python-pillow.org/).
- **Licensing**: Formal licensing documentation will be established in upcoming release milestones prior to the v1.0.0 production release.
