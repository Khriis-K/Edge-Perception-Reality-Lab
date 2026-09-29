"""The generated fixture mimics SeeingThroughFog's layout, KITTI labels and metadata, with every case tests need."""

import json

import pytest

from scripts.make_fixture_dataset import build_fixture_dataset

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
WEATHERS = {"clear", "light_fog", "dense_fog", "rain", "snow"}


@pytest.fixture(scope="module")
def dataset(tmp_path_factory):
    root = tmp_path_factory.mktemp("fixture")
    ids = build_fixture_dataset(root)
    return root, ids


def metadata(root, sample_id):
    return json.loads((root / "labeltool_labels" / f"{sample_id}.json").read_text())


def label_lines(root, sample_id):
    return (root / "gt_labels" / "cam_left_labels_TMP" / f"{sample_id}.txt").read_text().splitlines()


def test_every_sample_has_an_image_labels_and_metadata(dataset):
    root, ids = dataset

    assert ids
    for sample_id in ids:
        assert (root / "cam_stereo_left_lut" / f"{sample_id}.png").read_bytes().startswith(PNG_SIGNATURE)
        assert label_lines(root, sample_id)
        assert metadata(root, sample_id)


def test_sample_ids_use_the_dataset_naming_scheme(dataset):
    _, ids = dataset

    for sample_id in ids:
        assert len(sample_id) == len("2018-02-12_15-39-23_00100")
        date, time, index = sample_id.split("_")
        assert date.count("-") == 2 and time.count("-") == 2 and index.isdigit()


def test_metadata_has_the_dataset_structure(dataset):
    root, ids = dataset

    for sample_id in ids:
        meta = metadata(root, sample_id)
        assert set(meta["weather"]) == WEATHERS
        assert set(meta["daytime"]) == {"day", "night"}
        assert {"environment", "illumination"} <= set(meta["meta"])


def test_covers_every_weather_in_day_and_night(dataset):
    root, ids = dataset
    seen = set()
    for sample_id in ids:
        meta = metadata(root, sample_id)
        weather = [w for w, on in meta["weather"].items() if on]
        light = [d for d, on in meta["daytime"].items() if on]
        if len(weather) == 1 and len(light) == 1:
            fog_or_other = "fog" if "fog" in weather[0] else weather[0]
            seen.add((fog_or_other, light[0]))

    assert seen >= {(w, d) for w in ["clear", "fog", "snow", "rain"] for d in ["day", "night"]}


def test_includes_a_sample_whose_weather_cannot_be_determined(dataset):
    root, ids = dataset

    assert any(not any(metadata(root, s)["weather"].values()) for s in ids)


def test_labels_cover_every_mapped_and_fallback_class(dataset):
    root, ids = dataset
    classes = {line.split()[0] for s in ids for line in label_lines(root, s)}

    assert {"PassengerCar", "LargeVehicle", "RidableVehicle", "Pedestrian", "Vehicle", "Obstacle"} <= classes


def test_well_formed_label_lines_are_kitti_with_numeric_2d_boxes(dataset):
    root, ids = dataset
    lines = [line for s in ids for line in label_lines(root, s)]
    well_formed = [line.split() for line in lines if len(line.split()) >= 15]

    assert well_formed
    for fields in well_formed:
        left, top, right, bottom = map(float, fields[4:8])
        assert left < right and top < bottom


def test_includes_exactly_one_malformed_label_line(dataset):
    root, ids = dataset
    lines = [line for s in ids for line in label_lines(root, s)]

    assert sum(1 for line in lines if len(line.split()) < 15) == 1


def test_generation_is_deterministic(tmp_path):
    first, second = tmp_path / "a", tmp_path / "b"
    build_fixture_dataset(first)
    build_fixture_dataset(second)

    files = sorted(p.relative_to(first) for p in first.rglob("*") if p.is_file())
    assert files == sorted(p.relative_to(second) for p in second.rglob("*") if p.is_file())
    for rel in files:
        assert (first / rel).read_bytes() == (second / rel).read_bytes()


def test_contains_only_the_three_parts_the_app_reads(dataset):
    root, _ = dataset

    assert sorted(p.name for p in root.iterdir()) == ["cam_stereo_left_lut", "gt_labels", "labeltool_labels"]
