"""Latency recorded by a run and exposed with its experiment, plus a generous local performance check.

The performance check is a regression tripwire for this machine, not a hardware-independent claim: its budgets are
many times what the stages normally take.
"""

import time

from test_experiments_api import TERMINAL, make_client, start, wait_for

from backend.latency import WARMUP_FRAMES
from backend.stub_runner import StubRunner
from scripts.make_sample_video import FRAMES


class SlowStartRunner(StubRunner):
    """A stub whose calls for the warm-up frames are slow, as a cold session's are."""

    def __init__(self):
        super().__init__()
        self.calls = 0

    def detect(self, image, confidence_threshold):
        self.calls += 1
        if self.calls <= 2 * WARMUP_FRAMES:  # a clean and a degraded call per frame
            time.sleep(0.2)
        return super().detect(image, confidence_threshold)


def run_experiment(client):
    job = wait_for(client, start(client)["id"], lambda j: j["status"] in TERMINAL)
    assert job["status"] == "completed", job
    return client.get(f"/api/experiments/{job['experiment_id']}").json()


def test_a_run_records_latency_per_stage_with_warm_ups_counted(tmp_path):
    latency = run_experiment(make_client(tmp_path, StubRunner()))["latency"]

    assert latency["warmup_frames"] == WARMUP_FRAMES
    assert latency["frames"] == FRAMES - WARMUP_FRAMES
    assert latency["inference_runs"] == 2 * (FRAMES - WARMUP_FRAMES)
    for stage in ("inference", "processing", "read", "degrade", "render"):
        assert 0 <= latency[stage]["p50_ms"] <= latency[stage]["p90_ms"], stage
    assert latency["read"]["p50_ms"] > 0  # decoding a frame always takes some time
    assert latency["effective_fps"] > 0


def test_slow_warm_up_calls_do_not_reach_the_percentiles(tmp_path):
    latency = run_experiment(make_client(tmp_path, SlowStartRunner()))["latency"]

    assert latency["inference"]["p90_ms"] < 100


def test_the_experiment_records_the_model_and_runtime_it_was_timed_with(tmp_path):
    experiment = run_experiment(make_client(tmp_path, StubRunner()))

    assert experiment["model"] == StubRunner().info.model_dump()


def test_pipeline_stages_stay_within_a_generous_local_budget(tmp_path):
    latency = run_experiment(make_client(tmp_path, StubRunner()))["latency"]

    # The sample is 320 x 192: each of these normally takes a few milliseconds.
    for stage in ("read", "degrade", "render", "processing"):
        assert latency[stage]["p50_ms"] < 250, stage
