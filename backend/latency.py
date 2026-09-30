"""How long each stage of a run takes on this machine: edge-readiness, measured, never promised.

Measurement method. Every frame of a run is timed with time.perf_counter, stage by stage:
- read: decoding the next frame from the video;
- degrade: applying the degradation;
- inference: the ONNX Runtime session.run call alone, once for the clean and once for the degraded frame (the stub
  runner, which has no session, times its whole detect call);
- processing: the rest of each detector call, letterboxing before inference and decoding plus NMS after it;
- render: encoding both frames as JPEGs into the cache.
The first WARMUP_FRAMES frames are left out of every stage and counted: a fresh session allocates memory and
picks kernels on its first calls, which would inflate the tail. Each stage reports its p50 and p90 (numpy's linear
interpolation) in milliseconds; inference pools the clean and degraded calls.

Effective fps is one stream reading and detecting each frame at the medians: 1000 / (read p50 + processing p50 +
inference p50). Degrading and rendering are left out, since a deployed detector wouldn't do them.

What the numbers are not: they are this machine's timing with the execution provider recorded alongside, not a
real-time claim for any other hardware. Another run on the same machine at the same time shares the CPU and slows
both. A cached run shows the timing from when it ran.
"""

from dataclasses import dataclass

import numpy as np
from pydantic import BaseModel

WARMUP_FRAMES = 2


@dataclass
class FrameTiming:
    """One frame's stage times, in seconds. Inference and processing have one entry per detector call."""

    read_s: float
    degrade_s: float
    inference_s: list[float]
    processing_s: list[float]
    render_s: float


class StageLatency(BaseModel):
    p50_ms: float
    p90_ms: float


class LatencySummary(BaseModel):
    warmup_frames: int  # left out of every stage
    frames: int  # measured
    inference_runs: int  # measured detector calls
    inference: StageLatency
    processing: StageLatency  # pre- and post-processing around inference
    read: StageLatency
    degrade: StageLatency
    render: StageLatency
    effective_fps: float | None  # None if the measured stages took no time at all


def stage_latency(seconds: list[float]) -> StageLatency:
    p50, p90 = np.percentile(np.asarray(seconds) * 1000, [50, 90])
    return StageLatency(p50_ms=float(p50), p90_ms=float(p90))


def summarize(timings: list[FrameTiming], warmup_frames: int = WARMUP_FRAMES) -> LatencySummary | None:
    """Per-stage percentiles over the frames after the warm-up. None when no frame is left to measure."""
    measured = timings[warmup_frames:]
    if not measured:
        return None
    inference = stage_latency([s for t in measured for s in t.inference_s])
    processing = stage_latency([s for t in measured for s in t.processing_s])
    read = stage_latency([t.read_s for t in measured])
    frame_ms = read.p50_ms + processing.p50_ms + inference.p50_ms
    return LatencySummary(
        warmup_frames=warmup_frames,
        frames=len(measured),
        inference_runs=sum(len(t.inference_s) for t in measured),
        inference=inference,
        processing=processing,
        read=read,
        degrade=stage_latency([t.degrade_s for t in measured]),
        render=stage_latency([t.render_s for t in measured]),
        effective_fps=1000 / frame_ms if frame_ms > 0 else None,
    )
