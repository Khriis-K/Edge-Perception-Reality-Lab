"""Latency summary: percentiles per stage, warm-up frames left out, and effective fps from the medians."""

import pytest

from backend.latency import FrameTiming, stage_latency, summarize


def timing(read=0.001, degrade=0.002, inference=(0.010, 0.012), processing=(0.003, 0.003), render=0.004):
    return FrameTiming(read_s=read, degrade_s=degrade, inference_s=list(inference), processing_s=list(processing), render_s=render)


def test_stage_latency_reports_p50_and_p90_in_milliseconds():
    stage = stage_latency([i / 1000 for i in range(1, 11)])  # 1..10 ms

    assert stage.p50_ms == pytest.approx(5.5)
    assert stage.p90_ms == pytest.approx(9.1)


def test_warm_up_frames_are_left_out_and_counted():
    warm = timing(read=1.0, degrade=1.0, inference=(1.0, 1.0), processing=(1.0, 1.0), render=1.0)
    steady = [timing() for _ in range(5)]

    summary = summarize([warm, warm, *steady], warmup_frames=2)

    assert summary.warmup_frames == 2
    assert summary.frames == 5
    assert summary.inference_runs == 10  # both detector calls of every measured frame
    assert summary.read.p90_ms == pytest.approx(1.0)
    assert summary.inference.p90_ms < 20


def test_inference_pools_the_clean_and_degraded_calls():
    summary = summarize([timing(inference=(0.010, 0.030))] * 4, warmup_frames=0)

    assert summary.inference.p50_ms == pytest.approx(20.0)


def test_effective_fps_is_one_stream_reading_and_detecting_each_frame_at_the_medians():
    # read 1 ms + pre/post-processing 3 ms + inference 11 ms = 15 ms a frame. Degrading and rendering are lab
    # work a deployed detector wouldn't do, so they don't count.
    summary = summarize([timing()] * 3, warmup_frames=0)

    assert summary.inference.p50_ms == pytest.approx(11.0)
    assert summary.effective_fps == pytest.approx(1000 / 15)


def test_effective_fps_is_none_when_nothing_measurable_took_time():
    zero = timing(read=0.0, inference=(0.0, 0.0), processing=(0.0, 0.0))

    assert summarize([zero] * 3, warmup_frames=0).effective_fps is None


def test_a_clip_no_longer_than_the_warm_up_has_no_latency():
    assert summarize([timing(), timing()], warmup_frames=2) is None
