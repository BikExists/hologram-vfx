"""Decoupled / Asynchronous Hand Tracking Worker.

Provides non-blocking hand tracking by isolating MediaPipe CPU inference onto a
dedicated worker thread with single-slot 'latest-frame-wins' buffer policy.
"""

from dataclasses import dataclass
import threading
import time
from typing import List, Optional, Tuple, Union
import numpy as np

from src.hand_tracker import HandTracker, HandData


@dataclass
class TrackingResult:
    """Snapshot of tracking results produced by HandTracker."""

    hands: List[HandData]
    primary_hand: Optional[HandData]
    timestamp: float          # Time when tracking inference completed
    capture_timestamp: float  # Time when camera frame was captured / submitted
    frame_id: int             # Monotonically increasing submission index
    processing_time_ms: float # Worker inference duration in ms
    is_stale: bool = False    # True if age exceeded max_stale_ms threshold
    is_grace_frame: bool = False


class AsyncHandTracker:
    """Thread-safe, decoupled wrapper around HandTracker.

    Features:
    - Dedicated daemon worker thread for MediaPipe inference.
    - Single-slot 'latest-frame-wins' handoff: never accumulates a FIFO backlog.
    - Safe frame copy on submission: eliminates data races with render pipeline.
    - Age measurement and staleness protection: flags or clears outdated tracking.
    - Complete API parity with synchronous HandTracker.
    - Deterministic synchronous mode toggle (`sync_mode=True`) for tests/benchmarks.
    """

    def __init__(
        self,
        sync_mode: bool = False,
        max_stale_ms: float = 200.0,
        max_num_hands: int = 2,
        min_detection_confidence: float = 0.6,
        min_tracking_confidence: float = 0.6,
        grace_period_frames: int = 4,
        pinch_grab_thresh: float = 0.38,
        pinch_release_thresh: float = 0.52,
        max_tracking_dim: int = 640,
    ):
        self.sync_mode = sync_mode
        self.max_stale_ms = max_stale_ms

        # Underlying synchronous MediaPipe tracker instance
        self._tracker = HandTracker(
            max_num_hands=max_num_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
            grace_period_frames=grace_period_frames,
            pinch_grab_thresh=pinch_grab_thresh,
            pinch_release_thresh=pinch_release_thresh,
            max_tracking_dim=max_tracking_dim,
        )

        # Thread synchronization primitives
        self._lock = threading.Lock()
        self._frame_ready = threading.Event()
        self._shutdown_event = threading.Event()

        # Slot state (protected by _lock)
        self._pending_frame: Optional[np.ndarray] = None
        self._pending_timestamp: float = 0.0
        self._pending_frame_id: int = 0
        self._has_pending: bool = False

        # Telemetry & performance metrics (protected by _lock or atomic)
        self._dropped_frames: int = 0
        self._total_submitted: int = 0
        self._total_processed: int = 0
        self._worker_fps: float = 0.0
        self._worker_fps_history: List[float] = []
        self._worker_proc_time_ms: float = 0.0
        self._last_worker_time: float = 0.0
        self._last_landmark_age_ms: float = 0.0
        self._last_error_log_time: float = 0.0

        # Latest published result
        self._latest_result: TrackingResult = TrackingResult(
            hands=[],
            primary_hand=None,
            timestamp=0.0,
            capture_timestamp=0.0,
            frame_id=0,
            processing_time_ms=0.0,
            is_stale=False,
            is_grace_frame=False,
        )

        # Start worker thread if not in synchronous mode
        self._worker_thread: Optional[threading.Thread] = None
        if not self.sync_mode:
            self._worker_thread = threading.Thread(
                target=self._worker_loop,
                daemon=True,
                name="HandTrackingWorker",
            )
            self._worker_thread.start()

    # -------------------------------------------------------------------------
    # Public Asynchronous Lifecycle & Pipeline Methods
    # -------------------------------------------------------------------------

    def submit_frame(
        self,
        frame_bgr: np.ndarray,
        timestamp: Optional[float] = None,
    ) -> None:
        """Submit a camera frame for tracking.

        In async mode: makes a thread-safe copy and places it into the single-slot buffer.
        If the worker is still busy with an earlier frame, the previous pending frame is
        overwritten ('latest-frame-wins') and dropped_frames is incremented.
        In sync mode: executes MediaPipe immediately on the calling thread.
        """
        now = time.perf_counter() if timestamp is None else timestamp

        if self.sync_mode:
            self._process_sync(frame_bgr, now)
            return

        # Safe frame copy: guarantees the render loop can mutate its frame buffer
        # without data races or torn frames in the tracking worker thread.
        frame_copy = frame_bgr.copy()

        with self._lock:
            self._total_submitted += 1
            if self._has_pending:
                self._dropped_frames += 1
            self._pending_frame = frame_copy
            self._pending_timestamp = now
            self._pending_frame_id += 1
            self._has_pending = True
            self._frame_ready.set()

    def get_latest_result(
        self,
        max_stale_ms: Optional[float] = None,
    ) -> TrackingResult:
        """Query the latest available tracking result without blocking.

        Checks landmark age against `max_stale_ms`. If the age exceeds the threshold,
        the result is flagged as stale to avoid frozen ghost tracking.
        """
        now = time.perf_counter()
        stale_threshold = self.max_stale_ms if max_stale_ms is None else max_stale_ms

        with self._lock:
            result = self._latest_result

        # Calculate result age from camera capture time to present consumption time
        if result.capture_timestamp > 0.0:
            age_ms = (now - result.capture_timestamp) * 1000.0
        else:
            age_ms = 0.0

        self._last_landmark_age_ms = age_ms

        # Staleness protection: if tracking has ceased or hung, flag and decay hands
        if age_ms > stale_threshold and result.hands and not result.is_stale:
            stale_result = TrackingResult(
                hands=[],
                primary_hand=None,
                timestamp=result.timestamp,
                capture_timestamp=result.capture_timestamp,
                frame_id=result.frame_id,
                processing_time_ms=result.processing_time_ms,
                is_stale=True,
                is_grace_frame=False,
            )
            with self._lock:
                self._latest_result = stale_result
            return stale_result

        return result

    # -------------------------------------------------------------------------
    # Backward-Compatible HandTracker API Facade
    # -------------------------------------------------------------------------

    def process_frame_multi(
        self,
        frame_bgr: np.ndarray,
        timestamp: Optional[float] = None,
    ) -> List[HandData]:
        """Backward-compatible entry point for multi-hand tracking.

        In sync mode: executes synchronously and returns detected hands.
        In async mode: submits the frame and immediately returns the latest available hands.
        """
        now = time.perf_counter() if timestamp is None else timestamp
        if self.sync_mode:
            self._process_sync(frame_bgr, now)
            return self._latest_result.hands

        self.submit_frame(frame_bgr, timestamp=now)
        return self.get_latest_result().hands

    def process_frame(
        self,
        frame_bgr: np.ndarray,
        timestamp: Optional[float] = None,
    ) -> Optional[HandData]:
        """Backward-compatible entry point returning primary hand."""
        hands = self.process_frame_multi(frame_bgr, timestamp=timestamp)
        if not hands:
            return None
        return self.last_valid_hand or hands[0]

    def draw_holographic_landmarks(
        self,
        frame: np.ndarray,
        hand_data: Union[HandData, List[HandData]],
        color_bgr: Tuple[int, int, int] = (255, 230, 0),
    ) -> None:
        """Draw sci-fi holographic skeleton and joints onto the target frame."""
        self._tracker.draw_holographic_landmarks(frame, hand_data, color_bgr)

    def reset(self) -> None:
        """Reset tracking state, estimators, and pending buffer slots."""
        with self._lock:
            self._pending_frame = None
            self._has_pending = False
            self._frame_ready.clear()
            self._latest_result = TrackingResult(
                hands=[],
                primary_hand=None,
                timestamp=0.0,
                capture_timestamp=0.0,
                frame_id=0,
                processing_time_ms=0.0,
                is_stale=False,
                is_grace_frame=False,
            )
            self._tracker.reset()

    def close(self) -> None:
        """Clean shutdown releasing worker thread and MediaPipe resources."""
        self._shutdown_event.set()
        self._frame_ready.set()
        if self._worker_thread is not None and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1.0)
            self._worker_thread = None
        self._tracker.close()

    # -------------------------------------------------------------------------
    # Properties & Telemetry Accessors
    # -------------------------------------------------------------------------

    @property
    def last_valid_hand(self) -> Optional[HandData]:
        """Most recent valid primary hand."""
        with self._lock:
            return self._latest_result.primary_hand

    @last_valid_hand.setter
    def last_valid_hand(self, hand: Optional[HandData]) -> None:
        """Allow setting last_valid_hand for testing and state injection."""
        with self._lock:
            hands = [hand] if hand is not None else []
            self._latest_result = TrackingResult(
                hands=hands,
                primary_hand=hand,
                timestamp=time.perf_counter(),
                capture_timestamp=time.perf_counter(),
                frame_id=self._latest_result.frame_id,
                processing_time_ms=self._latest_result.processing_time_ms,
                is_stale=False,
                is_grace_frame=hand.is_grace_frame if hand is not None else False,
            )
            self._tracker.last_valid_hand = hand
            self._tracker.last_valid_hands = hands
            self._tracker.detected_hands = hands

    @property
    def last_valid_hands(self) -> List[HandData]:
        """Most recent valid hand list."""
        with self._lock:
            return self._latest_result.hands

    @last_valid_hands.setter
    def last_valid_hands(self, hands: List[HandData]) -> None:
        """Allow setting last_valid_hands for testing and state injection."""
        with self._lock:
            primary = hands[0] if hands else None
            self._latest_result = TrackingResult(
                hands=hands,
                primary_hand=primary,
                timestamp=time.perf_counter(),
                capture_timestamp=time.perf_counter(),
                frame_id=self._latest_result.frame_id,
                processing_time_ms=self._latest_result.processing_time_ms,
                is_stale=False,
                is_grace_frame=any(h.is_grace_frame for h in hands) if hands else False,
            )
            self._tracker.last_valid_hand = primary
            self._tracker.last_valid_hands = hands
            self._tracker.detected_hands = hands

    @property
    def detected_hands(self) -> List[HandData]:
        """Hands detected in the most recent completed inference."""
        with self._lock:
            return self._latest_result.hands

    @detected_hands.setter
    def detected_hands(self, hands: List[HandData]) -> None:
        """Allow setting detected_hands for testing and state injection."""
        self.last_valid_hands = hands

    @property
    def tracking_fps(self) -> float:
        """Estimated tracking worker updates per second."""
        with self._lock:
            return self._worker_fps

    @property
    def processing_time_ms(self) -> float:
        """MediaPipe inference duration of the last completed frame."""
        with self._lock:
            return self._worker_proc_time_ms

    @property
    def dropped_frames_count(self) -> int:
        """Count of frames superseded in the slot before worker could process them."""
        with self._lock:
            return self._dropped_frames

    @property
    def total_submitted_frames(self) -> int:
        """Total number of frames submitted to tracker."""
        with self._lock:
            return self._total_submitted

    @property
    def total_processed_frames(self) -> int:
        """Total number of frames processed by tracking worker."""
        with self._lock:
            return self._total_processed

    @property
    def last_landmark_age_ms(self) -> float:
        """Measured age in milliseconds of the landmark data currently in use."""
        return self._last_landmark_age_ms

    @property
    def lost_frames_count(self) -> int:
        """Number of consecutive frames without hand detections."""
        return self._tracker.lost_frames_count

    @property
    def grace_period_frames(self) -> int:
        """Configured grace period frame tolerance."""
        return self._tracker.grace_period_frames

    # -------------------------------------------------------------------------
    # Internal Worker Implementation
    # -------------------------------------------------------------------------

    def _process_sync(self, frame_bgr: np.ndarray, timestamp: float) -> None:
        """Synchronous execution path for tests and benchmark baseline."""
        t_start = time.perf_counter()
        try:
            hands = self._tracker.process_frame_multi(frame_bgr, timestamp=timestamp)
            primary_hand = self._tracker.last_valid_hand
        except Exception as e:
            now_err = time.perf_counter()
            if now_err - self._last_error_log_time > 2.0:
                import sys
                print(f"[Warning] Hand tracking error (sync): {e}", file=sys.stderr)
                self._last_error_log_time = now_err
            hands = []
            primary_hand = None
        t_end = time.perf_counter()
        proc_ms = (t_end - t_start) * 1000.0

        with self._lock:
            self._total_submitted += 1
            self._total_processed += 1
            self._worker_proc_time_ms = proc_ms
            if self._last_worker_time > 0.0:
                dt = t_end - self._last_worker_time
                if dt > 0.001:
                    inst_fps = 1.0 / dt
                    self._worker_fps_history.append(inst_fps)
                    if len(self._worker_fps_history) > 15:
                        self._worker_fps_history.pop(0)
                    self._worker_fps = sum(self._worker_fps_history) / len(self._worker_fps_history)
            self._last_worker_time = t_end

            self._latest_result = TrackingResult(
                hands=hands,
                primary_hand=primary_hand,
                timestamp=t_end,
                capture_timestamp=timestamp,
                frame_id=self._total_submitted,
                processing_time_ms=proc_ms,
                is_stale=False,
                is_grace_frame=any(h.is_grace_frame for h in hands) if hands else False,
            )

    def _worker_loop(self) -> None:
        """Background thread executing MediaPipe processing."""
        while not self._shutdown_event.is_set():
            # Wait for a frame submission or shutdown signal
            if not self._frame_ready.wait(timeout=0.05):
                continue
            if self._shutdown_event.is_set():
                break

            # Grab pending frame under lock (sub-microsecond duration)
            with self._lock:
                if not self._has_pending:
                    self._frame_ready.clear()
                    continue
                frame = self._pending_frame
                cap_ts = self._pending_timestamp
                frame_id = self._pending_frame_id
                self._pending_frame = None
                self._has_pending = False
                self._frame_ready.clear()

            if frame is None:
                continue

            # Run MediaPipe CPU inference outside lock with fault tolerance
            t_start = time.perf_counter()
            try:
                hands = self._tracker.process_frame_multi(frame, timestamp=cap_ts)
                primary_hand = self._tracker.last_valid_hand
            except Exception as e:
                now_err = time.perf_counter()
                if now_err - self._last_error_log_time > 2.0:
                    import sys
                    print(f"[Warning] Hand tracking worker error: {e}", file=sys.stderr)
                    self._last_error_log_time = now_err
                hands = []
                primary_hand = None
            t_end = time.perf_counter()
            proc_ms = (t_end - t_start) * 1000.0

            # Atomically publish new tracking result under lock
            with self._lock:
                self._total_processed += 1
                self._worker_proc_time_ms = proc_ms

                if self._last_worker_time > 0.0:
                    dt = t_end - self._last_worker_time
                    if dt > 0.001:
                        inst_fps = 1.0 / dt
                        self._worker_fps_history.append(inst_fps)
                        if len(self._worker_fps_history) > 15:
                            self._worker_fps_history.pop(0)
                        self._worker_fps = sum(self._worker_fps_history) / len(self._worker_fps_history)
                self._last_worker_time = t_end

                self._latest_result = TrackingResult(
                    hands=hands,
                    primary_hand=primary_hand,
                    timestamp=t_end,
                    capture_timestamp=cap_ts,
                    frame_id=frame_id,
                    processing_time_ms=proc_ms,
                    is_stale=False,
                    is_grace_frame=any(h.is_grace_frame for h in hands) if hands else False,
                )
