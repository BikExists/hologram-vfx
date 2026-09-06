"""MediaPipe Hand Tracking and Gesture Integration.

Encapsulates hand detection, landmark extraction, multi-hand arbitration,
lost-tracking grace period, and visual landmark rendering.
"""

from dataclasses import dataclass
import time
from typing import List, Optional, Tuple
import cv2
import mediapipe as mp
import numpy as np

from src.gestures import GestureEstimator


@dataclass
class HandData:
    """Processed hand information for a single frame."""

    landmarks_norm: List[Tuple[float, float, float]]
    landmarks_px: List[Tuple[float, float]]
    palm_center_px: Tuple[float, float]
    pinch_point_px: Tuple[float, float]
    is_pinching: bool
    pinch_distance_px: float
    norm_pinch_distance: float
    openness: float
    hand_scale_px: float
    handedness: str  # 'Right' or 'Left'
    confidence: float
    is_grace_frame: bool = False


class HandTracker:
    """Real-time hand tracking powered by MediaPipe Hands."""

    def __init__(
        self,
        max_num_hands: int = 2,
        min_detection_confidence: float = 0.6,
        min_tracking_confidence: float = 0.6,
        grace_period_frames: int = 4,
        pinch_grab_thresh: float = 0.38,
        pinch_release_thresh: float = 0.52,
    ):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_num_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self.grace_period_frames = grace_period_frames
        self.lost_frames_count = 0
        self.last_valid_hand: Optional[HandData] = None

        self.estimator = GestureEstimator(
            pinch_grab_thresh=pinch_grab_thresh,
            pinch_release_thresh=pinch_release_thresh,
        )

    def reset(self) -> None:
        """Reset tracker state and filters."""
        self.estimator.reset()
        self.lost_frames_count = 0
        self.last_valid_hand = None

    def close(self) -> None:
        """Release MediaPipe resources."""
        if hasattr(self, "hands") and self.hands is not None:
            self.hands.close()

    def process_frame(
        self,
        frame_bgr: np.ndarray,
        timestamp: Optional[float] = None,
    ) -> Optional[HandData]:
        """Detect hands in frame and return primary HandData or None if not found."""
        now = time.perf_counter() if timestamp is None else timestamp
        h, w = frame_bgr.shape[:2]

        # Convert to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        rgb_frame.flags.writeable = False
        results = self.hands.process(rgb_frame)

        if results.multi_hand_landmarks and results.multi_handedness:
            self.lost_frames_count = 0

            # Select primary hand (prefer pinching hand or largest hand)
            best_idx = 0
            if len(results.multi_hand_landmarks) > 1:
                # Score based on hand size (bounding box area)
                max_area = -1.0
                for i, hand_lms in enumerate(results.multi_hand_landmarks):
                    xs = [lm.x for lm in hand_lms.landmark]
                    ys = [lm.y for lm in hand_lms.landmark]
                    area = (max(xs) - min(xs)) * (max(ys) - min(ys))
                    if area > max_area:
                        max_area = area
                        best_idx = i

            selected_landmarks = results.multi_hand_landmarks[best_idx]
            handedness_label = results.multi_handedness[best_idx].classification[0].label
            confidence = results.multi_handedness[best_idx].classification[0].score

            # Extract normalized landmarks
            norm_lms = [(lm.x, lm.y, lm.z) for lm in selected_landmarks.landmark]
            px_lms = [(lm[0] * w, lm[1] * h) for lm in norm_lms]

            # Compute gesture metrics
            metrics = self.estimator.compute_metrics(
                norm_lms,
                frame_width=w,
                frame_height=h,
                timestamp=now,
            )

            hand_data = HandData(
                landmarks_norm=norm_lms,
                landmarks_px=px_lms,
                palm_center_px=metrics["palm_center_px"],
                pinch_point_px=metrics["pinch_point_px"],
                is_pinching=metrics["is_pinching"],
                pinch_distance_px=metrics["pinch_distance_px"],
                norm_pinch_distance=metrics["norm_pinch_distance"],
                openness=metrics["openness"],
                hand_scale_px=metrics["hand_scale_px"],
                handedness=handedness_label,
                confidence=float(confidence),
                is_grace_frame=False,
            )

            self.last_valid_hand = hand_data
            return hand_data

        # Hand not detected in this frame: check grace period
        self.lost_frames_count += 1
        if self.lost_frames_count <= self.grace_period_frames and self.last_valid_hand is not None:
            # Return last valid hand marked as grace frame
            grace_hand = HandData(
                landmarks_norm=self.last_valid_hand.landmarks_norm,
                landmarks_px=self.last_valid_hand.landmarks_px,
                palm_center_px=self.last_valid_hand.palm_center_px,
                pinch_point_px=self.last_valid_hand.pinch_point_px,
                is_pinching=self.last_valid_hand.is_pinching,
                pinch_distance_px=self.last_valid_hand.pinch_distance_px,
                norm_pinch_distance=self.last_valid_hand.norm_pinch_distance,
                openness=self.last_valid_hand.openness,
                hand_scale_px=self.last_valid_hand.hand_scale_px,
                handedness=self.last_valid_hand.handedness,
                confidence=max(0.1, self.last_valid_hand.confidence * 0.8),
                is_grace_frame=True,
            )
            return grace_hand

        # Beyond grace period: hand completely lost
        if self.lost_frames_count > self.grace_period_frames:
            self.estimator.reset()
            self.last_valid_hand = None

        return None

    def draw_holographic_landmarks(
        self,
        frame: np.ndarray,
        hand_data: HandData,
        color_bgr: Tuple[int, int, int] = (255, 230, 0),  # Cyan
    ) -> None:
        """Draws subtle sci-fi holographic skeleton and joints onto the frame."""
        if not hand_data or not hand_data.landmarks_px:
            return

        pts = hand_data.landmarks_px
        h, w = frame.shape[:2]

        # Standard connections
        connections = [
            # Thumb
            (0, 1), (1, 2), (2, 3), (3, 4),
            # Index
            (0, 5), (5, 6), (6, 7), (7, 8),
            # Middle
            (0, 9), (9, 10), (10, 11), (11, 12),
            # Ring
            (0, 13), (13, 14), (14, 15), (15, 16),
            # Pinky
            (0, 17), (17, 18), (18, 19), (19, 20),
            # Palm base
            (5, 9), (9, 13), (13, 17),
        ]

        # Draw semi-transparent holographic skeleton lines
        overlay = frame.copy()
        for p1_idx, p2_idx in connections:
            pt1 = (int(pts[p1_idx][0]), int(pts[p1_idx][1]))
            pt2 = (int(pts[p2_idx][0]), int(pts[p2_idx][1]))
            cv2.line(overlay, pt1, pt2, color_bgr, 1, cv2.LINE_AA)

        # Draw joint nodes
        for idx, pt in enumerate(pts):
            center = (int(pt[0]), int(pt[1]))
            is_tip = idx in (4, 8, 12, 16, 20)
            radius = 3 if is_tip else 2
            node_color = (255, 255, 255) if is_tip else color_bgr
            cv2.circle(overlay, center, radius, node_color, -1, cv2.LINE_AA)

        # Highlight pinch point if pinching
        if hand_data.is_pinching:
            pinch_pt = (int(hand_data.pinch_point_px[0]), int(hand_data.pinch_point_px[1]))
            cv2.circle(overlay, pinch_pt, 7, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.circle(overlay, pinch_pt, 3, color_bgr, -1, cv2.LINE_AA)

        # Alpha blend onto frame
        cv2.addWeighted(overlay, 0.45, frame, 0.55, 0, frame)
