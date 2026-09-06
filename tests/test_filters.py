"""Unit tests for smoothing filters (LowPassFilter, OneEuroFilter, EMAFilter)."""

import math
import numpy as np
import pytest
from src.filters import EMAFilter, LowPassFilter, OneEuroFilter, PointFilter


def test_low_pass_filter():
    lpf = LowPassFilter(alpha=0.5)
    assert lpf.last_value() is None

    # First sample sets initial value
    val = lpf.filter(10.0)
    assert val == 10.0

    # Second sample blends: 0.5 * 20.0 + 0.5 * 10.0 = 15.0
    val2 = lpf.filter(20.0)
    assert val2 == 15.0

    lpf.reset()
    assert lpf.last_value() is None


def test_ema_filter():
    ema = EMAFilter(alpha=0.2)
    assert ema.value is None

    res1 = ema.filter(100.0)
    assert res1 == 100.0

    res2 = ema.filter(50.0)
    # 0.2 * 50 + 0.8 * 100 = 90
    assert abs(res2 - 90.0) < 1e-4

    ema.reset()
    assert ema.value is None


def test_one_euro_filter_stationary_jitter_reduction():
    filt = OneEuroFilter(freq=30.0, mincutoff=1.0, beta=0.01)

    t = 0.0
    dt = 1.0 / 30.0
    base_val = 50.0

    # Feed stationary signal with high-frequency noise
    filtered_values = []
    for i in range(40):
        noise = math.sin(i * 10.0) * 2.0  # High-frequency oscillation
        val = base_val + noise
        out = filt.filter(val, timestamp=t)
        filtered_values.append(out)
        t += dt

    # Filtered variance should be significantly lower than noisy variance
    raw_var = np.var([base_val + math.sin(i * 10.0) * 2.0 for i in range(10, 40)])
    filt_var = np.var(filtered_values[10:])
    assert filt_var < raw_var * 0.4


def test_one_euro_filter_rapid_movement():
    filt = OneEuroFilter(freq=30.0, mincutoff=1.0, beta=0.1)

    t = 0.0
    dt = 1.0 / 30.0

    # Start at 0
    for _ in range(10):
        filt.filter(0.0, timestamp=t)
        t += dt

    # Sudden high-speed jump to 100
    fast_out = filt.filter(100.0, timestamp=t)
    # With high beta and speed, it adapts quickly
    assert fast_out > 20.0


def test_point_filter():
    pf = PointFilter()
    p1 = pf.filter_pt((10.0, 20.0), timestamp=1.0)
    assert abs(p1[0] - 10.0) < 1e-4
    assert abs(p1[1] - 20.0) < 1e-4

    p2 = pf.filter_pt((12.0, 22.0), timestamp=1.033)
    assert isinstance(p2, tuple)
    assert len(p2) == 2
    assert 10.0 < p2[0] < 12.0
    assert 20.0 < p2[1] < 22.0
