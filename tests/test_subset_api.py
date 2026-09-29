"""Contract tests for the Subset table endpoint: a seeded manifest and per-condition counts from the fixture."""

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.conditions import CONDITIONS
from scripts.make_fixture_dataset import build_fixture_dataset


@pytest.fixture
def root(tmp_path):
    root = tmp_path / "SeeingThroughFog"
    build_fixture_dataset(root)
    return root


@pytest.fixture
def client(root, tmp_path):
    return TestClient(create_app(static_dir=tmp_path / "no-dist", dataset_root=root))


def test_default_subset_covers_every_condition(client):
    body = client.get("/api/dataset/subset").json()

    assert [row["condition"] for row in body["conditions"]] == list(CONDITIONS)
    assert all(row["frames"] == 1 for row in body["conditions"])
    assert body["manifest"]["seed"] == 0
    assert body["manifest"]["cap"] == 300
    assert body["manifest"]["vocabulary_version"] == 1
    assert body["manifest"]["frames"]["clear-day"] == ["2018-02-03_10-00-00_00100"]


def test_excluded_samples_are_counted_by_reason(client):
    body = client.get("/api/dataset/subset").json()

    assert body["excluded_total"] == 3
    assert body["excluded"] == {"fog with rain or snow": 1, "twilight": 1, "malformed label line": 1}
    assert any("line 2" in p for p in body["problems"])


def test_rows_report_objects_the_smallest_class_and_low_n(client):
    row = client.get("/api/dataset/subset").json()["conditions"][0]

    assert row == {
        "condition": "clear-day",
        "frames": 1,
        "objects": 2,
        "smallest_class": "LargeVehicle",
        "smallest_class_count": 0,
        "low_n": True,
    }
    assert client.get("/api/dataset/subset").json()["low_n_objects"] == 30


def test_seed_and_cap_are_recorded_in_the_manifest(client):
    manifest = client.get("/api/dataset/subset", params={"seed": 42, "cap": 5}).json()["manifest"]

    assert (manifest["seed"], manifest["cap"]) == (42, 5)


def test_the_same_request_gives_the_same_manifest(client):
    first = client.get("/api/dataset/subset", params={"seed": 3, "cap": 1}).json()["manifest"]

    assert client.get("/api/dataset/subset", params={"seed": 3, "cap": 1}).json()["manifest"] == first


@pytest.mark.parametrize("params", [{"cap": 0}, {"cap": -5}, {"seed": -1}, {"cap": "many"}])
def test_bad_seed_or_cap_is_rejected(client, params):
    assert client.get("/api/dataset/subset", params=params).status_code == 422


def test_subset_needs_a_ready_dataset(tmp_path):
    client = TestClient(create_app(static_dir=tmp_path / "no-dist"))

    response = client.get("/api/dataset/subset")

    assert response.status_code == 409
    assert "--dataset" in response.json()["detail"]


def test_a_missing_part_is_named(client, root):
    (root / "labeltool_labels_refined").rename(root.parent / "moved")

    response = client.get("/api/dataset/subset")

    assert response.status_code == 409
    assert "metadata" in response.json()["detail"].lower()
