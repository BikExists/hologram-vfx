"""Holographic VFX Color Themes and Palettes.

Defines BGR color palettes for core, glow, rings, particles, and HUD.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class ColorTheme:
    name: str
    core: Tuple[int, int, int]          # BGR, central white-hot core
    inner_glow: Tuple[int, int, int]    # BGR, intense luminous halo
    outer_glow: Tuple[int, int, int]    # BGR, diffuse ambient halo
    ring_primary: Tuple[int, int, int]  # BGR, main rotating ring
    ring_secondary: Tuple[int, int, int]# BGR, secondary ring / ticks
    particle: Tuple[int, int, int]      # BGR, swirling particles
    tether: Tuple[int, int, int]        # BGR, electric pinch tether
    shockwave: Tuple[int, int, int]     # BGR, expanding ripple
    hud_accent: Tuple[int, int, int]    # BGR, HUD text & borders


THEMES: Dict[str, ColorTheme] = {
    "cyan": ColorTheme(
        name="Cyber Cyan",
        core=(255, 255, 255),
        inner_glow=(255, 235, 120),    # Electric bright cyan
        outer_glow=(220, 140, 20),     # Deep cyan / blue
        ring_primary=(255, 240, 100),
        ring_secondary=(200, 180, 40),
        particle=(255, 255, 180),
        tether=(255, 245, 160),
        shockwave=(255, 220, 80),
        hud_accent=(255, 220, 80),
    ),
    "solar": ColorTheme(
        name="Solar Flare",
        core=(255, 255, 255),
        inner_glow=(80, 180, 255),     # Warm golden amber
        outer_glow=(10, 80, 240),      # Fiery orange-red
        ring_primary=(60, 190, 255),
        ring_secondary=(30, 120, 240),
        particle=(120, 220, 255),
        tether=(90, 210, 255),
        shockwave=(50, 160, 255),
        hud_accent=(60, 190, 255),
    ),
    "violet": ColorTheme(
        name="Neon Violet",
        core=(255, 255, 255),
        inner_glow=(255, 120, 220),    # Bright magenta-violet
        outer_glow=(180, 20, 120),     # Deep purple
        ring_primary=(255, 140, 240),
        ring_secondary=(210, 70, 180),
        particle=(255, 180, 250),
        tether=(255, 160, 240),
        shockwave=(240, 100, 210),
        hud_accent=(240, 120, 220),
    ),
    "matrix": ColorTheme(
        name="Emerald Matrix",
        core=(255, 255, 255),
        inner_glow=(120, 255, 140),    # Bright neon lime
        outer_glow=(30, 180, 40),      # Deep matrix green
        ring_primary=(100, 255, 120),
        ring_secondary=(40, 200, 60),
        particle=(160, 255, 180),
        tether=(130, 255, 150),
        shockwave=(90, 240, 110),
        hud_accent=(100, 255, 120),
    ),
}

THEME_KEYS: List[str] = list(THEMES.keys())


def get_theme(name: str) -> ColorTheme:
    """Returns theme by key or display name, or defaults to 'cyan'."""
    query = str(name).strip().lower()
    if query in THEMES:
        return THEMES[query]
    for theme in THEMES.values():
        if theme.name.lower() == query:
            return theme
    return THEMES["cyan"]
