"""Smoothing and filtering utilities for hand tracking and orb motion.

Implements the 1-Euro Filter (Casiez et al., 2012) and Exponential Moving Average (EMA).
The 1-Euro Filter provides high precision and jitter reduction at low speeds
while minimizing lag during rapid movements.
"""

import math
import time
from typing import Optional, Tuple, Union
import numpy as np


class LowPassFilter:
    """First-order low-pass filter."""

    def __init__(self, alpha: float = 0.5):
        self.alpha = float(alpha)
        self.y: Optional[Union[float, np.ndarray]] = None

    def reset(self) -> None:
        self.y = None

    def filter(self, value: Union[float, np.ndarray], alpha: Optional[float] = None) -> Union[float, np.ndarray]:
        if alpha is not None:
            self.alpha = float(alpha)
        if self.y is None:
            self.y = np.copy(value) if isinstance(value, np.ndarray) else float(value)
            return self.y
        self.y = self.alpha * value + (1.0 - self.alpha) * self.y
        return self.y

    def last_value(self) -> Optional[Union[float, np.ndarray]]:
        return self.y


class OneEuroFilter:
    """1-Euro filter for reducing jitter and lag in interactive tracking.

    Parameters
    ----------
    freq : float
        Estimated sample rate in Hz (default: 30.0).
    mincutoff : float
        Minimum cutoff frequency in Hz. Lower values reduce jitter when stationary.
    beta : float
        Speed coefficient. Higher values reduce lag during high-velocity movements.
    dcutoff : float
        Cutoff frequency for the derivative filter in Hz.
    """

    def __init__(
        self,
        freq: float = 30.0,
        mincutoff: float = 1.0,
        beta: float = 0.05,
        dcutoff: float = 1.0,
    ):
        self.freq = max(1e-4, float(freq))
        self.mincutoff = float(mincutoff)
        self.beta = float(beta)
        self.dcutoff = float(dcutoff)

        self.x_filt = LowPassFilter()
        self.dx_filt = LowPassFilter()
        self.last_time: Optional[float] = None

    def reset(self) -> None:
        self.x_filt.reset()
        self.dx_filt.reset()
        self.last_time = None

    def _alpha(self, cutoff: float, dt: float) -> float:
        tau = 1.0 / (2.0 * math.pi * max(cutoff, 1e-4))
        return 1.0 / (1.0 + tau / max(dt, 1e-5))

    def filter(
        self,
        value: Union[float, np.ndarray],
        timestamp: Optional[float] = None,
    ) -> Union[float, np.ndarray]:
        """Filters a scalar or numpy array sample with optional timestamp."""
        now = time.perf_counter() if timestamp is None else timestamp

        if self.last_time is None or self.x_filt.y is None:
            self.last_time = now
            return self.x_filt.filter(value)

        dt = now - self.last_time
        self.last_time = now
        if dt <= 0.0:
            dt = 1.0 / self.freq

        # Estimate derivative
        dx = (value - self.x_filt.y) / dt
        edx = self.dx_filt.filter(dx, self._alpha(self.dcutoff, dt))

        # Speed-dependent cutoff
        cutoff = self.mincutoff + self.beta * float(np.linalg.norm(edx) if isinstance(edx, np.ndarray) else abs(edx))
        return self.x_filt.filter(value, self._alpha(cutoff, dt))


class PointFilter:
    """Convenience filter for 2D or 3D coordinate points (x, y) or (x, y, z)."""

    def __init__(self, mincutoff: float = 1.2, beta: float = 0.03):
        self.filter = OneEuroFilter(mincutoff=mincutoff, beta=beta)

    def reset(self) -> None:
        self.filter.reset()

    def filter_pt(self, pt: Tuple[float, ...], timestamp: Optional[float] = None) -> Tuple[float, ...]:
        arr = np.array(pt, dtype=np.float64)
        filtered = self.filter.filter(arr, timestamp=timestamp)
        return tuple(filtered.tolist())


class EMAFilter:
    """Exponential Moving Average filter."""

    def __init__(self, alpha: float = 0.25):
        self.alpha = float(np.clip(alpha, 0.01, 1.0))
        self.value: Optional[Union[float, np.ndarray]] = None

    def reset(self) -> None:
        self.value = None

    def filter(self, new_val: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        if self.value is None:
            self.value = np.copy(new_val) if isinstance(new_val, np.ndarray) else float(new_val)
            return self.value
        self.value = self.alpha * new_val + (1.0 - self.alpha) * self.value
        return self.value
