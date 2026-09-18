"""MediaPipe Hand Tracking and Gesture Integration.

Encapsulates hand detection, landmark extraction, multi-hand arbitration,
lost-tracking grace period, and visual landmark rendering.
"""

from dataclasses import dataclass
import time
from typing import Dict, List, Optional, Tuple, Union
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
        self.last_valid_hands: List[HandData] = []
        self.detected_hands: List[HandData] = []

        # Independent gesture estimators per hand to eliminate filter crosstalk
        self.estimators: Dict[str, GestureEstimator] = {
            "Right": GestureEstimator(
                pinch_grab_thresh=pinch_grab_thresh,
                pinch_release_thresh=pinch_release_thresh,
            ),
            "Left": GestureEstimator(
                pinch_grab_thresh=pinch_grab_thresh,
                pinch_release_thresh=pinch_release_thresh,
            ),
        }
        # Fallback/backward compatibility estimator reference
        self.estimator = self.estimators["Right"]

    def reset(self) -> None:
        """Reset tracker state and filters."""
        for est in self.estimators.values():
            est.reset()
        self.lost_frames_count = 0
        self.last_valid_hand = None
        self.last_valid_hands = []
        self.detected_hands = []

    def close(self) -> None:
        """Release MediaPipe resources."""
        if hasattr(self, "hands") and self.hands is not None:
            self.hands.close()

    def process_frame_multi(
        self,
        frame_bgr: np.ndarray,
        timestamp: Optional[float] = None,
    ) -> List[HandData]:
        """Detect hands in frame and return a list of all detected HandData objects."""
        now = time.perf_counter() if timestamp is None else timestamp
        h, w = frame_bgr.shape[:2]

        # Convert to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        rgb_frame.flags.writeable = False
        results = self.hands.process(rgb_frame)

        if results.multi_hand_landmarks and results.multi_handedness:
            self.lost_frames_count = 0
            hands_list: List[HandData] = []

            for i, hand_lms in enumerate(results.multi_hand_landmarks):
                classification = results.multi_handedness[i].classification[0]
                handedness_label = classification.label
                confidence = float(classification.score)

                estimator = self.estimators.get(handedness_label, self.estimator)

                norm_lms = [(lm.x, lm.y, lm.z) for lm in hand_lms.landmark]
                px_lms = [(lm[0] * w, lm[1] * h) for lm in norm_lms]

                metrics = estimator.compute_metrics(
                    norm_lms,
                    frame_width=w,
                    frame_height=h,
                    timestamp=now,
                )

                hdata = HandData(
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
                    confidence=confidence,
                    is_grace_frame=False,
                )
                hands_list.append(hdata)

            # Determine primary hand (prefer pinching hand, then largest hand)
            primary_hand = None
            pinching_hands = [hd for hd in hands_list if hd.is_pinching]
            if pinching_hands:
                primary_hand = pinching_hands[0]
            elif hands_list:
                primary_hand = max(hands_list, key=lambda hd: hd.hand_scale_px)

            self.detected_hands = hands_list
            self.last_valid_hands = hands_list
            self.last_valid_hand = primary_hand
            return hands_list

        # Hand not detected in this frame: check grace period
        self.lost_frames_count += 1
        if self.lost_frames_count <= self.grace_period_frames and self.last_valid_hands:
            grace_hands = []
            for prev_hand in self.last_valid_hands:
                grace_hands.append(
                    HandData(
                        landmarks_norm=prev_hand.landmarks_norm,
                        landmarks_px=prev_hand.landmarks_px,
                        palm_center_px=prev_hand.palm_center_px,
                        pinch_point_px=prev_hand.pinch_point_px,
                        is_pinching=prev_hand.is_pinching,
                        pinch_distance_px=prev_hand.pinch_distance_px,
                        norm_pinch_distance=prev_hand.norm_pinch_distance,
                        openness=prev_hand.openness,
                        hand_scale_px=prev_hand.hand_scale_px,
                        handedness=prev_hand.handedness,
                        confidence=max(0.1, prev_hand.confidence * 0.8),
                        is_grace_frame=True,
                    )
                )
            self.detected_hands = grace_hands
            if self.last_valid_hand is not None:
                self.last_valid_hand = grace_hands[0]
            return grace_hands

        # Beyond grace period: hands completely lost
        if self.lost_frames_count > self.grace_period_frames:
            for est in self.estimators.values():
                est.reset()
            self.last_valid_hand = None
            self.last_valid_hands = []
            self.detected_hands = []

        return []

    def process_frame(
        self,
        frame_bgr: np.ndarray,
        timestamp: Optional[float] = None,
    ) -> Optional[HandData]:
        """Detect hands in frame and return primary HandData or None if not found (backward-compatible)."""
        hands = self.process_frame_multi(frame_bgr, timestamp=timestamp)
        if not hands:
            return None
        return self.last_valid_hand or hands[0]

    def draw_holographic_landmarks(
        self,
        frame: np.ndarray,
        hand_data: Union[HandData, List[HandData]],
        color_bgr: Tuple[int, int, int] = (255, 230, 0),  # Cyan
    ) -> None:
        """Draws subtle sci-fi holographic skeleton and joints onto the frame for one or multiple hands."""
        if not hand_data:
            return

        hands_to_draw = hand_data if isinstance(hand_data, list) else [hand_data]
        valid_hands = [h for h in hands_to_draw if h and h.landmarks_px]
        if not valid_hands:
            return

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

        overlay = frame.copy()
        for hand in valid_hands:
            pts = hand.landmarks_px

            # Draw semi-transparent holographic skeleton lines
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
            if hand.is_pinching:
                pinch_pt = (int(hand.pinch_point_px[0]), int(hand.pinch_point_px[1]))
                cv2.circle(overlay, pinch_pt, 7, (255, 255, 255), 2, cv2.LINE_AA)
                cv2.circle(overlay, pinch_pt, 3, color_bgr, -1, cv2.LINE_AA)

        # Alpha blend onto frame
        cv2.addWeighted(overlay, 0.45, frame, 0.55, 0, frame)

