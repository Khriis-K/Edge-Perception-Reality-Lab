"""API contract tests for synthetic degradation on the subset's clear frames: a job like any other, stability and
ground-truth metrics for both variants, the cache, the Synthetic run history, and the extra Benchmark condition row."""

import pytest
from fastapi.testclient import TestClient
from test_benchmark_api import condition, make_client, results, root, subset_manifest  # noqa: F401 (root: fixture)
from test_benchmark_api import run_to_completion as run_benchmark
from test_experiments_api import TERMINAL, FailingRunner, GatedRunner, wait_for

from backend.app import create_app
from backend.stub_runner import StubRunner

FOG = {"kind": "fog", "severity": 0.6, "seed": 0}
# Dark enough that the stub loses the fixture's bright car.
DARKNESS = {"kind": "darkness", "severity": 0.6, "seed": 0}


def start(client, degradation=FOG, manifest=None, condition_name="clear-day"):
    body = {"manifest": manifest or subset_manifest(client), "condition": condition_name, "degradation": degradation}
    response = client.post("/api/synthetic-frames/jobs", json=body)
    assert response.status_code in (200, 202), response.text
    return response


def run_to_completion(client, **kwargs):
    job = start(client, **kwargs).json()
    return wait_for(client, job["id"], lambda j: j["status"] in TERMINAL)


def frames_results(client, experiment_id, display_threshold=0.25):
    response = client.get(
        f"/api/synthetic-frames/experiments/{experiment_id}", params={"display_threshold": display_threshold}
    )
    assert response.status_code == 200, response.text
    return response.json()


def class_row(row, name):
    return next(c for c in row["classes"] if c["class_name"] == name)


# --- a run ------------------------------------------------------------------------------------------------


def test_a_run_over_the_clear_frames_is_a_job_with_its_own_mode(tmp_path, root):
    runner = GatedRunner()
    client = make_client(tmp_path, root, runner)

    response = start(client)
    job = response.json()

    assert response.status_code == 202
    assert job["mode"] == "synthetic-frames"
    assert job["cached"] is False
    running = wait_for(client, job["id"], lambda j: j["status"] == "running" and j["frames_total"] == 1)
    assert running["frames_done"] == 0
    runner.open()
    assert wait_for(client, job["id"], lambda j: j["status"] in TERMINAL)["status"] == "completed"


def test_a_fog_run_reports_stability_and_ap_for_clean_and_degraded(tmp_path, root):
    client = make_client(tmp_path, root, StubRunner())
    job = run_to_completion(client)

    body = frames_results(client, job["experiment_id"])

    assert body["condition"] == "clear-day"
    assert body["degradation"]["kind"] == "fog"
    assert body["degradation"]["severity"] == 0.6
    assert body["degradation"]["parameters"]["transmission"] == pytest.approx(0.46)
    # The stub still finds the bright car through fog, and the person it places beside it: both retained, and AP
    # unchanged.
    assert (body["stability"]["retention"]["count"], body["stability"]["retention"]["total"]) == (2, 2)
    assert body["stability"]["frames_evaluated"] == 1
    for variant in ("clean", "degraded"):
        assert body[variant]["map"] == 0.5
        assert body[variant]["objects"] == 2
        assert body[variant]["frames"] == 1
        assert class_row(body[variant], "PassengerCar")["ap"] == 1.0
        assert class_row(body[variant], "Pedestrian")["ap"] == 0.0


def test_a_degradation_that_loses_the_car_shows_in_both_metric_sets(tmp_path, root):
    client = make_client(tmp_path, root, StubRunner())
    job = run_to_completion(client, degradation=DARKNESS)

    body = frames_results(client, job["experiment_id"])

    assert body["clean"]["map"] == 0.5
    assert body["degraded"]["map"] == 0.0
    assert (body["stability"]["retention"]["count"], body["stability"]["retention"]["total"]) == (0, 2)


def test_clean_ap_equals_the_benchmarks_ap_on_the_same_frames(tmp_path, root):
    client = make_client(tmp_path, root, StubRunner())
    benchmark = condition(results(client, run_benchmark(client)["experiment_id"]), "clear-day")

    clean = frames_results(client, run_to_completion(client, degradation=DARKNESS)["experiment_id"])["clean"]

    assert clean["map"] == benchmark["map"]
    assert clean["classes"] == benchmark["classes"]


def test_a_clear_night_run_uses_the_clear_night_frames(tmp_path, root):
    client = make_client(tmp_path, root, StubRunner())
    job = run_to_completion(client, condition_name="clear-night")

    body = frames_results(client, job["experiment_id"])

    assert body["condition"] == "clear-night"
    assert class_row(body["clean"], "LargeVehicle")["objects"] == 1


def test_results_are_rescored_at_any_display_threshold_without_inference(tmp_path, root):
    runner = GatedRunner()
    runner.open()
    client = make_client(tmp_path, root, runner)
    job = run_to_completion(client)
    calls = runner.calls

    low = class_row(frames_results(client, job["experiment_id"], 0.25)["clean"], "Pedestrian")
    high = class_row(frames_results(client, job["experiment_id"], 0.5)["clean"], "Pedestrian")

    assert (low["predictions"], high["predictions"]) == (1, 0)
    assert runner.calls == calls


# --- cache ------------------------------------------------------------------------------------------------


def test_a_repeat_reuses_the_cache(tmp_path, root):
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
    assert again.json()["frames_done"] == again.json()["frames_total"] == 1
    assert runner.calls == calls


@pytest.mark.parametrize(
    "change",
    [
        {"degradation": DARKNESS},
        {"degradation": {**FOG, "severity": 0.7}},
        {"degradation": {**FOG, "seed": 1}},
        {"condition_name": "clear-night"},
    ],
)
def test_another_degradation_severity_seed_or_condition_starts_a_new_run(tmp_path, root, change):
    client = make_client(tmp_path, root, StubRunner())
    first = run_to_completion(client)

    other = start(client, **change)

    assert other.status_code == 202
    assert other.json()["experiment_id"] != first["experiment_id"]
    wait_for(client, other.json()["id"], lambda j: j["status"] in TERMINAL)


def test_another_manifest_starts_a_new_run(tmp_path, root):
    client = make_client(tmp_path, root, StubRunner())
    first = run_to_completion(client)

    other = start(client, manifest=subset_manifest(client, seed=3))

    assert other.json()["experiment_id"] != first["experiment_id"]
    wait_for(client, other.json()["id"], lambda j: j["status"] in TERMINAL)


def test_cached_runs_survive_a_restart(tmp_path, root):
    first = run_to_completion(make_client(tmp_path, root, StubRunner()))

    client = make_client(tmp_path, root, FailingRunner())
    again = start(client).json()

    assert again["cached"] is True
    assert frames_results(client, again["experiment_id"])["id"] == first["experiment_id"]


def test_a_run_and_a_benchmark_never_share_an_id(tmp_path, root):
    client = make_client(tmp_path, root, StubRunner())

    frames_run = run_to_completion(client)
    benchmark = run_benchmark(client)

    assert frames_run["experiment_id"] != benchmark["experiment_id"]
    lookup = client.get(f"/api/benchmark/experiments/{frames_run['experiment_id']}", params={"display_threshold": 0.5})
    assert lookup.status_code == 404


def test_a_cancelled_run_is_not_cached(tmp_path, root):
    runner = GatedRunner()
    client = make_client(tmp_path, root, runner)
    job = start(client).json()
    wait_for(client, job["id"], lambda j: j["status"] == "running")

    client.post(f"/api/jobs/{job['id']}/cancel")
    runner.open()
    done = wait_for(client, job["id"], lambda j: j["status"] in TERMINAL)

    assert done["status"] == "cancelled"
    lookup = client.get(f"/api/synthetic-frames/experiments/{job['experiment_id']}", params={"display_threshold": 0.5})
    assert lookup.status_code == 404


def test_a_failed_run_says_where_and_is_not_cached(tmp_path, root):
    class FailsAtOnce(StubRunner):
        def detect(self, image, confidence_threshold):
            raise RuntimeError("inference exploded")

    client = make_client(tmp_path, root, FailsAtOnce())

    job = run_to_completion(client)

    assert job["status"] == "failed"
    assert "frame 0" in job["error"]
    assert "inference exploded" in job["error"]
    lookup = client.get(f"/api/synthetic-frames/experiments/{job['experiment_id']}", params={"display_threshold": 0.5})
    assert lookup.status_code == 404


# --- the Synthetic run history ----------------------------------------------------------------------------


def test_the_run_history_lists_the_run_under_its_frames(tmp_path, root):
    client = make_client(tmp_path, root, StubRunner())
    job = run_to_completion(client)

    runs = client.get("/api/experiments").json()

    assert len(runs) == 1
    run = runs[0]
    assert run["id"] == job["experiment_id"]
    assert run["input"] == "dataset"
    assert run["sample_id"] == "clear-day"
    assert run["sample_title"] == "Clear · day frames"
    assert run["degradation"]["kind"] == "fog"
    assert run["frame_count"] == 1


def test_video_runs_are_listed_as_video_input(tmp_path, root):
    client = make_client(tmp_path, root, StubRunner())
    job = client.post(
        "/api/jobs", json={"sample_id": "synthetic-traffic", "degradation": {"kind": "blur", "severity": 0.1, "seed": 0}}
    ).json()
    wait_for(client, job["id"], lambda j: j["status"] in TERMINAL)

    (run,) = client.get("/api/experiments").json()

    assert run["input"] == "video"
    assert run["sample_id"] == "synthetic-traffic"


# --- the Benchmark condition tree -------------------------------------------------------------------------


def test_the_degraded_condition_is_a_row_beside_the_benchmark_with_its_map_and_counts(tmp_path, root):
    client = make_client(tmp_path, root, StubRunner())
    benchmark = run_benchmark(client)
    frames_run = run_to_completion(client, degradation=DARKNESS)

    body = results(client, benchmark["experiment_id"])

    (row,) = body["synthetic"]
    assert row["experiment_id"] == frames_run["experiment_id"]
    assert row["title"] == "Darkness 0.60"
    assert row["condition"] == "clear-day"
    assert (row["map"], row["objects"], row["frames"], row["low_n"]) == (0.0, 2, 1, True)
    assert class_row(row, "PassengerCar")["ap"] == 0.0
    # The real conditions are unchanged.
    assert len(body["conditions"]) == 8


def test_a_run_on_another_manifest_is_not_a_row(tmp_path, root):
    client = make_client(tmp_path, root, StubRunner())
    benchmark = run_benchmark(client)
    run_to_completion(client, manifest=subset_manifest(client, seed=3))

    assert results(client, benchmark["experiment_id"])["synthetic"] == []


def test_the_row_is_scored_at_the_benchmarks_display_threshold(tmp_path, root):
    client = make_client(tmp_path, root, StubRunner())
    benchmark = run_benchmark(client)
    run_to_completion(client)

    low = class_row(results(client, benchmark["experiment_id"], 0.25)["synthetic"][0], "Pedestrian")
    high = class_row(results(client, benchmark["experiment_id"], 0.5)["synthetic"][0], "Pedestrian")

    assert (low["predictions"], high["predictions"]) == (1, 0)


# --- refused starts and lookups ---------------------------------------------------------------------------


@pytest.mark.parametrize("condition_name", ["fog-day", "rain-night", "clear", "sunny"])
def test_only_clear_frames_can_be_degraded(tmp_path, root, condition_name):
    client = make_client(tmp_path, root, StubRunner())
    body = {"manifest": subset_manifest(client), "condition": condition_name, "degradation": FOG}

    assert client.post("/api/synthetic-frames/jobs", json=body).status_code == 422


def test_a_manifest_with_no_frames_in_the_condition_is_refused_in_plain_language(tmp_path, root):
    client = make_client(tmp_path, root, StubRunner())
    manifest = subset_manifest(client)
    manifest["frames"]["clear-day"] = []
    body = {"manifest": manifest, "condition": "clear-day", "degradation": FOG}

    response = client.post("/api/synthetic-frames/jobs", json=body)

    assert response.status_code == 422
    assert "no Clear · day frames" in response.json()["detail"]


def test_a_manifest_is_checked_like_a_benchmarks(tmp_path, root):
    client = make_client(tmp_path, root, StubRunner())
    manifest = {**subset_manifest(client), "vocabulary_version": 99}
    body = {"manifest": manifest, "condition": "clear-day", "degradation": FOG}

    response = client.post("/api/synthetic-frames/jobs", json=body)

    assert response.status_code == 422
    assert "vocabulary version 99" in response.json()["detail"]


def test_a_second_degradation_cannot_ride_along(tmp_path, root):
    client = make_client(tmp_path, root, StubRunner())
    body = {"manifest": subset_manifest(client), "condition": "clear-day", "degradation": FOG, "extra": DARKNESS}

    assert client.post("/api/synthetic-frames/jobs", json=body).status_code == 422


def test_a_run_needs_a_ready_dataset(tmp_path, root):
    client = TestClient(create_app(static_dir=tmp_path / "no-dist", runner=StubRunner(), cache_dir=tmp_path / "c"))
    manifest = subset_manifest(make_client(tmp_path, root, StubRunner()))
    body = {"manifest": manifest, "condition": "clear-day", "degradation": FOG}

    response = client.post("/api/synthetic-frames/jobs", json=body)

    assert response.status_code == 409


def test_a_run_needs_the_detector(tmp_path, root):
    client = make_client(tmp_path, root, None)
    body = {"manifest": subset_manifest(client), "condition": "clear-day", "degradation": FOG}

    response = client.post("/api/synthetic-frames/jobs", json=body)

    assert response.status_code == 503
    assert "fetch_model.py" in response.json()["detail"]


def test_unknown_results_are_404(tmp_path, root):
    client = make_client(tmp_path, root, StubRunner())
    benchmark = run_benchmark(client)

    for experiment_id in ("f" * 64, "..%5C..%5Cetc", benchmark["experiment_id"]):
        lookup = client.get(f"/api/synthetic-frames/experiments/{experiment_id}", params={"display_threshold": 0.5})
        assert lookup.status_code == 404
