"""Entrypoint for the Hand-Tracked Holographic VFX System.

Usage:
    python main.py
    python main.py --list-cameras
    python main.py --camera-id 0 --theme cyan
    python main.py --synthetic --theme violet
    python main.py --benchmark 120 --headless
"""

import argparse
import datetime
from pathlib import Path
import sys
import time
import traceback
import cv2

from src.app import HolographicVFXApp
from src.camera import detect_available_cameras
from src.paths import write_crash_log, get_crash_log_path
from src.vfx.color_themes import THEME_KEYS


def parse_args():
    parser = argparse.ArgumentParser(
        description="Hand-Tracked Holographic VFX System - Interactive glowing orb experience"
    )
    parser.add_argument(
        "--camera-id",
        type=int,
        default=0,
        help="Webcam device index (default: 0)",
    )
    parser.add_argument(
        "--list-cameras",
        action="store_true",
        help="Detect and list available video input devices and exit",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=640,
        help="Frame width in pixels (default: 640)",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=480,
        help="Frame height in pixels (default: 480)",
    )
    parser.add_argument(
        "--theme",
        type=str,
        default="cyan",
        choices=THEME_KEYS,
        help=f"Color theme: {', '.join(THEME_KEYS)} (default: cyan)",
    )
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Use synthetic test video feed instead of physical webcam",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without GUI window (for benchmarking or automated environments)",
    )
    parser.add_argument(
        "--include-virtual",
        action="store_true",
        help="Include virtual/software cameras in device detection and listing",
    )
    parser.add_argument(
        "--skip-welcome",
        action="store_true",
        help="Skip the holographic welcome screen on startup",
    )
    parser.add_argument(
        "--sync-tracking",
        action="store_true",
        help="Run hand tracking synchronously on main thread (disables decoupled background worker)",
    )
    parser.add_argument(
        "--benchmark",
        type=int,
        default=None,
        metavar="FRAMES",
        help="Run for N frames, print performance benchmark statistics, and exit",
    )
    parser.add_argument(
        "--save-sample",
        type=str,
        default=None,
        metavar="PATH",
        help="Path to save a sample rendered output image before exiting",
    )
    return parser.parse_args()


def _handle_fatal_exception(exc: Exception, headless: bool = False) -> None:
    """Logs fatal exceptions to crash_log.txt and displays a native error dialog on Windows."""
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tb = traceback.format_exc()

    crash_report = (
        "============================================================\n"
        "  Holographic VFX - Fatal Application Crash Report\n"
        "============================================================\n"
        f"Timestamp : {now_str}\n"
        f"Platform  : {sys.platform} (Python {sys.version.split()[0]})\n"
        f"Error Type: {type(exc).__name__}\n"
        f"Message   : {exc}\n"
        "------------------------------------------------------------\n"
        "Traceback:\n"
        f"{tb}\n"
        "============================================================\n"
    )

    # Output to stderr for console execution
    print(f"\n[Fatal Error] {type(exc).__name__}: {exc}", file=sys.stderr)
    print(tb, file=sys.stderr)

    # Persist report to user capture directory
    saved_log_path = write_crash_log(crash_report)
    log_location_str = str(saved_log_path) if saved_log_path else "Pictures/HolographicVFX/crash_log.txt"

    # Display native GUI error message box on Windows when not headless
    if sys.platform == "win32" and not headless:
        try:
            import ctypes
            error_title = "Holographic VFX - Application Error"
            error_message = (
                f"Holographic VFX encountered an unexpected error:\n\n"
                f"{type(exc).__name__}: {exc}\n\n"
                f"A diagnostic crash report has been saved to:\n{log_location_str}\n\n"
                f"Please check the log or report this issue if it persists."
            )
            # MB_OK (0x00) | MB_ICONERROR (0x10) | MB_SYSTEMMODAL (0x1000)
            ctypes.windll.user32.MessageBoxW(0, error_message, error_title, 0x10 | 0x1000)
        except Exception:
            pass


def main():
    args = parse_args()

    if args.list_cameras:
        print("\nScanning for available video devices...")
        devices = detect_available_cameras(
            max_devices=6,
            include_synthetic=True,
            include_virtual=args.include_virtual,
        )
        print(f"Found {len(devices)} device(s):")
        for i, dev in enumerate(devices):
            if dev.is_synthetic:
                tag = "[Synthetic]"
            elif getattr(dev, "is_physical", True):
                tag = f"[Physical, Device ID: {dev.device_id}]"
            else:
                tag = f"[Virtual, Device ID: {dev.device_id}]"
            print(f"  [{i + 1}] {dev.name:<32} {tag}")
        sys.exit(0)

    print("=" * 60)
    print("  HAND-TRACKED HOLOGRAPHIC VFX SYSTEM")
    print("=" * 60)
    print(f" Camera ID   : {args.camera_id} {'(Synthetic)' if args.synthetic else '(Physical)'}")
    print(f" Resolution  : {args.width}x{args.height}")
    print(f" Theme       : {args.theme}")
    print(f" Headless    : {args.headless}")
    if args.benchmark:
        print(f" Benchmark   : {args.benchmark} frames")
    print("-" * 60)
    print(" Controls:")
    print("   [Pinch]     : Grab & move holographic object / Pinch-to-click UI")
    print("   [Menu Dwell]: Move open palm to top-right [ MENU ] corner to toggle menu")
    print("   [2nd Hand]  : Scroll menu up / down with secondary hand")
    print("   [1 .. 6]    : Switch object (Orb, Cube, Planet, Ghost Orchid, Bhondu, Jellyfish)")
    print("   [M]         : Toggle touchless holographic menu")
    print("   [Tab / I]   : Cycle mode: Standard 2-Hand vs Independent Dual-Hand")
    print("   [V]         : Switch camera input source")
    print("   [C]         : Cycle color themes")
    print("   [R]         : Reset object to center")
    print("   [H]         : Toggle skeleton joints overlay")
    print("   [S]         : Save screenshot")
    print("   [Space/Ent] : Dismiss welcome screen")
    print("   [Q / ESC]   : Close menu / Quit application")
    print("=" * 60)

    app = None
    try:
        app = HolographicVFXApp(
            camera_id=args.camera_id,
            width=args.width,
            height=args.height,
            theme_name=args.theme,
            synthetic_mode=args.synthetic,
            headless=args.headless,
            include_virtual=args.include_virtual,
            skip_welcome=args.skip_welcome or (args.benchmark is not None),
            sync_tracking=args.sync_tracking,
        )

        if args.benchmark:
            mode_str = "Synchronous" if args.sync_tracking else "Asynchronous Decoupled"
            print(f"[Benchmark] Running {args.benchmark} frames ({mode_str} Tracking)...")
            if not app.camera_selector.open():
                print("[Benchmark] Initial camera open failed, using fallback...")

            start_t = time.perf_counter()
            latencies = []
            tracking_fps_list = []
            landmark_ages = []
            dropped_frames = 0
            sample_frame = None

            for i in range(args.benchmark):
                f_start = time.perf_counter()
                ret, frame, telemetry = app.step_frame()
                f_dur = time.perf_counter() - f_start
                latencies.append(f_dur * 1000.0)
                if ret and frame is not None:
                    sample_frame = frame
                    if "tracking_fps" in telemetry and telemetry["tracking_fps"] > 0:
                        tracking_fps_list.append(telemetry["tracking_fps"])
                    if "landmark_age_ms" in telemetry and telemetry["landmark_age_ms"] > 0:
                        landmark_ages.append(telemetry["landmark_age_ms"])
                    dropped_frames = telemetry.get("tracking_dropped_frames", 0)

            total_t = time.perf_counter() - start_t
            app.close()

            avg_lat = sum(latencies) / len(latencies)
            avg_fps = len(latencies) / total_t
            min_lat = min(latencies)
            max_lat = max(latencies)

            print("\n--- Benchmark Results ---")
            print(f" Total Frames       : {len(latencies)}")
            print(f" Total Time         : {total_t:.2f} s")
            print(f" Render FPS         : {avg_fps:.1f} FPS")
            print(f" Avg Frame Latency  : {avg_lat:.2f} ms")
            print(f" Min Latency        : {min_lat:.2f} ms")
            print(f" Max Latency        : {max_lat:.2f} ms")
            print(f" Tracking Mode      : {mode_str}")
            if tracking_fps_list:
                avg_trk_fps = sum(tracking_fps_list) / len(tracking_fps_list)
                print(f" Tracking Worker FPS: {avg_trk_fps:.1f} FPS")
            if landmark_ages:
                avg_age = sum(landmark_ages) / len(landmark_ages)
                print(f" Avg Landmark Age   : {avg_age:.2f} ms")
            if not args.sync_tracking:
                print(f" Dropped Frames     : {dropped_frames}")
            print("-------------------------")

            if args.save_sample and sample_frame is not None:
                sample_path = Path(args.save_sample)
                sample_path.parent.mkdir(parents=True, exist_ok=True)
                ok, enc = cv2.imencode(".png", sample_frame)
                if ok and enc is not None:
                    sample_path.write_bytes(enc.tobytes())
                    print(f"[Info] Saved sample frame to: {sample_path.resolve()}")

            sys.exit(0)

        app.run()
    except Exception as e:
        _handle_fatal_exception(e, headless=args.headless)
        if app is not None:
            try:
                app.close()
            except Exception:
                pass
        sys.exit(1)


if __name__ == "__main__":
    main()
