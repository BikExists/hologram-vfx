"""Gesture detection and estimation algorithms.

Calculates scale-invariant pinch detection with hysteresis,
hand openness metric [0.0, 1.0], and palm centroid with smoothing.
"""

import math
from typing import Dict, List, Optional, Tuple
import numpy as np
from src.filters import EMAFilter, OneEuroFilter, PointFilter


class GestureEstimator:
    """Estimates pinch state, hand openness, and spatial anchors from landmarks."""

    # Default hysteresis thresholds (scale-normalized)
    DEFAULT_PINCH_GRAB = 0.38
    DEFAULT_PINCH_RELEASE = 0.52

    # Openness calibration boundaries (scale-normalized average extension)
    RAW_OPEN_MIN = 0.80  # Closed fist
    RAW_OPEN_MAX = 1.95  # Wide open hand

    def __init__(
        self,
        pinch_grab_thresh: float = DEFAULT_PINCH_GRAB,
        pinch_release_thresh: float = DEFAULT_PINCH_RELEASE,
        openness_filter_cutoff: float = 1.2,
        openness_filter_beta: float = 0.02,
    ):
        self.pinch_grab_thresh = float(pinch_grab_thresh)
        self.pinch_release_thresh = float(pinch_release_thresh)

        # Internal state
        self._is_pinching: bool = False
        self._palm_filter = PointFilter(mincutoff=1.5, beta=0.03)
        self._pinch_filter = PointFilter(mincutoff=1.5, beta=0.03)
        self._openness_filter = OneEuroFilter(
            mincutoff=openness_filter_cutoff,
            beta=openness_filter_beta,
        )
        self._norm_pinch_filter = OneEuroFilter(mincutoff=4.0, beta=0.1)

    def reset(self) -> None:
        """Reset internal filter states and gestures."""
        self._is_pinching = False
        self._palm_filter.reset()
        self._pinch_filter.reset()
        self._openness_filter.reset()
        self._norm_pinch_filter.reset()

    @staticmethod
    def calculate_distance_2d(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """Euclidean distance in 2D."""
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

    @staticmethod
    def calculate_distance_3d(p1: Tuple[float, float, float], p2: Tuple[float, float, float]) -> float:
        """Euclidean distance in 3D."""
        return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2 + (p1[2] - p2[2]) ** 2)

    def compute_metrics(
        self,
        landmarks: List[Tuple[float, float, float]],
        frame_width: int,
        frame_height: int,
        timestamp: Optional[float] = None,
    ) -> Dict:
        """Processes 21 MediaPipe hand landmarks and extracts gesture metrics.

        Parameters
        ----------
        landmarks : List of (x, y, z) in normalized [0, 1] coordinates.
        frame_width : int, width of video frame in pixels.
        frame_height : int, height of video frame in pixels.
        timestamp : Optional float timestamp.

        Returns
        -------
        Dict with keys:
            palm_center_px: (x, y) in pixels (filtered)
            pinch_point_px: (x, y) in pixels (filtered)
            is_pinching: bool (hysteresis-stabilized)
            pinch_distance_px: float
            norm_pinch_distance: float
            openness: float in [0.0, 1.0] (filtered)
            raw_openness: float
            hand_scale_px: float
        """
        if len(landmarks) < 21:
            raise ValueError(f"Expected 21 landmarks, got {len(landmarks)}")

        # Convert landmarks to pixel space for screen operations
        pts_px = [
            (lm[0] * frame_width, lm[1] * frame_height, lm[2] * frame_width)
            for lm in landmarks
        ]

        # Landmark indices (MediaPipe Hand model)
        # 0: Wrist
        # 4: Thumb tip, 2: Thumb MCP, 3: Thumb IP
        # 5: Index MCP, 6: Index PIP, 8: Index tip
        # 9: Middle MCP, 10: Middle PIP, 12: Middle tip
        # 13: Ring MCP, 14: Ring PIP, 16: Ring tip
        # 17: Pinky MCP, 18: Pinky PIP, 20: Pinky tip
        wrist = pts_px[0]
        thumb_tip = pts_px[4]
        index_mcp = pts_px[5]
        index_tip = pts_px[8]
        middle_mcp = pts_px[9]
        middle_tip = pts_px[12]
        ring_mcp = pts_px[13]
        ring_tip = pts_px[16]
        pinky_mcp = pts_px[17]
        pinky_tip = pts_px[20]

        # Structural hand scale: Wrist (0) to Middle MCP (9) is rigid
        hand_scale_px = max(10.0, self.calculate_distance_2d(wrist[:2], middle_mcp[:2]))

        # Palm center: weighted average of palm joints (Wrist, Index MCP, Middle MCP, Pinky MCP)
        raw_palm_x = (wrist[0] * 0.25 + index_mcp[0] * 0.25 + middle_mcp[0] * 0.25 + pinky_mcp[0] * 0.25)
        raw_palm_y = (wrist[1] * 0.25 + index_mcp[1] * 0.25 + middle_mcp[1] * 0.25 + pinky_mcp[1] * 0.25)
        filtered_palm = self._palm_filter.filter_pt((raw_palm_x, raw_palm_y), timestamp=timestamp)

        # Raw pinch point: midpoint between thumb tip and index tip
        raw_pinch_x = (thumb_tip[0] + index_tip[0]) * 0.5
        raw_pinch_y = (thumb_tip[1] + index_tip[1]) * 0.5
        filtered_pinch = self._pinch_filter.filter_pt((raw_pinch_x, raw_pinch_y), timestamp=timestamp)

        # Pinch distance: 3D distance between thumb tip and index tip
        raw_pinch_dist_px = self.calculate_distance_3d(thumb_tip, index_tip)
        norm_pinch_dist = raw_pinch_dist_px / hand_scale_px
        filtered_norm_pinch = float(
            self._norm_pinch_filter.filter(norm_pinch_dist, timestamp=timestamp)
        )

        # Pinch Hysteresis State Machine
        if not self._is_pinching:
            if filtered_norm_pinch < self.pinch_grab_thresh:
                self._is_pinching = True
        else:
            if filtered_norm_pinch > self.pinch_release_thresh:
                self._is_pinching = False

        # Openness Calculation:
        # Distance from wrist to each fingertip, normalized by hand scale
        finger_tips = [thumb_tip, index_tip, middle_tip, ring_tip, pinky_tip]
        tip_dists = [self.calculate_distance_2d(wrist[:2], tip[:2]) for tip in finger_tips]
        avg_tip_dist = sum(tip_dists) / len(tip_dists)
        raw_openness = avg_tip_dist / hand_scale_px

        # Normalized openness mapped to [0.0, 1.0] with smooth Hermite S-curve
        norm_val = (raw_openness - self.RAW_OPEN_MIN) / (self.RAW_OPEN_MAX - self.RAW_OPEN_MIN)
        clamped_val = max(0.0, min(1.0, norm_val))
        # Hermite smoothstep for organic feel: 3x^2 - 2x^3
        smooth_val = clamped_val * clamped_val * (3.0 - 2.0 * clamped_val)

        filtered_openness = float(
            self._openness_filter.filter(smooth_val, timestamp=timestamp)
        )
        filtered_openness = max(0.0, min(1.0, filtered_openness))

        return {
            "palm_center_px": (float(filtered_palm[0]), float(filtered_palm[1])),
            "pinch_point_px": (float(filtered_pinch[0]), float(filtered_pinch[1])),
            "is_pinching": self._is_pinching,
            "pinch_distance_px": float(raw_pinch_dist_px),
            "norm_pinch_distance": float(filtered_norm_pinch),
            "openness": float(filtered_openness),
            "raw_openness": float(raw_openness),
            "hand_scale_px": float(hand_scale_px),
        }
