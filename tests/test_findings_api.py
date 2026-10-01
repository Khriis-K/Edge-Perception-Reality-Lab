"""API contract tests for Findings: the runs it can open, each run's findings document (sim-to-real drops, the
condition-by-class heatmap, precision-recall curves, worst frames, the video reliability timeline, the run record and limitations), and the
user's headlines, stored with the run.

On the fixture dataset with the stub runner (see tests/test_benchmark_api.py): clear-day's car is a hit and its
pedestrian a miss (mAP 0.50 over 2 objects); fog-day's one RidableVehicle is missed (mAP 0.00 over 1 object). The stub
still finds the car through synthetic fog 0.6, so the synthetic side loses nothing.
"""

import pytest
from test_benchmark_api import make_client, root, subset_manifest  # noqa: F401 (root: fixture)
from test_benchmark_api import results as benchmark_results
from test_benchmark_api import run_to_completion as run_benchmark
from test_experiments_api import TERMINAL, wait_for
from test_experiments_api import make_client as make_video_client
from test_experiments_api import run_to_completion as run_video
from test_synthetic_frames_api import DARKNESS, FOG
from test_synthetic_frames_api import run_to_completion as run_synthetic_frames

from backend.stub_runner import StubRunner
from scripts.make_sample_video import FRAMES


def findings(client, experiment_id, display_threshold=0.25):
    response = client.get(f"/api/findings/{experiment_id}", params={"display_threshold": display_threshold})
    assert response.status_code == 200, response.text
    return response.json()


def drop(comparison, name):
    return next(c for c in comparison["classes"] if c["class_name"] == name)


@pytest.fixture
def client(tmp_path, root):
    return make_client(tmp_path, root, StubRunner())


# --- sim-to-real ------------------------------------------------------------------------------------------


def test_sim_to_real_sets_clear_day_beside_synthetic_fog_on_it_and_real_fog_by_day(client):
    benchmark = run_benchmark(client)
    fog = run_synthetic_frames(client, degradation=FOG)

    sim = findings(client, benchmark["experiment_id"])["sim_to_real"]

    assert sim["reference"] == {"condition": "clear-day", "map": 0.5, "objects": 2, "frames": 1, "low_n": True}
    real = sim["real"]
    assert (real["condition"], real["experiment_id"]) == ("fog-day", None)
    assert (real["map"], real["objects"], real["frames"]) == (0.0, 1, 1)
    assert real["map_drop"] == 0.5
    [synthetic] = sim["synthetic"]
    assert synthetic["experiment_id"] == fog["experiment_id"]
    assert synthetic["title"] == "Synthetic fog 0.60"
    assert (synthetic["condition"], synthetic["map"], synthetic["objects"]) == ("clear-day", 0.5, 2)
    assert synthetic["map_drop"] == 0.0


def test_per_class_drops_pair_the_same_class_on_both_sides_and_are_undefined_without_ap(client):
    benchmark = run_benchmark(client)
    run_synthetic_frames(client, degradation=FOG)

    sim = findings(client, benchmark["experiment_id"])["sim_to_real"]
    synthetic, real = sim["synthetic"][0], sim["real"]

    car = drop(synthetic, "PassengerCar")
    assert (car["reference_ap"], car["ap"], car["drop"]) == (1.0, 1.0, 0.0)
    assert (car["reference_objects"], car["objects"], car["low_n"]) == (1, 1, True)
    # Fog-day has no cars, so its car AP, and the drop to it, are undefined: never a flattering 0.
    real_car = drop(real, "PassengerCar")
    assert (real_car["reference_ap"], real_car["ap"], real_car["drop"]) == (1.0, None, None)
    assert real_car["objects"] == 0
    ridable = drop(real, "RidableVehicle")
    assert (ridable["reference_ap"], ridable["ap"], ridable["drop"]) == (None, 0.0, None)


def test_sim_to_real_shares_the_benchmarks_metric_definitions(client):
    benchmark = run_benchmark(client)
    run_synthetic_frames(client, degradation=FOG)
    scored = benchmark_results(client, benchmark["experiment_id"])

    sim = findings(client, benchmark["experiment_id"])["sim_to_real"]

    by_condition = {c["condition"]: c for c in scored["conditions"]}
    [synthetic_row] = scored["synthetic"]
    for side, row in ((sim["real"], by_condition["fog-day"]), (sim["synthetic"][0], synthetic_row)):
        assert side["map"] == row["map"]
        assert [(c["class_name"], c["ap"], c["objects"]) for c in side["classes"]] == [
            (c["class_name"], c["ap"], c["objects"]) for c in row["classes"]
        ]
    assert sim["reference"]["map"] == by_condition["clear-day"]["map"]


def test_only_synthetic_fog_on_clear_day_frames_counts_as_the_simulation(client):
    benchmark = run_benchmark(client)
    run_synthetic_frames(client, degradation=DARKNESS)
    run_synthetic_frames(client, degradation=FOG, condition_name="clear-night")

    assert findings(client, benchmark["experiment_id"])["sim_to_real"]["synthetic"] == []


def test_without_clear_day_frames_there_is_nothing_to_compare(client):
    manifest = subset_manifest(client)
    manifest["frames"]["clear-day"] = []
    benchmark = run_benchmark(client, manifest)

    sim = findings(client, benchmark["experiment_id"])["sim_to_real"]

    assert sim == {"reference": None, "real": None, "synthetic": []}


# --- precision-recall -------------------------------------------------------------------------------------


def curve(side, name):
    return next(c for c in side["classes"] if c["class_name"] == name)


def test_pr_curves_set_clear_day_beside_synthetic_fog_and_real_fog_with_hand_checked_points(client):
    benchmark = run_benchmark(client)
    fog = run_synthetic_frames(client, degradation=FOG)

    curves = findings(client, benchmark["experiment_id"])["pr_curves"]

    reference = curves["reference"]
    assert (reference["title"], reference["condition"], reference["experiment_id"]) == ("Clear · day", "clear-day", None)
    # Clear-day: the stub's car (0.9) is the one car's hit; its person (0.3) misses the one pedestrian.
    car = curve(reference, "PassengerCar")
    assert car["pr_curve"] == [{"threshold": 0.9, "precision": 1.0, "recall": 1.0}]
    assert (car["ap"], car["objects"], car["precision"], car["recall"]) == (1.0, 1, 1.0, 1.0)
    pedestrian = curve(reference, "Pedestrian")
    assert pedestrian["pr_curve"] == [{"threshold": 0.3, "precision": 0.0, "recall": 0.0}]
    assert (pedestrian["precision"], pedestrian["recall"]) == (0.0, 0.0)
    [synthetic] = curves["synthetic"]
    assert (synthetic["title"], synthetic["experiment_id"]) == ("Synthetic fog 0.60", fog["experiment_id"])
    assert curve(synthetic, "PassengerCar")["pr_curve"] == car["pr_curve"]
    # Fog-day: nothing is predicted, so its one RidableVehicle has AP 0 and no curve at all.
    real = curves["real"]
    assert (real["title"], real["condition"], real["experiment_id"]) == ("Real fog · day", "fog-day", None)
    ridable = curve(real, "RidableVehicle")
    assert (ridable["pr_curve"], ridable["ap"], ridable["objects"]) == ([], 0.0, 1)


def test_pr_curves_are_the_benchmarks_own_and_mark_the_display_threshold(client):
    benchmark = run_benchmark(client)
    scored = benchmark_results(client, benchmark["experiment_id"], display_threshold=0.5)

    curves = findings(client, benchmark["experiment_id"], display_threshold=0.5)["pr_curves"]

    clear_day = next(c for c in scored["conditions"] if c["condition"] == "clear-day")
    assert curves["reference"]["classes"] == clear_day["classes"]
    # At 0.5 the person (0.3) is no longer shown: no precision to mark, and recall stays 0.
    pedestrian = curve(curves["reference"], "Pedestrian")
    assert (pedestrian["precision"], pedestrian["recall"]) == (None, 0.0)
    assert pedestrian["pr_curve"] == [{"threshold": 0.3, "precision": 0.0, "recall": 0.0}]


def test_without_clear_day_frames_there_are_no_curves_to_overlay(client):
    manifest = subset_manifest(client)
    manifest["frames"]["clear-day"] = []
    benchmark = run_benchmark(client, manifest)

    curves = findings(client, benchmark["experiment_id"])["pr_curves"]

    assert curves == {"reference": None, "real": None, "synthetic": []}


# --- where it fails: the condition-by-class heatmap ------------------------------------------------------


def test_the_heatmap_has_a_row_per_condition_with_day_and_night_apart_and_low_n_cells(client):
    benchmark = run_benchmark(client)

    rows = findings(client, benchmark["experiment_id"])["conditions"]

    assert [r["condition"] for r in rows] == [
        "clear-day", "clear-night", "fog-day", "fog-night", "snow-day", "snow-night", "rain-day", "rain-night",
    ]  # fmt: skip
    clear_day = rows[0]
    assert (clear_day["map"], clear_day["objects"], clear_day["frames"], clear_day["low_n"]) == (0.5, 2, 1, True)
    assert [c["class_name"] for c in clear_day["cells"]] == [
        "PassengerCar", "LargeVehicle", "RidableVehicle", "Pedestrian"
    ]  # fmt: skip
    car = clear_day["cells"][0]
    assert (car["ap"], car["objects"], car["frames"], car["low_n"]) == (1.0, 1, 1, True)
    # A class with no objects has no AP: an empty cell, not a 0.
    assert clear_day["cells"][2]["ap"] is None
    assert clear_day["cells"][2]["objects"] == 0


# --- worst frames -----------------------------------------------------------------------------------------


def test_worst_frames_rank_every_conditions_frames_by_error_score_with_their_counts(client):
    benchmark = run_benchmark(client)

    worst = findings(client, benchmark["experiment_id"])["worst_frames"]

    # Snow-day: the car on its LargeVehicle is a confusion, the stub's person a false alarm, its pedestrian missed.
    first = worst[0]
    assert (first["id"], first["condition"], first["score"]) == ("2018-02-06_10-00-00_00400", "snow-day", 3.0)
    assert (first["misses"], first["false_alarms"], first["class_confusions"], first["hits"]) == (1, 1, 1, 0)
    # Ties keep vocabulary order: clear-day before clear-night.
    assert [(f["condition"], f["score"]) for f in worst[1:3]] == [("clear-day", 2.0), ("clear-night", 2.0)]
    assert [f["score"] for f in worst] == sorted((f["score"] for f in worst), reverse=True)
    # Fog-night's person is forgiven by its ignore region and its car is a hit: a frame with no errors isn't "worst".
    assert "fog-night" not in {f["condition"] for f in worst}
    assert len(worst) <= 6


def test_worst_frames_are_scored_at_the_display_threshold(client):
    benchmark = run_benchmark(client)

    # Above the stub person's 0.3, clear-day keeps only its missed pedestrian.
    worst = findings(client, benchmark["experiment_id"], display_threshold=0.5)["worst_frames"]

    clear_day = next(f for f in worst if f["condition"] == "clear-day")
    assert (clear_day["score"], clear_day["false_alarms"], clear_day["misses"]) == (1.0, 0, 1)


# --- the inspector: run record, latency, limitations ------------------------------------------------------


def test_a_benchmark_runs_record_names_its_frames_objects_manifest_model_mapping_and_match_iou(client):
    manifest = subset_manifest(client)
    benchmark = run_benchmark(client, manifest)

    body = findings(client, benchmark["experiment_id"])

    assert body["kind"] == "benchmark"
    record = body["record"]
    assert (record["frames"], record["objects"]) == (8, 10)
    assert record["manifest"] == manifest
    assert record["model"]["name"] == "Stub detector"
    assert record["match_iou"] == 0.5
    assert record["confidence_floor"] == 0.05
    assert record["class_mapping"] == client.get("/api/benchmark/class-mapping").json()


def test_a_benchmark_run_records_its_latency_with_the_warm_up_left_out(client):
    benchmark = run_benchmark(client)

    latency = findings(client, benchmark["experiment_id"])["latency"]

    assert latency["warmup_frames"] == 2
    assert latency["frames"] == 6  # the fixture's 8 frames, less the warm-up
    assert latency["inference_runs"] == 6
    assert latency["inference"]["p50_ms"] >= 0
    assert latency["effective_fps"] is None or latency["effective_fps"] > 0
    # A Benchmark run degrades and renders nothing: those stages are absent, not 0 ms.
    assert latency["degrade"] is None
    assert latency["render"] is None


def test_read_this_first_states_the_sim_to_real_caveat_and_the_limits_of_the_result(client):
    benchmark = run_benchmark(client)

    limitations = " ".join(findings(client, benchmark["experiment_id"])["limitations"])

    assert "distributional, not paired" in limitations
    assert "daytime" in limitations
    assert "low n" in limitations
    assert "not been validated for safety-critical" in limitations


# --- video runs -------------------------------------------------------------------------------------------


@pytest.fixture
def video_client(tmp_path):
    return make_video_client(tmp_path, StubRunner())


def test_a_video_run_has_a_reliability_timeline_with_every_frames_stability_counts(video_client):
    job = run_video(video_client)

    body = findings(video_client, job["experiment_id"])

    assert body["kind"] == "video"
    stability = video_client.get(f"/api/experiments/{job['experiment_id']}/stability").json()
    assert [p["index"] for p in body["timeline"]] == list(range(FRAMES))
    assert [
        (p["score"], p["dropped"], p["introduced"], p["class_changes"], p["confidence_loss"]) for p in body["timeline"]
    ] == [(f["score"], f["dropped"], f["introduced"], f["class_changes"], f["confidence_loss"]) for f in stability["frames"]]
    assert "sim_to_real" not in body and "conditions" not in body


def test_a_benchmark_run_has_no_reliability_timeline(client):
    benchmark = run_benchmark(client)

    assert "timeline" not in findings(client, benchmark["experiment_id"])


def test_a_video_runs_worst_frames_are_its_highest_stability_scores(video_client):
    job = run_video(video_client)

    body = findings(video_client, job["experiment_id"])

    worst = body["worst_frames"]
    assert len(worst) <= 6
    assert all(f["score"] > 0 for f in worst)
    scores = sorted((p["score"] for p in body["timeline"] if p["score"] > 0), reverse=True)
    assert [f["score"] for f in worst] == scores[:6]


def test_a_video_runs_record_latency_and_limitations(video_client):
    job = run_video(video_client)

    body = findings(video_client, job["experiment_id"])

    record = body["record"]
    assert record["sample_id"] == "synthetic-traffic"
    assert record["frames"] == FRAMES
    assert record["degradation"]["kind"] == "blur"
    assert record["model"]["name"] == "Stub detector"
    assert record["match_iou"] == 0.5
    assert record["stability_threshold"] == 0.25
    assert body["latency"]["frames"] == FRAMES - 2
    limitations = " ".join(body["limitations"])
    assert "not accuracy" in limitations
    assert "not been validated for safety-critical" in limitations


# --- which runs Findings can open -------------------------------------------------------------------------


def test_findings_lists_benchmark_and_video_runs_newest_first_but_not_runs_on_clear_frames(tmp_path, root):
    client = make_client(tmp_path, root, StubRunner())
    video = run_video(client)
    benchmark = run_benchmark(client)
    run_synthetic_frames(client, degradation=FOG)

    runs = client.get("/api/findings").json()

    assert [(r["id"], r["kind"]) for r in runs] == [
        (benchmark["experiment_id"], "benchmark"),
        (video["experiment_id"], "video"),
    ]
    assert runs[0]["title"] == "Benchmark: seed 0, up to 300 frames per condition"
    assert runs[1]["title"] == "Gaussian blur 0.10 on Synthetic traffic (generated)"
    assert all(r["saved_at"] for r in runs)


def test_an_unknown_run_has_no_findings(client):
    assert client.get("/api/findings/" + "0" * 64, params={"display_threshold": 0.25}).status_code == 404
    assert client.get("/api/findings/not-an-id", params={"display_threshold": 0.25}).status_code == 404


# --- headlines --------------------------------------------------------------------------------------------


def put_headline(client, experiment_id, key, text):
    return client.put(f"/api/findings/{experiment_id}/headlines/{key}", json={"text": text})


def test_a_new_run_has_no_headlines_nothing_writes_one_for_the_user(client):
    benchmark = run_benchmark(client)
    run_synthetic_frames(client, degradation=FOG)

    assert findings(client, benchmark["experiment_id"])["headlines"] == {}


def test_a_headline_the_user_writes_is_stored_with_the_run_and_survives_a_restart(tmp_path, root):
    client = make_client(tmp_path, root, StubRunner())
    benchmark = run_benchmark(client)

    response = put_headline(client, benchmark["experiment_id"], "sim-to-real", "  Synthetic fog costs less than real fog.  ")

    assert response.status_code == 200, response.text
    assert response.json() == {"sim-to-real": "Synthetic fog costs less than real fog."}
    restarted = make_client(tmp_path, root, StubRunner())  # same cache folder, a fresh app
    assert findings(restarted, benchmark["experiment_id"])["headlines"] == {
        "sim-to-real": "Synthetic fog costs less than real fog."
    }


def test_each_finding_keeps_its_own_headline_and_a_blank_one_clears_it(client):
    benchmark = run_benchmark(client)
    experiment_id = benchmark["experiment_id"]
    put_headline(client, experiment_id, "sim-to-real", "One.")
    put_headline(client, experiment_id, "where-it-fails", "Two.")

    response = put_headline(client, experiment_id, "sim-to-real", "   ")

    assert response.json() == {"where-it-fails": "Two."}
    assert findings(client, experiment_id)["headlines"] == {"where-it-fails": "Two."}


def test_a_benchmark_run_takes_a_precision_recall_headline(client):
    benchmark = run_benchmark(client)

    response = put_headline(client, benchmark["experiment_id"], "precision-recall", "Real fog caps recall.")

    assert response.status_code == 200, response.text
    assert findings(client, benchmark["experiment_id"])["headlines"] == {"precision-recall": "Real fog caps recall."}


def test_a_video_run_takes_a_timeline_headline_but_not_a_benchmark_one(video_client):
    job = run_video(video_client)

    assert put_headline(video_client, job["experiment_id"], "reliability-timeline", "Blur barely moves it.").status_code == 200
    assert put_headline(video_client, job["experiment_id"], "sim-to-real", "No.").status_code == 422
    assert findings(video_client, job["experiment_id"])["headlines"] == {"reliability-timeline": "Blur barely moves it."}


@pytest.mark.parametrize(
    ("key", "text", "status"),
    [
        ("reliability-timeline", "A benchmark has no timeline.", 422),
        ("made-up", "No such finding.", 422),
        ("sim-to-real", "x" * 501, 422),
    ],
)
def test_headlines_are_refused_for_findings_the_run_lacks_and_past_one_sentence(client, key, text, status):
    benchmark = run_benchmark(client)

    assert put_headline(client, benchmark["experiment_id"], key, text).status_code == status
    assert findings(client, benchmark["experiment_id"])["headlines"] == {}


def test_a_headline_for_an_unknown_run_is_404(client):
    assert put_headline(client, "0" * 64, "sim-to-real", "Nothing to attach it to.").status_code == 404
    assert put_headline(client, "not-an-id", "sim-to-real", "Not a path.").status_code == 404
