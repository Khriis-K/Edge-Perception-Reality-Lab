"""API contract tests for the experiment cache: reusing finished runs, previewing reuse, and run history."""

import shutil

import pytest
from test_experiments_api import (
    DEGRADATION,
    RUN,
    SAMPLE,
    TERMINAL,
    FailingRunner,
    GatedRunner,
    make_client,
    run_to_completion,
    start,
    wait_for,
)

from backend.stub_runner import StubRunner
from scripts.make_sample_video import FRAMES

OTHER_RUN = {**RUN, "degradation": {**DEGRADATION, "severity": 0.2}}


def open_runner():
    runner = GatedRunner()
    runner.open()
    return runner


# --- reuse ------------------------------------------------------------------------------


def test_an_identical_run_reuses_the_cached_results_without_inference(tmp_path):
    runner = open_runner()
    client = make_client(tmp_path, runner)
    first = run_to_completion(client)
    calls = runner.calls

    response = client.post("/api/jobs", json=RUN)

    assert response.status_code == 200
    job = response.json()
    assert job["cached"] is True
    assert job["status"] == "completed"
    assert job["experiment_id"] == first["experiment_id"]
    assert job["frames_done"] == job["frames_total"] == FRAMES
    assert job["progress"] == 1.0
    assert runner.calls == calls
    assert first["cached"] is False


def test_cached_results_survive_a_restart(tmp_path):
    first = run_to_completion(make_client(tmp_path, StubRunner()))

    # A new app on the same cache folder, with a detector that would fail if it ran.
    client = make_client(tmp_path, FailingRunner())
    job = client.post("/api/jobs", json=RUN).json()

    assert job["cached"] is True
    assert job["experiment_id"] == first["experiment_id"]
    assert client.get(f"/api/jobs/{job['id']}").json()["status"] == "completed"
    assert client.get(f"/api/experiments/{job['experiment_id']}").json()["frames"][FRAMES - 1]["index"] == FRAMES - 1
    assert client.get(f"/api/experiments/{job['experiment_id']}/stability").status_code == 200
    assert client.get(f"/api/experiments/{job['experiment_id']}/frames/degraded/0").status_code == 200


def test_changing_a_setting_starts_a_new_job(tmp_path):
    client = make_client(tmp_path, StubRunner())
    first = run_to_completion(client)

    response = client.post("/api/jobs", json=OTHER_RUN)

    assert response.status_code == 202
    assert response.json()["cached"] is False
    assert response.json()["experiment_id"] != first["experiment_id"]


def test_an_identical_run_started_while_one_is_running_joins_it(tmp_path):
    runner = GatedRunner()
    client = make_client(tmp_path, runner)
    first = start(client)

    second = client.post("/api/jobs", json=RUN)

    assert second.status_code == 202
    assert second.json()["id"] == first["id"]
    runner.open()
    wait_for(client, first["id"], lambda j: j["status"] in TERMINAL)


# --- incomplete runs are never cached ------------------------------------------------------


def test_a_cancelled_run_is_not_reused(tmp_path):
    runner = GatedRunner()
    client = make_client(tmp_path, runner)
    job = start(client)
    wait_for(client, job["id"], lambda j: j["status"] == "running")
    client.post(f"/api/jobs/{job['id']}/cancel")
    runner.open()
    wait_for(client, job["id"], lambda j: j["status"] in TERMINAL)

    again = client.post("/api/jobs", json=RUN)

    assert again.status_code == 202
    assert again.json()["cached"] is False
    assert again.json()["id"] != job["id"]
    wait_for(client, again.json()["id"], lambda j: j["status"] in TERMINAL)


def test_starting_again_while_a_cancel_is_pending_starts_a_fresh_run(tmp_path):
    runner = GatedRunner()
    client = make_client(tmp_path, runner)
    first = start(client)
    wait_for(client, first["id"], lambda j: j["status"] == "running")
    client.post(f"/api/jobs/{first['id']}/cancel")  # the worker has not seen it yet: it is still "running"

    second = client.post("/api/jobs", json=RUN).json()
    runner.open()

    assert second["id"] != first["id"]
    assert wait_for(client, first["id"], lambda j: j["status"] in TERMINAL)["status"] == "cancelled"
    assert wait_for(client, second["id"], lambda j: j["status"] in TERMINAL)["status"] == "completed"
    # The cancelled job cleaned up only its own staging folder: the fresh run's entry is whole.
    experiment = client.get(f"/api/experiments/{second['experiment_id']}").json()
    assert len(experiment["frames"]) == FRAMES
    assert client.get(f"/api/experiments/{second['experiment_id']}/frames/clean/{FRAMES - 1}").status_code == 200


def test_deleting_the_cache_mid_run_fails_the_run_instead_of_caching_a_partial_one(tmp_path):
    runner = GatedRunner()
    client = make_client(tmp_path, runner)
    job = start(client)
    runner.allow(2 * 5)
    wait_for(client, job["id"], lambda j: j["frames_done"] == 5)
    shutil.rmtree(tmp_path / "cache")
    runner.open()

    final = wait_for(client, job["id"], lambda j: j["status"] in TERMINAL)

    assert final["status"] == "failed"
    assert client.get(f"/api/experiments/{job['experiment_id']}").status_code == 404
    assert client.get("/api/experiments").json() == []


def test_a_failed_run_is_not_listed_or_reused(tmp_path):
    client = make_client(tmp_path, FailingRunner())
    assert run_to_completion(client)["status"] == "failed"

    assert client.get("/api/experiments").json() == []
    assert client.post("/api/jobs/preview", json=RUN).json()["cached"] is False


# --- preview ----------------------------------------------------------------------------------


def test_preview_reports_whether_a_run_will_reuse_the_cache_without_starting_one(tmp_path):
    runner = open_runner()
    client = make_client(tmp_path, runner)

    before = client.post("/api/jobs/preview", json=RUN)
    assert before.status_code == 200
    assert before.json()["cached"] is False
    assert runner.calls == 0

    job = run_to_completion(client)
    after = client.post("/api/jobs/preview", json=RUN).json()

    assert after == {"experiment_id": job["experiment_id"], "cached": True}
    assert before.json()["experiment_id"] == job["experiment_id"]
    assert client.post("/api/jobs/preview", json=OTHER_RUN).json()["cached"] is False


def test_preview_validates_like_a_run_request(client):
    assert client.post("/api/jobs/preview", json={**RUN, "sample_id": "nope"}).status_code == 422


def test_preview_without_model_weights_explains_how_to_fetch_them(tmp_path):
    response = make_client(tmp_path, runner=None).post("/api/jobs/preview", json=RUN)

    assert response.status_code == 503
    assert "scripts/fetch_model.py" in response.json()["detail"]


# --- history ----------------------------------------------------------------------------------


def test_history_lists_completed_runs_newest_first_without_paths(tmp_path):
    client = make_client(tmp_path, StubRunner())
    assert client.get("/api/experiments").json() == []
    first = run_to_completion(client)
    second = client.post("/api/jobs", json=OTHER_RUN).json()
    wait_for(client, second["id"], lambda j: j["status"] in TERMINAL)

    runs = client.get("/api/experiments").json()

    assert [run["id"] for run in runs] == [second["experiment_id"], first["experiment_id"]]
    newest = runs[0]
    assert newest["sample_id"] == SAMPLE
    assert newest["sample_title"] == "Synthetic traffic (generated)"
    assert newest["degradation"]["kind"] == "blur"
    assert newest["degradation"]["severity"] == 0.2
    assert newest["degradation"]["parameters"]
    assert newest["model"] == StubRunner().info.model_dump()
    assert newest["frame_count"] == FRAMES
    assert newest["saved_at"] >= runs[1]["saved_at"]
    assert "frames" not in newest
    assert not any("path" in key or "dir" in key for key in newest)


def test_history_is_read_from_the_cache_folder(tmp_path):
    job = run_to_completion(make_client(tmp_path, StubRunner()))

    runs = make_client(tmp_path, runner=None).get("/api/experiments").json()

    assert [run["id"] for run in runs] == [job["experiment_id"]]


def test_a_run_deleted_from_the_cache_by_hand_disappears(tmp_path):
    client = make_client(tmp_path, StubRunner())
    job = run_to_completion(client)
    shutil.rmtree(tmp_path / "cache" / job["experiment_id"])

    assert client.get("/api/experiments").json() == []
    assert client.get(f"/api/experiments/{job['experiment_id']}").status_code == 404
    assert client.post("/api/jobs", json=RUN).status_code == 202


def test_cache_info_reports_the_folder_and_its_size(tmp_path):
    client = make_client(tmp_path, StubRunner())
    empty = client.get("/api/cache").json()
    assert empty == {"folder": str((tmp_path / "cache").resolve()), "size_bytes": 0}

    run_to_completion(client)

    assert client.get("/api/cache").json()["size_bytes"] > 0


# --- confined to the cache ------------------------------------------------------------------


@pytest.mark.parametrize(
    "experiment_id",
    ["..", "..%2foutside", "..%5coutside", "%2e%2e%5coutside", "outside", "0" * 64],
    ids=["dot-dot", "slash", "backslash", "encoded-backslash", "sibling", "unknown"],
)
def test_path_traversal_out_of_the_cache_is_rejected(tmp_path, experiment_id):
    client = make_client(tmp_path, StubRunner())
    job = run_to_completion(client)
    # A complete entry outside the cache, reachable as cache/..\outside on Windows if ids were not checked.
    outside = tmp_path / "outside"
    shutil.copytree(tmp_path / "cache" / job["experiment_id"], outside)
    (outside / "frames" / "clean" / "0.jpg").write_text("outside the cache")

    for url in [f"/api/experiments/{experiment_id}", f"/api/experiments/{experiment_id}/frames/clean/0"]:
        response = client.get(url)
        assert response.status_code == 404, url
        assert "outside the cache" not in response.text


def test_cache_endpoints_are_in_the_openapi_schema(client):
    paths = client.get("/openapi.json").json()["paths"]

    for path in ["/api/jobs/preview", "/api/experiments", "/api/cache"]:
        assert path in paths


@pytest.fixture
def client(tmp_path):
    return make_client(tmp_path, StubRunner())
