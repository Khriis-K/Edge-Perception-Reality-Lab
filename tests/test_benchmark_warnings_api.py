"""A Benchmark run records a warning for frames whose only detections are classes outside the class mapping."""

from fastapi.testclient import TestClient
from test_experiments_api import TERMINAL, wait_for

from backend.app import create_app
from backend.detection import Box, Detection
from backend.stub_runner import StubRunner
from scripts.make_fixture_dataset import build_fixture_dataset

CLEAR_DAY = "2018-02-03_10-00-00_00100"


class TrafficLightRunner(StubRunner):
    """Sees only a traffic light, a COCO class with no dataset counterpart."""

    def detect(self, image, confidence_threshold):
        return [Detection(label="traffic light", confidence=0.8, box=Box(x1=0.1, y1=0.1, x2=0.2, y2=0.2))]


def test_frames_with_only_unmapped_detections_are_recorded_as_a_warning(tmp_path):
    root = tmp_path / "SeeingThroughFog"
    build_fixture_dataset(root)
    app = create_app(static_dir=tmp_path / "no-dist", runner=TrafficLightRunner(), cache_dir=tmp_path / "cache", dataset_root=root)
    client = TestClient(app)
    manifest = client.get("/api/dataset/subset").json()["manifest"]

    job = client.post("/api/benchmark/jobs", json={"manifest": manifest}).json()
    done = wait_for(client, job["id"], lambda j: j["status"] in TERMINAL)
    body = client.get(f"/api/benchmark/experiments/{done['experiment_id']}", params={"display_threshold": 0.25}).json()

    [warning] = body["warnings"]
    assert "8 frames" in warning
    assert "outside the class mapping" in warning
    assert CLEAR_DAY in warning
    # The unmapped detections count for nothing: no false alarms, so no class has a precision.
    assert all(c["precision"] is None for row in body["conditions"] for c in row["classes"])
