"""Entrypoint for the Hand-Tracked Holographic VFX System.

Usage:
    python main.py
    python main.py --list-cameras
    python main.py --camera-id 0 --theme cyan
    python main.py --synthetic --theme violet
    python main.py --benchmark 120 --headless
"""

import argparse
import sys
import time
import cv2

from src.app import HolographicVFXApp
from src.camera import detect_available_cameras
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


def main():
    args = parse_args()

    if args.list_cameras:
        print("\nScanning for available video devices...")
        devices = detect_available_cameras(max_devices=6, include_synthetic=True)
        print(f"Found {len(devices)} device(s):")
        for i, dev in enumerate(devices):
            tag = "[Synthetic]" if dev.is_synthetic else f"[Device ID: {dev.device_id}]"
            print(f"  [{i + 1}] {dev.name:<25} {tag}")
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
    print("   [Pinch]     : Grab and move holographic object")
    print("   [Open/Close]: Expand / shrink object size")
    print("   [1 / 2 / 3] : Switch object: 1=Orb, 2=Cube, 3=Planet")
    print("   [V]         : Switch camera input source")
    print("   [C]         : Cycle color themes")
    print("   [R]         : Reset object to center")
    print("   [H]         : Toggle skeleton joints overlay")
    print("   [S]         : Save screenshot")
    print("   [Q / ESC]   : Quit application")
    print("=" * 60)

    app = HolographicVFXApp(
        camera_id=args.camera_id,
        width=args.width,
        height=args.height,
        theme_name=args.theme,
        synthetic_mode=args.synthetic,
        headless=args.headless,
    )

    if args.benchmark:
        print(f"[Benchmark] Running {args.benchmark} frames...")
        if not app.camera_selector.open():
            print("[Benchmark] Initial camera open failed, using fallback...")

        start_t = time.perf_counter()
        latencies = []
        sample_frame = None

        for i in range(args.benchmark):
            f_start = time.perf_counter()
            ret, frame, telemetry = app.step_frame()
            f_dur = time.perf_counter() - f_start
            latencies.append(f_dur * 1000.0)
            if ret and frame is not None:
                sample_frame = frame

        total_t = time.perf_counter() - start_t
        app.close()

        avg_lat = sum(latencies) / len(latencies)
        avg_fps = len(latencies) / total_t
        min_lat = min(latencies)
        max_lat = max(latencies)

        print("\n--- Benchmark Results ---")
        print(f" Total Frames : {len(latencies)}")
        print(f" Total Time   : {total_t:.2f} s")
        print(f" Average FPS  : {avg_fps:.1f} FPS")
        print(f" Avg Latency  : {avg_lat:.2f} ms")
        print(f" Min Latency  : {min_lat:.2f} ms")
        print(f" Max Latency  : {max_lat:.2f} ms")
        print("-------------------------")

        if args.save_sample and sample_frame is not None:
            cv2.imwrite(args.save_sample, sample_frame)
            print(f"[Info] Saved sample frame to: {args.save_sample}")

        sys.exit(0)

    try:
        app.run()
    except Exception as e:
        print(f"[Fatal Error] Application encountered an error: {e}", file=sys.stderr)
        app.close()
        sys.exit(1)


if __name__ == "__main__":
    main()
