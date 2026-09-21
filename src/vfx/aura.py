"""High-performance cached radial aura rendering for holographic objects.

Eliminates per-frame np.ogrid and np.sqrt recomputation across holographic objects
by precomputing bounded radial glow patches and caching them by quantized radius and theme.
"""

from typing import Dict, Tuple, Optional
import cv2
import numpy as np


class AuraCache:
    """Bounded cache for precomputed radial glow / aura patches.

    Eliminates per-frame np.ogrid, np.sqrt, and float32 3D array broadcasting
    across holographic objects.
    """

    def __init__(self, max_entries: int = 64):
        self.max_entries = max_entries
        # Key: (glow_r_quantized, color_tuple, weight_quantized, power_quantized)
        self._standard_cache: Dict[Tuple[int, Tuple[int, int, int], int, int], np.ndarray] = {}
        # Key for planet: (r_quantized, outer_glow_tuple, inner_glow_tuple)
        self._planet_cache: Dict[Tuple[int, Tuple[int, int, int], Tuple[int, int, int]], Tuple[np.ndarray, int]] = {}

    def clear(self) -> None:
        """Flushes all cached aura patches."""
        self._standard_cache.clear()
        self._planet_cache.clear()

    def get_standard_aura(
        self,
        glow_r: int,
        color_bgr: Tuple[int, int, int],
        weight: float = 0.42,
        power: float = 2.2,
    ) -> np.ndarray:
        """Returns cached BGR uint8 radial glow patch of size (2*glow_r+1, 2*glow_r+1, 3)."""
        r_key = max(2, int(round(glow_r)))
        w_key = int(round(weight * 100))
        p_key = int(round(power * 10))
        c_key = (int(color_bgr[0]), int(color_bgr[1]), int(color_bgr[2]))
        cache_key = (r_key, c_key, w_key, p_key)

        cached = self._standard_cache.get(cache_key)
        if cached is not None:
            return cached

        # Generate precomputed patch
        py, px = np.ogrid[-r_key : r_key + 1, -r_key : r_key + 1]
        dist = np.sqrt(px * px + py * py)
        aura = np.clip(1.0 - (dist / float(r_key)), 0.0, 1.0) ** power
        aura_w = np.array(color_bgr, dtype=np.float32) * weight
        patch = np.clip(aura[:, :, None] * aura_w, 0, 255).astype(np.uint8)

        if len(self._standard_cache) >= self.max_entries:
            self._standard_cache.clear()

        self._standard_cache[cache_key] = patch
        return patch

    def render_standard_aura(
        self,
        target: np.ndarray,
        center_x: float,
        center_y: float,
        glow_r: int,
        color_bgr: Tuple[int, int, int],
        weight: float = 0.42,
        power: float = 2.2,
    ) -> None:
        """Composites standard radial aura onto target frame/ROI with bounds clipping."""
        r_int = max(2, int(round(glow_r)))
        if r_int <= 3:
            return

        patch = self.get_standard_aura(r_int, color_bgr, weight, power)

        h, w = target.shape[:2]
        cx = int(round(center_x))
        cy = int(round(center_y))

        # Target bounds
        x1 = max(0, cx - r_int)
        y1 = max(0, cy - r_int)
        x2 = min(w, cx + r_int + 1)
        y2 = min(h, cy + r_int + 1)

        if x2 <= x1 or y2 <= y1:
            return

        # Source patch sub-slice
        sx1 = x1 - (cx - r_int)
        sy1 = y1 - (cy - r_int)
        sx2 = sx1 + (x2 - x1)
        sy2 = sy1 + (y2 - y1)

        cv2.add(target[y1:y2, x1:x2], patch[sy1:sy2, sx1:sx2], dst=target[y1:y2, x1:x2])

    def get_planet_halo(
        self,
        r: int,
        outer_glow: Tuple[int, int, int],
        inner_glow: Tuple[int, int, int],
    ) -> Tuple[np.ndarray, int]:
        """Returns cached atmospheric halo patch and halo half-box size for planet."""
        r_int = max(2, int(round(r)))
        c_out = (int(outer_glow[0]), int(outer_glow[1]), int(outer_glow[2]))
        c_in = (int(inner_glow[0]), int(inner_glow[1]), int(inner_glow[2]))
        cache_key = (r_int, c_out, c_in)

        cached = self._planet_cache.get(cache_key)
        if cached is not None:
            return cached

        glow_box = int(r_int * 1.7)
        # Note: box size is glow_box * 2 + 1 to keep symmetric centering
        py, px = np.ogrid[-glow_box : glow_box + 1, -glow_box : glow_box + 1]
        dist = np.sqrt(px * px + py * py)

        limb = np.clip(1.0 - (np.abs(dist - r_int) / float(r_int * 0.7)), 0.0, 1.0) ** 2.0
        core_sphere = np.clip(1.0 - (dist / float(r_int)), 0.0, 1.0) ** 1.5

        limb_w = np.array(outer_glow, dtype=np.float32) * 0.75
        core_w = np.array(inner_glow, dtype=np.float32) * 0.95
        glow_bgr = limb[:, :, None] * limb_w + core_sphere[:, :, None] * core_w
        patch = np.clip(glow_bgr, 0, 255).astype(np.uint8)

        if len(self._planet_cache) >= self.max_entries:
            self._planet_cache.clear()

        entry = (patch, glow_box)
        self._planet_cache[cache_key] = entry
        return entry

    def render_planet_halo(
        self,
        target: np.ndarray,
        center_x: float,
        center_y: float,
        r: float,
        outer_glow: Tuple[int, int, int],
        inner_glow: Tuple[int, int, int],
    ) -> None:
        """Composites planet atmospheric halo onto target frame/ROI with bounds clipping."""
        r_int = max(2, int(round(r)))
        patch, glow_box = self.get_planet_halo(r_int, outer_glow, inner_glow)

        h, w = target.shape[:2]
        cx = int(round(center_x))
        cy = int(round(center_y))

        x1 = max(0, cx - glow_box)
        y1 = max(0, cy - glow_box)
        x2 = min(w, cx + glow_box + 1)
        y2 = min(h, cy + glow_box + 1)

        if x2 <= x1 or y2 <= y1:
            return

        sx1 = x1 - (cx - glow_box)
        sy1 = y1 - (cy - glow_box)
        sx2 = sx1 + (x2 - x1)
        sy2 = sy1 + (y2 - y1)

        cv2.add(target[y1:y2, x1:x2], patch[sy1:sy2, sx1:sx2], dst=target[y1:y2, x1:x2])


# Shared global singleton instance
_GLOBAL_AURA_CACHE = AuraCache()


def get_aura_cache() -> AuraCache:
    """Returns shared global AuraCache instance."""
    return _GLOBAL_AURA_CACHE
