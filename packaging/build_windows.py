"""Reproducible build and distribution script for Holographic VFX on Windows.

Workflow:
1. PyInstaller: Compiles HolographicVFX into dist/HolographicVFX/ (--onedir, windowed, icon)
2. Portable ZIP: Packages dist/HolographicVFX into dist/HolographicVFX-v0.1.0-dev-Windows-x64.zip
3. Inno Setup: Compiles packaging/installer.iss into dist/HolographicVFX-v0.1.0-dev-Windows-x64-Setup.exe

Usage:
    python packaging/build_windows.py [--all | --zip | --installer | --pyinstaller]
"""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

REPO_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = REPO_ROOT / "dist"
BUILD_DIR = REPO_ROOT / "build"
ASSETS_DIR = REPO_ROOT / "assets"
SPEC_FILE = REPO_ROOT / "HolographicVFX.spec"
ISS_FILE = REPO_ROOT / "packaging" / "installer.iss"

VERSION = "0.1.0-dev"
APP_NAME = "HolographicVFX"
ZIP_NAME = f"{APP_NAME}-v{VERSION}-Windows-x64.zip"
SETUP_NAME = f"{APP_NAME}-v{VERSION}-Windows-x64-Setup.exe"


def find_iscc() -> Path:
    """Finds Inno Setup Compiler (ISCC.exe)."""
    # 1. Check in PATH
    iscc_path = shutil.which("iscc") or shutil.which("ISCC")
    if iscc_path:
        return Path(iscc_path)

    # 2. Check standard installation locations
    candidate_paths = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles", "")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Inno Setup 5" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles", "")) / "Inno Setup 5" / "ISCC.exe",
    ]
    for p in candidate_paths:
        if p.is_file():
            return p

    raise FileNotFoundError(
        "Inno Setup Compiler (ISCC.exe) not found. "
        "Please install Inno Setup 6 (via winget install JRSoftware.InnoSetup or from https://jrsoftware.org/isdl.php)."
    )


def build_pyinstaller():
    """Runs PyInstaller using HolographicVFX.spec."""
    print("=" * 60)
    print("Step 1: Running PyInstaller...")
    print("=" * 60)
    cmd = [sys.executable, "-m", "PyInstaller", str(SPEC_FILE), "-y"]
    print(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(REPO_ROOT))
    if result.returncode != 0:
        raise RuntimeError(f"PyInstaller build failed with exit code {result.returncode}")
    print("[Success] PyInstaller build completed successfully.")


def create_portable_zip():
    """Creates the portable distribution ZIP archive containing the HolographicVFX directory."""
    print("=" * 60)
    print("Step 2: Creating Portable ZIP Archive...")
    print("=" * 60)
    app_dir = DIST_DIR / APP_NAME
    if not app_dir.is_dir():
        raise FileNotFoundError(f"Standalone application folder not found at {app_dir}. Build PyInstaller first.")

    target_zip = DIST_DIR / ZIP_NAME
    if target_zip.exists():
        target_zip.unlink()

    print(f"Archiving {app_dir} -> {target_zip}...")
    with zipfile.ZipFile(target_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for root, dirs, files in os.walk(app_dir):
            for file in files:
                abs_path = Path(root) / file
                rel_path = abs_path.relative_to(DIST_DIR)
                zf.write(abs_path, arcname=str(rel_path))

    size_mb = target_zip.stat().st_size / (1024 * 1024)
    print(f"[Success] Portable ZIP created: {target_zip} ({size_mb:.2f} MB)")
    return target_zip


def build_installer():
    """Compiles the Inno Setup installer."""
    print("=" * 60)
    print("Step 3: Building Inno Setup Installer...")
    print("=" * 60)
    iscc_exe = find_iscc()
    print(f"Using Inno Setup compiler: {iscc_exe}")

    cmd = [str(iscc_exe), str(ISS_FILE)]
    print(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(REPO_ROOT))
    if result.returncode != 0:
        raise RuntimeError(f"Inno Setup compilation failed with exit code {result.returncode}")

    target_setup = DIST_DIR / SETUP_NAME
    if not target_setup.is_file():
        raise FileNotFoundError(f"Expected installer not found at {target_setup}")

    size_mb = target_setup.stat().st_size / (1024 * 1024)
    print(f"[Success] Installer created: {target_setup} ({size_mb:.2f} MB)")
    return target_setup


def main():
    parser = argparse.ArgumentParser(description="Build Holographic VFX Windows Distribution Artifacts")
    parser.add_argument("--pyinstaller", action="store_true", help="Run PyInstaller build")
    parser.add_argument("--zip", action="store_true", help="Create portable ZIP archive")
    parser.add_argument("--installer", action="store_true", help="Build Inno Setup installer")
    parser.add_argument("--all", action="store_true", help="Run complete build (PyInstaller + ZIP + Installer)")

    args = parser.parse_args()

    # Default to --all if no specific action specified
    if not (args.pyinstaller or args.zip or args.installer or args.all):
        args.all = True

    try:
        if args.all or args.pyinstaller:
            build_pyinstaller()
        if args.all or args.zip:
            create_portable_zip()
        if args.all or args.installer:
            build_installer()

        print("\n" + "=" * 60)
        print("DISTRIBUTION BUILD SUMMARY")
        print("=" * 60)
        zip_path = DIST_DIR / ZIP_NAME
        setup_path = DIST_DIR / SETUP_NAME
        if zip_path.is_file():
            print(f"Portable Archive: {zip_path.name} ({zip_path.stat().st_size / (1024*1024):.2f} MB)")
        if setup_path.is_file():
            print(f"Windows Setup:    {setup_path.name} ({setup_path.stat().st_size / (1024*1024):.2f} MB)")
        print("=" * 60)

    except Exception as e:
        print(f"\n[Error] Build failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
