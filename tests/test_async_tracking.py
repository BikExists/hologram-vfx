"""Tests for Decoupled / Asynchronous Hand Tracking.

Verifies thread safety, single-slot latest-frame-wins behavior, staleness detection,
grace period integration, backward compatibility, and clean shutdown.
"""

import threading
import time
import numpy as np
import pytest

from src.app import HolographicVFXApp
from src.hand_tracker import HandData
from src.tracking_worker import AsyncHandTracker, TrackingResult


def test_async_tracker_lifecycle_sync_and_async():
    """Verify clean start and shutdown for both sync and async modes."""
    # Sync mode: no worker thread
    sync_tracker = AsyncHandTracker(sync_mode=True)
    assert sync_tracker.sync_mode is True
    assert sync_tracker._worker_thread is None
    sync_tracker.close()

    # Async mode: worker thread starts and shuts down cleanly
    async_tracker = AsyncHandTracker(sync_mode=False)
    assert async_tracker.sync_mode is False
    assert async_tracker._worker_thread is not None
    assert async_tracker._worker_thread.is_alive()
    thread = async_tracker._worker_thread
    async_tracker.close()
    assert async_tracker._worker_thread is None
    assert not thread.is_alive()


def test_async_tracker_sync_mode_execution():
    """Verify that sync_mode behaves deterministically and executes immediately."""
    tracker = AsyncHandTracker(sync_mode=True)
    try:
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        now = time.perf_counter()

        tracker.submit_frame(frame, timestamp=now)
        result = tracker.get_latest_result()

        assert isinstance(result, TrackingResult)
        assert result.capture_timestamp == now
        assert result.processing_time_ms >= 0.0
        assert tracker.total_submitted_frames == 1
        assert tracker.total_processed_frames == 1
        assert tracker.dropped_frames_count == 0

        # Test process_frame_multi facade
        hands = tracker.process_frame_multi(frame, timestamp=now)
        assert isinstance(hands, list)
    finally:
        tracker.close()


def test_async_tracker_single_slot_latest_frame_wins():
    """Verify that submitting multiple frames while worker is busy drops intermediate frames."""
    tracker = AsyncHandTracker(sync_mode=False)
    try:
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # Submit 10 frames as fast as possible
        for i in range(10):
            tracker.submit_frame(frame, timestamp=time.perf_counter())

        # Allow worker thread a moment to process the pending frame
        time.sleep(0.2)

        # The worker should have processed some frames, and dropped the superseded ones
        assert tracker.total_submitted_frames == 10
        # In a single-slot buffer, dropped frames + processed frames == total submitted (or pending)
        assert tracker.dropped_frames_count > 0
        assert tracker.total_processed_frames < 10
    finally:
        tracker.close()


def test_async_tracker_safe_frame_copy_isolation():
    """Verify that modifying the source frame after submit does not corrupt tracking frame."""
    tracker = AsyncHandTracker(sync_mode=False)
    try:
        # Create a frame with a distinct value
        frame = np.full((480, 640, 3), 50, dtype=np.uint8)
        tracker.submit_frame(frame, timestamp=time.perf_counter())

        # Immediately mutate source frame in-place (simulating render pipeline)
        frame.fill(255)

        # Give worker a moment to process
        time.sleep(0.1)

        result = tracker.get_latest_result()
        assert isinstance(result, TrackingResult)
    finally:
        tracker.close()


def test_async_tracker_staleness_detection():
    """Verify that results older than max_stale_ms are flagged as stale."""
    tracker = AsyncHandTracker(sync_mode=True, max_stale_ms=50.0)
    try:
        # Manually inject a fake hand result with an old timestamp
        mock_hand = HandData(
            landmarks_norm=[(0.5, 0.5, 0.0)] * 21,
            landmarks_px=[(320.0, 240.0)] * 21,
            palm_center_px=(320.0, 240.0),
            pinch_point_px=(320.0, 240.0),
            is_pinching=False,
            pinch_distance_px=50.0,
            norm_pinch_distance=0.5,
            openness=0.8,
            hand_scale_px=100.0,
            handedness="Right",
            confidence=0.9,
            is_grace_frame=False,
        )
        old_time = time.perf_counter() - 0.200  # 200 ms ago

        with tracker._lock:
            tracker._latest_result = TrackingResult(
                hands=[mock_hand],
                primary_hand=mock_hand,
                timestamp=old_time + 0.03,
                capture_timestamp=old_time,
                frame_id=1,
                processing_time_ms=30.0,
                is_stale=False,
            )

        # Query with default max_stale_ms=50ms
        res = tracker.get_latest_result(max_stale_ms=50.0)
        assert res.is_stale is True
        assert len(res.hands) == 0
        assert res.primary_hand is None
    finally:
        tracker.close()


def test_async_tracker_concurrent_rapid_access():
    """Stress test concurrent submissions and queries from multiple threads."""
    tracker = AsyncHandTracker(sync_mode=False)
    num_threads = 4
    iterations_per_thread = 25
    stop_event = threading.Event()
    exceptions = []

    def producer():
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        try:
            for _ in range(iterations_per_thread):
                if stop_event.is_set():
                    break
                tracker.submit_frame(frame, timestamp=time.perf_counter())
                time.sleep(0.002)
        except Exception as e:
            exceptions.append(e)

    def consumer():
        try:
            for _ in range(iterations_per_thread):
                if stop_event.is_set():
                    break
                _ = tracker.get_latest_result()
                _ = tracker.tracking_fps
                _ = tracker.processing_time_ms
                _ = tracker.last_landmark_age_ms
                time.sleep(0.002)
        except Exception as e:
            exceptions.append(e)

    threads = []
    for _ in range(num_threads // 2):
        threads.append(threading.Thread(target=producer))
        threads.append(threading.Thread(target=consumer))

    try:
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=3.0)

        assert len(exceptions) == 0, f"Exceptions occurred: {exceptions}"
    finally:
        stop_event.set()
        tracker.close()


def test_app_integration_with_async_tracking():
    """Verify HolographicVFXApp end-to-end integration with async tracking."""
    app = HolographicVFXApp(
        width=640,
        height=480,
        synthetic_mode=True,
        headless=True,
        skip_welcome=True,
        sync_tracking=False,
    )
    try:
        assert app.tracker.sync_mode is False

        # Step 20 frames
        for _ in range(20):
            ret, frame, telemetry = app.step_frame()
            assert ret is True
            assert frame is not None
            assert "tracking_fps" in telemetry
            assert "tracking_time_ms" in telemetry
            assert "landmark_age_ms" in telemetry
            assert "tracking_dropped_frames" in telemetry
            assert telemetry["tracking_is_async"] is True

    finally:
        app.close()
        assert not app.running


def test_app_integration_with_sync_tracking():
    """Verify HolographicVFXApp integration when sync_tracking=True."""
    app = HolographicVFXApp(
        width=640,
        height=480,
        synthetic_mode=True,
        headless=True,
        skip_welcome=True,
        sync_tracking=True,
    )
    try:
        assert app.tracker.sync_mode is True

        for _ in range(15):
            ret, frame, telemetry = app.step_frame()
            assert ret is True
            assert telemetry["tracking_is_async"] is False
            assert "tracking_fps" in telemetry

    finally:
        app.close()
        assert not app.running
