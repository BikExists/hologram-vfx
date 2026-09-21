# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification file for Holographic VFX Standalone Application.

Target: Windows standalone application (x86_64)
Mode: --onedir + --windowed (console=False)
"""

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all MediaPipe model graphs, tflite binaries, and metadata descriptors
mediapipe_datas = collect_data_files('mediapipe')

# Collect OpenCV submodules
cv2_submodules = collect_submodules('cv2')

# Collect MediaPipe submodules (excluding optional genai/torch converters)
mp_submodules = [
    sub for sub in collect_submodules('mediapipe')
    if 'genai' not in sub and 'torch' not in sub
]

# Explicit hidden imports to guarantee dynamic reflection resolves
hidden_imports = [
    'mediapipe',
    'mediapipe.python',
    'mediapipe.python.solutions',
    'mediapipe.python.solutions.hands',
    'cv2',
    'numpy',
    'src',
    'src.app',
    'src.camera',
    'src.filters',
    'src.gestures',
    'src.hand_tracker',
    'src.tracking_worker',
    'src.interaction',
    'src.paths',
    'src.objects',
    'src.objects.base',
    'src.objects.orb',
    'src.objects.cube',
    'src.objects.planet',
    'src.objects.ghost_orchid',
    'src.objects.bhondu_face',
    'src.objects.jellyfish',
    'src.objects.manager',
    'src.ui',
    'src.ui.cursor',
    'src.ui.manager',
    'src.ui.menu',
    'src.ui.state',
    'src.ui.trigger_zone',
    'src.ui.welcome',
    'src.vfx',
    'src.vfx.aura',
    'src.vfx.color_themes',
    'src.vfx.hud',
    'src.vfx.orb_renderer',
    'src.vfx.particles',
    'src.vfx.presenter',
] + cv2_submodules + mp_submodules

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=mediapipe_datas + [('assets', 'assets')],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'IPython', 'jupyter', 'pytest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher,
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='HolographicVFX',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Windowed desktop application (no console window)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='HolographicVFX',
)
