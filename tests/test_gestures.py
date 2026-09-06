"""Unit tests for gesture recognition, pinch hysteresis, and openness estimation."""

import pytest
from src.gestures import GestureEstimator


def _create_mock_landmarks(openness_ratio: float = 1.0, pinch_dist: float = 0.6):
    """Creates a synthetic set of 21 MediaPipe hand landmarks in normalized [0, 1] coords.

    openness_ratio: 0.0 (fist) to 1.0 (open hand)
    pinch_dist: distance between thumb tip (4) and index tip (8)
    """
    lms = [(0.5, 0.7, 0.0)] * 21  # Default base (wrist)

    # Wrist at (0.5, 0.8)
    lms[0] = (0.5, 0.8, 0.0)

    # Middle MCP at (0.5, 0.5) -> palm_scale is 0.3
    lms[9] = (0.5, 0.5, 0.0)

    # MCPs
    lms[5] = (0.42, 0.52, 0.0)   # Index MCP
    lms[13] = (0.58, 0.52, 0.0)  # Ring MCP
    lms[17] = (0.65, 0.55, 0.0)  # Pinky MCP
    lms[2] = (0.38, 0.70, 0.0)   # Thumb MCP

    # Fingertips extended proportional to openness_ratio
    # Open: tip y ~ 0.2-0.3; Closed: tip y ~ 0.55-0.65
    tip_y_open = 0.25
    tip_y_closed = 0.60
    current_tip_y = tip_y_closed + (tip_y_open - tip_y_closed) * openness_ratio

    lms[4] = (0.45 - pinch_dist * 0.15, current_tip_y + pinch_dist * 0.1, 0.0)   # Thumb tip
    lms[8] = (0.45 + pinch_dist * 0.15, current_tip_y, 0.0)                      # Index tip
    lms[12] = (0.50, current_tip_y, 0.0)                                          # Middle tip
    lms[16] = (0.58, current_tip_y, 0.0)                             # Ring tip
    lms[20] = (0.65, current_tip_y, 0.0)                             # Pinky tip

    return lms


def test_pinch_hysteresis_state_machine():
    estimator = GestureEstimator(pinch_grab_thresh=0.35, pinch_release_thresh=0.55)

    # 1. Start with fingers far apart (pinch_dist = 0.8) -> not pinching
    lms_open = _create_mock_landmarks(openness_ratio=1.0, pinch_dist=0.8)
    metrics1 = estimator.compute_metrics(lms_open, 640, 480, timestamp=1.0)
    assert not metrics1["is_pinching"]

    # 2. Fingers close tightly together (pinch_dist = 0.15) -> enters pinching
    lms_pinched = _create_mock_landmarks(openness_ratio=0.5, pinch_dist=0.15)
    for t in [1.033, 1.066, 1.099]:
        metrics2 = estimator.compute_metrics(lms_pinched, 640, 480, timestamp=t)
    assert metrics2["is_pinching"]

    # 3. Fingers separate slightly to intermediate threshold (pinch_dist = 0.45)
    # Due to hysteresis, should REMAIN pinching!
    lms_intermediate = _create_mock_landmarks(openness_ratio=0.5, pinch_dist=0.42)
    for t in [1.133, 1.166]:
        metrics3 = estimator.compute_metrics(lms_intermediate, 640, 480, timestamp=t)
    assert metrics3["is_pinching"]

    # 4. Fingers separate past release threshold (pinch_dist = 0.9) -> releases
    lms_released = _create_mock_landmarks(openness_ratio=1.0, pinch_dist=0.9)
    for t in [1.200, 1.233, 1.266]:
        metrics4 = estimator.compute_metrics(lms_released, 640, 480, timestamp=t)
    assert not metrics4["is_pinching"]


def test_hand_openness_scaling():
    estimator = GestureEstimator()

    # Closed fist
    lms_fist = _create_mock_landmarks(openness_ratio=0.0, pinch_dist=0.3)
    fist_metrics = None
    for t in [1.0, 1.033, 1.066, 1.099, 1.133]:
        fist_metrics = estimator.compute_metrics(lms_fist, 640, 480, timestamp=t)

    assert fist_metrics is not None
    assert 0.0 <= fist_metrics["openness"] < 0.35

    # Open hand
    lms_open = _create_mock_landmarks(openness_ratio=1.0, pinch_dist=0.7)
    open_metrics = None
    for t in [2.0, 2.033, 2.066, 2.099, 2.133]:
        open_metrics = estimator.compute_metrics(lms_open, 640, 480, timestamp=t)

    assert open_metrics is not None
    assert open_metrics["openness"] > fist_metrics["openness"]
    assert 0.6 <= open_metrics["openness"] <= 1.0


def test_invalid_landmark_count():
    estimator = GestureEstimator()
    with pytest.raises(ValueError, match="Expected 21 landmarks"):
        estimator.compute_metrics([(0.0, 0.0, 0.0)] * 10, 640, 480)
