"""API contract for degraded runs: one degradation per experiment, clean and degraded results side by side."""

import time

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.stub_runner import StubRunner
from scripts.make_sample_video import FRAMES, HEIGHT, WIDTH

SAMPLE = "synthetic-traffic"
FOG = {"kind": "fog", "severity": 0.5, "seed": 3}


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(static_dir=tmp_path / "no-dist", runner=StubRunner(), cache_dir=tmp_path / "cache"))


def run(client, degradation):
    response = client.post("/api/jobs", json={"sample_id": SAMPLE, "degradation": degradation})
    assert response.status_code == 202, response.text
    job_id = response.json()["id"]
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] not in {"queued", "running"}:
            assert job["status"] == "completed", job
            return client.get(f"/api/experiments/{job['experiment_id']}").json()
        time.sleep(0.01)
    raise AssertionError("the run never finished")


def frame_image(client, experiment, variant, index):
    response = client.get(f"/api/experiments/{experiment['id']}/frames/{variant}/{index}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    return cv2.imdecode(np.frombuffer(response.content, np.uint8), cv2.IMREAD_COLOR)


# --- the recorded configuration ------------------------------------------------------


def test_the_experiment_records_the_degradation_its_derived_parameters_and_seed(client):
    experiment = run(client, FOG)

    assert experiment["degradation"] == {
        "kind": "fog",
        "severity": 0.5,
        "seed": 3,
        "parameters": {"transmission": pytest.approx(0.55), "airlight": pytest.approx(0.8)},
    }


# --- clean and degraded on the same frames ---------------------------------------------


def test_the_detector_runs_on_both_the_clean_and_the_degraded_frame(client):
    # At full darkness the stub's bright car is gone, so the two result sets must differ.
    experiment = run(client, {"kind": "darkness", "severity": 1.0, "seed": 0})

    assert [f["index"] for f in experiment["frames"]] == list(range(FRAMES))
    for frame in experiment["frames"]:
        assert sorted(d["label"] for d in frame["clean"]) == ["car", "person"]
        assert frame["degraded"] == []


def test_clean_and_degraded_images_are_served_for_the_same_frame_at_the_same_size(client):
    experiment = run(client, {"kind": "darkness", "severity": 0.8, "seed": 0})

    clean = frame_image(client, experiment, "clean", 10)
    degraded = frame_image(client, experiment, "degraded", 10)

    assert clean.shape == degraded.shape == (HEIGHT, WIDTH, 3)
    assert degraded.mean() < 0.5 * clean.mean()


def test_the_same_seed_reproduces_the_degraded_frames_and_another_seed_does_not(client):
    noise = {"kind": "noise", "severity": 0.5}
    first = run(client, {**noise, "seed": 11})
    again = run(client, {**noise, "seed": 11})
    other = run(client, {**noise, "seed": 12})

    np.testing.assert_array_equal(frame_image(client, first, "degraded", 5), frame_image(client, again, "degraded", 5))
    assert not np.array_equal(frame_image(client, first, "degraded", 5), frame_image(client, other, "degraded", 5))
    # Each frame gets its own noise, not one pattern repeated on every frame.
    assert not np.array_equal(
        frame_image(client, first, "degraded", 5) - frame_image(client, first, "clean", 5),
        frame_image(client, first, "degraded", 6) - frame_image(client, first, "clean", 6),
    )


@pytest.mark.parametrize("variant", ["both", "../clean", "Clean"])
def test_frame_images_accept_only_the_two_known_variants(client, variant):
    experiment = run(client, FOG)

    assert client.get(f"/api/experiments/{experiment['id']}/frames/{variant}/0").status_code in {404, 422}


# --- validation ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "body",
    [
        {"sample_id": SAMPLE},
        {"sample_id": SAMPLE, "degradation": [FOG, {"kind": "blur", "severity": 0.5, "seed": 0}]},
        {"sample_id": SAMPLE, "degradation": FOG, "degradations": [{"kind": "blur", "severity": 0.5, "seed": 0}]},
        {"sample_id": SAMPLE, "degradation": {**FOG, "blur": 0.5}},
        {"sample_id": SAMPLE, "degradation": {**FOG, "severity": -0.1}},
        {"sample_id": SAMPLE, "degradation": {**FOG, "severity": 1.5}},
        {"sample_id": SAMPLE, "degradation": {**FOG, "kind": "rain"}},
        {"sample_id": SAMPLE, "degradation": {**FOG, "seed": -1}},
        {"sample_id": SAMPLE, "degradation": {"kind": "fog", "severity": 0.5}},
    ],
    ids=[
        "no-degradation",
        "two-as-a-list",
        "second-under-another-key",
        "extra-setting",
        "severity-below-0",
        "severity-above-1",
        "unknown-kind",
        "negative-seed",
        "no-seed",
    ],
)
def test_a_run_needs_exactly_one_valid_degradation(client, body):
    response = client.post("/api/jobs", json=body)

    assert response.status_code == 422


def test_a_nan_severity_is_rejected(client):
    body = '{"sample_id": "synthetic-traffic", "degradation": {"kind": "fog", "severity": NaN, "seed": 0}}'

    response = client.post("/api/jobs", content=body, headers={"Content-Type": "application/json"})

    assert response.status_code == 422


# --- the catalog the inspector reads ---------------------------------------------------------


def test_the_catalog_lists_exactly_the_five_degradations(client):
    catalog = client.get("/api/degradations").json()

    assert [d["kind"] for d in catalog] == ["darkness", "blur", "fog", "noise", "jpeg"]
    assert all(d["title"] for d in catalog)
    assert [d["kind"] for d in catalog if d["randomized"]] == ["noise"]


def test_derived_parameters_are_served_for_a_severity(client):
    response = client.get("/api/degradations/jpeg/parameters", params={"severity": 1.0})

    assert response.status_code == 200
    assert response.json() == {"quality": 5}


@pytest.mark.parametrize("query", ["severity=1.5", "severity=-1", ""])
def test_derived_parameters_need_a_severity_in_zero_to_one(client, query):
    assert client.get(f"/api/degradations/fog/parameters?{query}").status_code == 422


def test_derived_parameters_of_an_unknown_kind_are_rejected(client):
    assert client.get("/api/degradations/rain/parameters?severity=0.5").status_code == 422
