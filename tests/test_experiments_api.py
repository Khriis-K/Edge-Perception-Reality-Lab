"""API contract tests for detection runs: samples, background jobs, results, and frame images."""

import shutil
import threading
import time

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.jobs import CONFIDENCE_FLOOR
from backend.stub_runner import StubRunner
from scripts.make_sample_video import FRAMES, HEIGHT, WIDTH

SAMPLE = "synthetic-traffic"
TERMINAL = {"completed", "cancelled", "failed"}


class GatedRunner(StubRunner):
    """A stub that runs only as many frames as the test allows, so a job can be caught mid-run."""

    def __init__(self):
        super().__init__()
        self._allowed = threading.Semaphore(0)
        self.calls = 0

    def allow(self, frames):
        self._allowed.release(frames)

    def open(self):
        self.allow(10_000)

    def detect(self, image, confidence_threshold):
        self.calls += 1
        self._allowed.acquire(timeout=10)
        return super().detect(image, confidence_threshold)


class FailingRunner(StubRunner):
    """A stub that breaks on the third frame."""

    def __init__(self):
        super().__init__()
        self.calls = 0

    def detect(self, image, confidence_threshold):
        self.calls += 1
        if self.calls == 3:
            raise RuntimeError("inference exploded")
        return super().detect(image, confidence_threshold)


def make_client(tmp_path, runner):
    return TestClient(create_app(static_dir=tmp_path / "no-dist", runner=runner, cache_dir=tmp_path / "cache"))


@pytest.fixture
def client(tmp_path):
    return make_client(tmp_path, StubRunner())


def start(client):
    response = client.post("/api/jobs", json={"sample_id": SAMPLE})
    assert response.status_code == 202, response.text
    return response.json()


def wait_for(client, job_id, predicate, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if predicate(job):
            return job
        time.sleep(0.01)
    raise AssertionError(f"job never reached the expected state; last seen: {job}")


def run_to_completion(client):
    job = start(client)
    return wait_for(client, job["id"], lambda j: j["status"] in TERMINAL)


# --- samples ----------------------------------------------------------------------


def test_samples_list_the_bundled_video_by_id_without_a_path(client):
    samples = client.get("/api/samples").json()

    # The real clip comes first: the Synthetic screen preselects the first sample.
    assert [s["id"] for s in samples] == ["krakow-city-driving", SAMPLE]
    for sample in samples:
        assert "path" not in sample
        assert sample["title"]


# --- start -> progress -> complete --------------------------------------------------


def test_starting_a_run_returns_a_job_at_once_before_any_inference_finishes(tmp_path):
    runner = GatedRunner()
    client = make_client(tmp_path, runner)

    job = start(client)

    assert job["status"] in {"queued", "running"}
    assert job["mode"] == "synthetic"
    assert job["frames_done"] == 0
    assert job["experiment_id"]
    runner.open()


def test_progress_is_reported_while_the_job_runs(tmp_path):
    runner = GatedRunner()
    client = make_client(tmp_path, runner)
    job = start(client)

    running = wait_for(client, job["id"], lambda j: j["status"] == "running" and j["frames_total"] == FRAMES)
    assert running["progress"] == 0.0

    runner.allow(12)
    partway = wait_for(client, job["id"], lambda j: j["frames_done"] == 12)
    assert partway["status"] == "running"
    assert partway["progress"] == 12 / FRAMES

    runner.open()
    done = wait_for(client, job["id"], lambda j: j["status"] in TERMINAL)
    assert done["status"] == "completed"
    assert done["frames_done"] == FRAMES
    assert done["progress"] == 1.0
    assert done["error"] is None


def test_a_completed_run_has_normalized_detections_for_every_frame(client):
    job = run_to_completion(client)

    experiment = client.get(f"/api/experiments/{job['experiment_id']}").json()

    assert experiment["id"] == job["experiment_id"]
    assert experiment["sample_id"] == SAMPLE
    assert (experiment["frame_width"], experiment["frame_height"]) == (WIDTH, HEIGHT)
    assert [f["index"] for f in experiment["frames"]] == list(range(FRAMES))
    for frame in experiment["frames"]:
        labels = sorted(d["label"] for d in frame["detections"])
        assert labels == ["car", "person"]
        for detection in frame["detections"]:
            assert all(0 <= detection["box"][k] <= 1 for k in ("x1", "y1", "x2", "y2"))


def test_results_keep_raw_detections_down_to_the_confidence_floor_and_no_lower(client):
    job = run_to_completion(client)

    experiment = client.get(f"/api/experiments/{job['experiment_id']}").json()

    confidences = [d["confidence"] for f in experiment["frames"] for d in f["detections"]]
    assert experiment["confidence_floor"] == CONFIDENCE_FLOOR
    assert min(confidences) == 0.3  # below the display default, above the floor: kept
    assert all(c >= CONFIDENCE_FLOOR for c in confidences)  # the stub's 0.02 detection is dropped


def test_a_completed_run_records_the_model_metadata(client):
    job = run_to_completion(client)

    experiment = client.get(f"/api/experiments/{job['experiment_id']}").json()

    assert experiment["model"] == StubRunner().info.model_dump()


def test_frame_images_are_served_as_jpeg_at_the_video_size(client):
    job = run_to_completion(client)

    response = client.get(f"/api/experiments/{job['experiment_id']}/frames/{FRAMES - 1}")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    image = cv2.imdecode(np.frombuffer(response.content, np.uint8), cv2.IMREAD_COLOR)
    assert image.shape == (HEIGHT, WIDTH, 3)


def test_a_frame_whose_cached_image_was_deleted_is_404_not_a_server_error(tmp_path, client):
    job = run_to_completion(client)
    shutil.rmtree(tmp_path / "cache")

    response = client.get(f"/api/experiments/{job['experiment_id']}/frames/0")

    assert response.status_code == 404


# --- cancel -------------------------------------------------------------------------


def test_cancel_mid_run_stops_the_job_and_never_records_it_as_complete(tmp_path):
    runner = GatedRunner()
    client = make_client(tmp_path, runner)
    job = start(client)
    wait_for(client, job["id"], lambda j: j["status"] == "running")

    response = client.post(f"/api/jobs/{job['id']}/cancel")
    assert response.status_code == 200
    runner.open()

    final = wait_for(client, job["id"], lambda j: j["status"] in TERMINAL)
    assert final["status"] == "cancelled"
    assert final["frames_done"] < FRAMES
    assert runner.calls < FRAMES  # it stopped, rather than finishing and discarding
    assert client.get(f"/api/experiments/{job['experiment_id']}").status_code == 404
    assert client.get(f"/api/experiments/{job['experiment_id']}/frames/0").status_code == 404
    assert not (tmp_path / "cache" / job["experiment_id"]).exists()


def test_cancelling_a_finished_job_leaves_it_complete(client):
    job = run_to_completion(client)

    response = client.post(f"/api/jobs/{job['id']}/cancel")

    assert response.json()["status"] == "completed"
    assert client.get(f"/api/experiments/{job['experiment_id']}").status_code == 200


# --- failure --------------------------------------------------------------------------


def test_a_failed_job_reports_the_error_and_is_never_recorded_as_complete(tmp_path):
    client = make_client(tmp_path, FailingRunner())

    job = run_to_completion(client)

    assert job["status"] == "failed"
    assert "inference exploded" in job["error"]
    assert client.get(f"/api/experiments/{job['experiment_id']}").status_code == 404
    assert not (tmp_path / "cache" / job["experiment_id"]).exists()


def test_starting_a_run_without_model_weights_explains_how_to_fetch_them(tmp_path):
    client = make_client(tmp_path, runner=None)

    response = client.post("/api/jobs", json={"sample_id": SAMPLE})

    assert response.status_code == 503
    assert "scripts/fetch_model.py" in response.json()["detail"]


# --- validation -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "body",
    [{"sample_id": "nope"}, {"sample_id": "../samples/synthetic_traffic.mp4"}, {}, {"path": "C:/video.mp4"}],
    ids=["unknown-sample", "path-as-id", "missing", "path-field"],
)
def test_starting_a_run_needs_a_known_sample_id(client, body):
    response = client.post("/api/jobs", json=body)

    assert response.status_code == 422


@pytest.mark.parametrize("method, path", [("get", "/api/jobs/nope"), ("post", "/api/jobs/nope/cancel")])
def test_unknown_jobs_are_404(client, method, path):
    assert getattr(client, method)(path).status_code == 404


def test_unknown_experiments_are_404(client):
    assert client.get("/api/experiments/nope").status_code == 404


# --- frame images: known ids only -------------------------------------------------------


@pytest.mark.parametrize(
    "path, status",
    [
        ("/api/experiments/unknown/frames/0", 404),
        ("/api/experiments/..%2F..%2Fpyproject.toml/frames/0", 404),
        ("/api/experiments/{exp}/frames/{frames}", 404),  # one past the last frame
        ("/api/experiments/{exp}/frames/-1", 422),
        ("/api/experiments/{exp}/frames/0.jpg", 422),
        # Decoded slashes mean no route matches at all.
        ("/api/experiments/{exp}/frames/..%2F..%2Fpyproject.toml", 404),
    ],
    ids=["unknown-experiment", "path-as-experiment", "out-of-range", "negative", "file-name", "path-as-frame"],
)
def test_frame_endpoint_rejects_anything_but_a_known_experiment_and_frame(client, path, status):
    job = run_to_completion(client)

    response = client.get(path.format(exp=job["experiment_id"], frames=FRAMES))

    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/json")


def test_frames_of_a_running_job_are_not_served(tmp_path):
    runner = GatedRunner()
    client = make_client(tmp_path, runner)
    job = start(client)
    wait_for(client, job["id"], lambda j: j["status"] == "running")

    assert client.get(f"/api/experiments/{job['experiment_id']}/frames/0").status_code == 404
    runner.open()


# --- schema -------------------------------------------------------------------------------


def test_run_endpoints_are_in_the_openapi_schema(client):
    schema = client.get("/openapi.json").json()

    for path in [
        "/api/samples",
        "/api/jobs",
        "/api/jobs/{job_id}",
        "/api/jobs/{job_id}/cancel",
        "/api/experiments/{experiment_id}",
        "/api/experiments/{experiment_id}/frames/{frame_index}",
    ]:
        assert path in schema["paths"]
