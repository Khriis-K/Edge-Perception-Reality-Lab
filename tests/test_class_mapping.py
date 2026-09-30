"""The COCO-to-dataset class mapping and the ignore-region rule for ground-truth labels."""

import pytest

from backend.class_mapping import dataset_class, map_detections, truth_role
from backend.detection import Box, Detection

BOX = Box(x1=0.1, y1=0.2, x2=0.3, y2=0.4)


@pytest.mark.parametrize(
    "coco, expected",
    [
        ("car", "PassengerCar"),
        ("truck", "LargeVehicle"),
        ("bus", "LargeVehicle"),
        ("bicycle", "RidableVehicle"),
        ("motorcycle", "RidableVehicle"),
        ("person", "Pedestrian"),
        # No counterpart in the dataset: excluded from benchmark metrics.
        ("train", None),
        ("dog", None),
        ("traffic light", None),
        ("airplane", None),
        # A dataset class name is not a COCO label.
        ("PassengerCar", None),
        ("Car", None),
    ],
)
def test_dataset_class(coco, expected):
    assert dataset_class(coco) == expected


@pytest.mark.parametrize(
    "label, role",
    [
        ("PassengerCar", "object"),
        ("LargeVehicle", "object"),
        ("RidableVehicle", "object"),
        ("Pedestrian", "object"),
        # The dataset's fallback classes: ignore regions.
        ("Vehicle", "ignore"),
        ("Obstacle", "ignore"),
        # Regions the annotators marked as not to be scored, and crowds of one class.
        ("DontCare", "ignore"),
        ("Pedestrian_is_group", "ignore"),
        ("PassengerCar_is_group", "ignore"),
        ("RidableVehicle_is_group", "ignore"),
        # Stray labels outside the dataset's scheme: neither objects nor ignore regions.
        ("person", "excluded"),
        ("train", "excluded"),
        ("_is_group", "excluded"),
    ],
)
def test_truth_role(label, role):
    assert truth_role(label) == role


def test_map_detections_relabels_and_drops_unmapped():
    raw = [
        Detection(label="car", confidence=0.9, box=BOX),
        Detection(label="dog", confidence=0.8, box=BOX),
        Detection(label="bus", confidence=0.3, box=BOX),
    ]

    mapped = map_detections(raw)

    assert mapped == [
        Detection(label="PassengerCar", confidence=0.9, box=BOX),
        Detection(label="LargeVehicle", confidence=0.3, box=BOX),
    ]
    # The raw detections are kept as they were.
    assert [d.label for d in raw] == ["car", "dog", "bus"]
