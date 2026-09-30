"""Contract test for the class-mapping endpoint that Setup, Findings and Report show."""

from fastapi.testclient import TestClient

from backend.app import create_app


def test_class_mapping_is_served_without_a_dataset(tmp_path):
    client = TestClient(create_app(static_dir=tmp_path / "no-dist"))

    response = client.get("/api/benchmark/class-mapping")

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == 1
    assert body["mapping"] == [
        {"coco": "car", "dataset_class": "PassengerCar"},
        {"coco": "truck", "dataset_class": "LargeVehicle"},
        {"coco": "bus", "dataset_class": "LargeVehicle"},
        {"coco": "bicycle", "dataset_class": "RidableVehicle"},
        {"coco": "motorcycle", "dataset_class": "RidableVehicle"},
        {"coco": "person", "dataset_class": "Pedestrian"},
    ]
    assert body["ignore_labels"] == ["Vehicle", "Obstacle", "DontCare", "*_is_group"]
    assert "neither hits nor misses" in body["ignore_rule"]
    assert "excluded" in body["unmapped_rule"]
