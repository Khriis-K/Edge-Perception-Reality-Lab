"""The frame viewer's API: each condition's frame scores in the results, and one frame's overlays at every threshold.

On the fixture with the stub runner, the snow-day frame has one of each error: the stub's car lands on a LargeVehicle
(a class confusion), its stray person is a false alarm, and the Pedestrian is missed."""

from fastapi.testclient import TestClient
from test_benchmark_api import CLEAR_DAY, condition, make_client, results, root, run_to_completion  # noqa: F401
from test_experiments_api import GatedRunner

from backend.benchmark import BenchmarkFrame, GroundTruth
from backend.benchmark_run import frame_detail
from backend.detection import Box, Detection
from backend.stub_runner import StubRunner

SNOW_DAY = "2018-02-06_10-00-00_00400"


def frame(client: TestClient, experiment_id: str, frame_id: str):
    response = client.get(f"/api/benchmark/experiments/{experiment_id}/frames/{frame_id}")
    assert response.status_code == 200, response.text
    return response.json()


def level_at(levels, threshold):
    chosen = levels[0]
    for level in levels[1:]:
        if level["min_confidence"] >= threshold:
            chosen = level
    return chosen


def test_each_condition_lists_its_frames_scores_and_their_parts(tmp_path, root):
    client = make_client(tmp_path, root, StubRunner())
    job = run_to_completion(client)

    snow_day = condition(results(client, job["experiment_id"], display_threshold=0.25), "snow-day")

    assert snow_day["frame_scores"] == [
        {"id": SNOW_DAY, "hits": 0, "misses": 1, "false_alarms": 1, "class_confusions": 1, "ignored": 0, "score": 3.0}
    ]


def test_a_frame_holds_its_outcomes_at_every_threshold(tmp_path, root):
    client = make_client(tmp_path, root, StubRunner())
    job = run_to_completion(client)

    body = frame(client, job["experiment_id"], SNOW_DAY)

    assert body["id"] == SNOW_DAY
    assert body["condition"] == "snow-day"
    assert [(p["label"], p["confidence"]) for p in body["predictions"]] == [("PassengerCar", 0.9), ("Pedestrian", 0.3)]
    assert [(t["label"], t["role"]) for t in body["truths"]] == [("LargeVehicle", "object"), ("Pedestrian", "object")]
    assert body["weights"] == {"misses": 1.0, "false_alarms": 1.0, "class_confusions": 1.0}
    assert [level["min_confidence"] for level in body["levels"]] == [None, 0.9, 0.3]
    at_quarter = level_at(body["levels"], 0.25)
    assert sorted((m["outcome"], m["prediction"], m["truth"]) for m in at_quarter["matches"]) == [
        ("class_confusion", 0, 0),
        ("false_alarm", 1, None),
        ("miss", None, 1),
    ]
    assert at_quarter["score"]["score"] == 3.0
    # Above the person, only the confusion and the miss are left.
    assert level_at(body["levels"], 0.5)["score"]["score"] == 2.0


def test_reading_a_frame_never_runs_inference(tmp_path, root):
    runner = GatedRunner()
    runner.open()
    client = make_client(tmp_path, root, runner)
    job = run_to_completion(client)
    calls = runner.calls

    frame(client, job["experiment_id"], CLEAR_DAY)

    assert runner.calls == calls


def test_an_unknown_frame_or_benchmark_is_not_found(tmp_path, root):
    client = make_client(tmp_path, root, StubRunner())
    job = run_to_completion(client)

    assert client.get(f"/api/benchmark/experiments/{job['experiment_id']}/frames/nope").status_code == 404
    assert client.get(f"/api/benchmark/experiments/{'0' * 64}/frames/{CLEAR_DAY}").status_code == 404


def test_unmapped_detections_are_kept_apart_and_excluded_labels_are_marked():
    box = Box(x1=0.1, y1=0.1, x2=0.3, y2=0.5)
    raw = BenchmarkFrame(
        id="f",
        predictions=[Detection(label="cat", confidence=0.7, box=box), Detection(label="truck", confidence=0.6, box=box)],
        truths=[GroundTruth(label="train", box=box), GroundTruth(label="DontCare", box=box)],
    )

    detail = frame_detail("fog-day", raw)

    assert [(p.label, p.confidence) for p in detail.predictions] == [("LargeVehicle", 0.6)]
    assert [(p.label, p.confidence) for p in detail.unmapped] == [("cat", 0.7)]
    assert [t.role for t in detail.truths] == ["excluded", "ignore"]
