"""API contract tests for Benchmark runs on the fixture dataset: start, poll, complete, cancel, cache reuse, manifest
checks, and results re-scored at any display threshold without re-running inference."""

import pytest
from fastapi.testclient import TestClient
from test_experiments_api import TERMINAL, FailingRunner, GatedRunner, wait_for

from backend.app import create_app
from backend.conditions import CONDITIONS
from backend.stub_runner import StubRunner
from scripts.make_fixture_dataset import build_fixture_dataset

CLEAR_DAY = "2018-02-03_10-00-00_00100"


@pytest.fixture
def root(tmp_path):
    root = tmp_path / "SeeingThroughFog"
    build_fixture_dataset(root)
    return root


def make_client(tmp_path, root, runner):
    app = create_app(static_dir=tmp_path / "no-dist", runner=runner, cache_dir=tmp_path / "cache", dataset_root=root)
    return TestClient(app)


def subset_manifest(client, **params):
    return client.get("/api/dataset/subset", params=params).json()["manifest"]


def start(client, manifest=None):
    response = client.post("/api/benchmark/jobs", json={"manifest": manifest or subset_manifest(client)})
    assert response.status_code in (200, 202), response.text
    return response


def run_to_completion(client, manifest=None):
    job = start(client, manifest).json()
    return wait_for(client, job["id"], lambda j: j["status"] in TERMINAL)


def results(client, experiment_id, display_threshold=0.25):
    response = client.get(
        f"/api/benchmark/experiments/{experiment_id}", params={"display_threshold": display_threshold}
    )
    assert response.status_code == 200, response.text
    return response.json()


def condition(body, name):
    return next(c for c in body["conditions"] if c["condition"] == name)


def class_row(row, name):
    return next(c for c in row["classes"] if c["class_name"] == name)


# --- start -> poll -> complete ------------------------------------------------------------


def test_a_benchmark_runs_as_a_job_over_every_manifest_frame(tmp_path, root):
    runner = GatedRunner()
    client = make_client(tmp_path, root, runner)

    response = start(client)
    job = response.json()

    assert response.status_code == 202
    assert job["mode"] == "benchmark"
    assert job["status"] in {"queued", "running"}
    assert job["cached"] is False
    running = wait_for(client, job["id"], lambda j: j["status"] == "running" and j["frames_total"] == len(CONDITIONS))
    assert running["frames_done"] == 0

    runner.allow(3)
    partway = wait_for(client, job["id"], lambda j: j["frames_done"] == 3)
    assert partway["progress"] == 3 / len(CONDITIONS)

    runner.open()
    done = wait_for(client, job["id"], lambda j: j["status"] in TERMINAL)
    assert done["status"] == "completed"
    assert done["frames_done"] == len(CONDITIONS)
    assert done["progress"] == 1.0
    assert runner.calls == len(CONDITIONS)  # one detector call per frame


def test_results_list_every_condition_with_map_objects_and_low_n(tmp_path, root):
    client = make_client(tmp_path, root, StubRunner())
    job = run_to_completion(client)

    body = results(client, job["experiment_id"])

    assert [c["condition"] for c in body["conditions"]] == list(CONDITIONS)
    for row in body["conditions"]:
        assert row["frames"] == 1
        assert row["low_n"] is True  # one fixture frame per condition
    # The stub finds the car drawn in clear-day; the pedestrian beside it is missed.
    assert condition(body, "clear-day")["map"] == 0.5
    assert condition(body, "clear-day")["objects"] == 2
    # A car and an Obstacle ignore region: the stub's stray person falls inside the region and is forgiven.
    assert condition(body, "fog-night")["map"] == 1.0
    assert condition(body, "fog-night")["objects"] == 1
    # The stub's car lands on a LargeVehicle: a class confusion, not a hit. Nothing is found.
    assert condition(body, "snow-day")["map"] == 0.0
    assert body["low_n_objects"] == 30
    assert body["iou_threshold"] == 0.5


def test_per_class_ap_precision_recall_and_counts_are_reported(tmp_path, root):
    client = make_client(tmp_path, root, StubRunner())
    job = run_to_completion(client)

    clear_day = condition(results(client, job["experiment_id"], display_threshold=0.25), "clear-day")
    car, pedestrian = class_row(clear_day, "PassengerCar"), class_row(clear_day, "Pedestrian")

    assert (car["ap"], car["precision"], car["recall"], car["objects"], car["frames"]) == (1.0, 1.0, 1.0, 1, 1)
    # The stub's person at 0.3 is a false alarm.
    assert (pedestrian["ap"], pedestrian["precision"], pedestrian["recall"]) == (0.0, 0.0, 0.0)
    assert class_row(clear_day, "LargeVehicle")["ap"] is None  # no objects


def test_changing_the_display_threshold_updates_precision_and_recall_without_inference(tmp_path, root):
    runner = GatedRunner()
    runner.open()
    client = make_client(tmp_path, root, runner)
    job = run_to_completion(client)
    calls = runner.calls

    low = class_row(condition(results(client, job["experiment_id"], 0.25), "clear-day"), "Pedestrian")
    high = class_row(condition(results(client, job["experiment_id"], 0.5), "clear-day"), "Pedestrian")

    assert (low["predictions"], low["precision"]) == (1, 0.0)
    assert (high["predictions"], high["precision"]) == (0, None)
    assert low["ap"] == high["ap"]
    assert runner.calls == calls


def test_the_experiment_record_holds_the_whole_manifest_and_the_model(tmp_path, root):
    client = make_client(tmp_path, root, StubRunner())
    manifest = subset_manifest(client, seed=7, cap=5)
    job = run_to_completion(client, manifest)

    body = results(client, job["experiment_id"])

    assert body["manifest"] == manifest
    assert body["model"]["name"] == "Stub detector"
    assert body["model"]["runtime"]
    assert body["class_mapping_version"] == 1
    assert body["confidence_floor"] == 0.05
    assert body["warnings"] == []


# --- cache -----------------------------------------------------------------------------------


def test_rerunning_the_same_manifest_reuses_the_cache(tmp_path, root):
    runner = GatedRunner()
    runner.open()
    client = make_client(tmp_path, root, runner)
    first = run_to_completion(client)
    calls = runner.calls

    again = start(client)

    assert again.status_code == 200
    assert again.json()["cached"] is True
    assert again.json()["status"] == "completed"
    assert again.json()["experiment_id"] == first["experiment_id"]
    assert again.json()["frames_done"] == again.json()["frames_total"] == len(CONDITIONS)
    assert runner.calls == calls


def test_cached_benchmarks_survive_a_restart(tmp_path, root):
    first = run_to_completion(make_client(tmp_path, root, StubRunner()))

    client = make_client(tmp_path, root, FailingRunner())
    again = start(client).json()

    assert again["cached"] is True
    assert results(client, again["experiment_id"])["id"] == first["experiment_id"]


def test_another_manifest_starts_a_new_run(tmp_path, root):
    client = make_client(tmp_path, root, StubRunner())
    first = run_to_completion(client)

    other = start(client, subset_manifest(client, seed=3))

    assert other.status_code == 202
    assert other.json()["experiment_id"] != first["experiment_id"]
    wait_for(client, other.json()["id"], lambda j: j["status"] in TERMINAL)


# --- cancel and failure ------------------------------------------------------------------------


def test_a_cancelled_benchmark_is_not_cached(tmp_path, root):
    runner = GatedRunner()
    client = make_client(tmp_path, root, runner)
    job = start(client).json()
    wait_for(client, job["id"], lambda j: j["status"] == "running")

    client.post(f"/api/jobs/{job['id']}/cancel")
    runner.open()
    done = wait_for(client, job["id"], lambda j: j["status"] in TERMINAL)

    assert done["status"] == "cancelled"
    assert client.get(f"/api/benchmark/experiments/{job['experiment_id']}", params={"display_threshold": 0.5}).status_code == 404
    again = start(client)
    assert again.status_code == 202
    assert again.json()["cached"] is False
    wait_for(client, again.json()["id"], lambda j: j["status"] in TERMINAL)


def test_a_failed_benchmark_says_where_and_is_not_cached(tmp_path, root):
    client = make_client(tmp_path, root, FailingRunner())

    job = run_to_completion(client)

    assert job["status"] == "failed"
    assert "frame 2" in job["error"]
    assert "inference exploded" in job["error"]
    assert client.get(f"/api/benchmark/experiments/{job['experiment_id']}", params={"display_threshold": 0.5}).status_code == 404


# --- refused starts ------------------------------------------------------------------------------


def test_a_manifest_from_another_vocabulary_version_is_refused_in_plain_language(tmp_path, root):
    client = make_client(tmp_path, root, StubRunner())
    manifest = {**subset_manifest(client), "vocabulary_version": 99}

    response = client.post("/api/benchmark/jobs", json={"manifest": manifest})

    assert response.status_code == 422
    assert "vocabulary version 99" in response.json()["detail"]


def test_frames_missing_from_the_local_dataset_are_reported(tmp_path, root):
    client = make_client(tmp_path, root, StubRunner())
    manifest = subset_manifest(client)
    manifest["frames"]["clear-day"].append("2019-01-01_00-00-00_00001")

    response = client.post("/api/benchmark/jobs", json={"manifest": manifest})

    assert response.status_code == 422
    assert "2019-01-01_00-00-00_00001" in response.json()["detail"]
    assert "not in the local dataset" in response.json()["detail"]


def test_a_manifest_is_json_never_a_path(tmp_path, root):
    client = make_client(tmp_path, root, StubRunner())

    for body in ({"manifest": "manifests/subset.json"}, {"path": "manifests/subset.json"}):
        assert client.post("/api/benchmark/jobs", json=body).status_code == 422


def test_a_benchmark_needs_a_ready_dataset(tmp_path, root):
    client = TestClient(create_app(static_dir=tmp_path / "no-dist", runner=StubRunner(), cache_dir=tmp_path / "c"))
    manifest = subset_manifest(make_client(tmp_path, root, StubRunner()))

    response = client.post("/api/benchmark/jobs", json={"manifest": manifest})

    assert response.status_code == 409
    assert "dataset" in response.json()["detail"].lower()


def test_a_benchmark_needs_the_detector(tmp_path, root):
    client = make_client(tmp_path, root, None)

    response = client.post("/api/benchmark/jobs", json={"manifest": subset_manifest(client)})

    assert response.status_code == 503
    assert "fetch_model.py" in response.json()["detail"]


# --- results lookups ----------------------------------------------------------------------------


def test_unknown_benchmark_results_are_404(tmp_path, root):
    client = make_client(tmp_path, root, StubRunner())

    assert client.get(f"/api/benchmark/experiments/{'f' * 64}", params={"display_threshold": 0.5}).status_code == 404
    assert client.get("/api/benchmark/experiments/..%5C..%5Cetc", params={"display_threshold": 0.5}).status_code == 404


@pytest.mark.parametrize("threshold", [-0.1, 1.5, "nan", "high"])
def test_a_bad_display_threshold_is_rejected(tmp_path, root, threshold):
    client = make_client(tmp_path, root, StubRunner())
    job = run_to_completion(client)

    response = client.get(f"/api/benchmark/experiments/{job['experiment_id']}", params={"display_threshold": threshold})

    assert response.status_code == 422


def test_a_synthetic_experiment_is_not_benchmark_results(tmp_path, root):
    client = make_client(tmp_path, root, StubRunner())
    job = client.post("/api/jobs", json={"sample_id": "synthetic-traffic", "degradation": {"kind": "blur", "severity": 0.1, "seed": 0}}).json()
    wait_for(client, job["id"], lambda j: j["status"] in TERMINAL)

    assert client.get(f"/api/benchmark/experiments/{job['experiment_id']}", params={"display_threshold": 0.5}).status_code == 404
