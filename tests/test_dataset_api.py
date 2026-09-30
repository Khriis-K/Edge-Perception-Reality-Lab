"""Contract tests for the dataset endpoints: status, re-check, and frame serving confined to the dataset."""

import shutil

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from scripts.make_fixture_dataset import build_fixture_dataset


@pytest.fixture
def root(tmp_path):
    root = tmp_path / "SeeingThroughFog"
    build_fixture_dataset(root)
    # Reachable as cam_stereo_left_lut/../../secret.png if sample ids were not checked.
    (tmp_path / "secret.png").write_text("outside the dataset")
    return root


@pytest.fixture
def client(root, tmp_path):
    return TestClient(create_app(static_dir=tmp_path / "no-dist", dataset_root=root))


def a_sample(root):
    return sorted((root / "cam_stereo_left_lut").iterdir())[0].stem


# --- status -------------------------------------------------------------------


def test_status_reports_ready_fixture(client, root):
    body = client.get("/api/dataset/status").json()

    assert body["configured"] and body["ready"]
    assert body["root"] == str(root.resolve())
    assert [p["key"] for p in body["parts"]] == ["camera", "labels", "metadata"]
    assert all(p["present"] for p in body["parts"])
    assert body["not_needed"]


def test_status_without_dataset_still_works(tmp_path):
    client = TestClient(create_app(static_dir=tmp_path / "no-dist"))

    body = client.get("/api/dataset/status").json()

    assert body["configured"] is False and body["ready"] is False
    assert body["root"] is None
    assert "--dataset" in body["message"]
    # The rest of the app is unaffected.
    assert client.get("/api/health").json() == {"status": "ok"}


def test_status_is_rechecked_on_every_request(client, root):
    moved = root.parent / "labeltool_labels_refined.bak"
    (root / "labeltool_labels_refined").rename(moved)

    missing = client.get("/api/dataset/status").json()
    assert not missing["ready"]
    assert "metadata" in missing["message"].lower()

    moved.rename(root / "labeltool_labels_refined")
    assert client.get("/api/dataset/status").json()["ready"]


def test_status_ignores_a_path_sent_by_the_browser(client, root, tmp_path):
    body = client.get("/api/dataset/status", params={"path": str(tmp_path), "root": str(tmp_path)}).json()

    assert body["root"] == str(root.resolve())


def test_no_endpoint_accepts_a_filesystem_path(client):
    schema = client.get("/openapi.json").json()

    for url, operations in schema["paths"].items():
        for method, operation in operations.items():
            names = [p["name"].lower() for p in operation.get("parameters", [])]
            assert not any(word in n for n in names for word in ("path", "dir", "folder", "root", "file")), (method, url)
            if url.startswith("/api/dataset"):
                assert "requestBody" not in operation, (method, url)


# --- frames -------------------------------------------------------------------


def test_serves_a_dataset_frame_by_sample_id(client, root):
    sample = a_sample(root)

    response = client.get(f"/api/dataset/frames/{sample}")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == (root / "cam_stereo_left_lut" / f"{sample}.png").read_bytes()


def test_unknown_frame_is_json_404(client):
    response = client.get("/api/dataset/frames/1999-01-01_00-00-00_00000")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")


@pytest.mark.parametrize(
    "url",
    [
        "/api/dataset/frames/..",
        "/api/dataset/frames/../../secret",
        "/api/dataset/frames/..%2f..%2fsecret",
        "/api/dataset/frames/..%5c..%5csecret",
        "/api/dataset/frames/%2e%2e%5c%2e%2e%5csecret",
        "/api/dataset/frames/secret",
    ],
)
def test_path_traversal_is_rejected(client, url):
    response = client.get(url)

    assert response.status_code in (400, 404, 422)
    assert "outside the dataset" not in response.text


def test_frames_need_a_configured_dataset(tmp_path):
    client = TestClient(create_app(static_dir=tmp_path / "no-dist"))

    response = client.get("/api/dataset/frames/2018-02-12_15-39-23_00100")

    assert response.status_code == 404
    assert "dataset" in response.json()["detail"].lower()


def test_removed_part_makes_frames_unavailable_without_restart(client, root):
    sample = a_sample(root)
    shutil.rmtree(root / "cam_stereo_left_lut")

    assert client.get(f"/api/dataset/frames/{sample}").status_code == 404
