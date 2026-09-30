"""The generated fixture mimics SeeingThroughFog's layout, KITTI labels and refined metadata, with every case tests need."""

import json

import pytest

from scripts.make_fixture_dataset import build_fixture_dataset

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
METADATA = "labeltool_labels_refined"


@pytest.fixture(scope="module")
def dataset(tmp_path_factory):
    root = tmp_path_factory.mktemp("fixture")
    ids = build_fixture_dataset(root)
    return root, ids


def metadata(root, sample_id):
    return json.loads((root / METADATA / f"{sample_id}.json").read_text())


def label_lines(root, sample_id):
    return (root / "gt_labels" / "cam_left_labels_TMP" / f"{sample_id}.txt").read_text().splitlines()


def weather(meta):
    """Hand-read of the refined flags, independent of the adapter: fog, rain, snow words that are set."""
    fog = [k for k, on in meta["fog"]["yes"].items() if on]
    rain = ["rain"] if meta["precipitation"]["yes"]["rain"] else []
    snow = [k for k, on in meta["precipitation"]["yes"]["snow"].items() if on]
    return fog, rain + snow


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


def test_metadata_has_the_refined_structure(dataset):
    root, ids = dataset

    for sample_id in ids:
        meta = metadata(root, sample_id)
        assert set(meta["fog"]) == {"no", "yes"}
        assert set(meta["fog"]["yes"]) == {"denseFog", "lightFog"}
        assert set(meta["precipitation"]["yes"]) == {"rain", "snow"}
        assert set(meta["precipitation"]["yes"]["snow"]) == {"heavySnow", "lightSnow"}
        assert set(meta["daytime"]) == {"day", "night"}
        assert isinstance(meta["twilight"], bool)


def test_no_and_yes_flags_agree(dataset):
    root, ids = dataset

    for sample_id in ids:
        meta = metadata(root, sample_id)
        fog, precipitation = weather(meta)
        assert meta["fog"]["no"] == (not fog)
        assert meta["precipitation"]["no"] == (not precipitation)


def test_covers_every_condition_in_day_and_night(dataset):
    root, ids = dataset
    seen = set()
    for sample_id in ids:
        meta = metadata(root, sample_id)
        fog, precipitation = weather(meta)
        light = [d for d, on in meta["daytime"].items() if on]
        if meta["twilight"] or (fog and precipitation):
            continue
        name = "fog" if fog else "rain" if precipitation == ["rain"] else "snow" if precipitation else "clear"
        seen.add((name, light[0]))

    assert seen == {(w, d) for w in ["clear", "fog", "snow", "rain"] for d in ["day", "night"]}


def test_covers_both_fog_words_and_both_snow_words(dataset):
    root, ids = dataset
    words = {w for s in ids for group in weather(metadata(root, s)) for w in group}

    assert {"denseFog", "lightFog", "heavySnow", "lightSnow", "rain"} <= words


def test_includes_a_fog_plus_snow_sample_and_a_twilight_sample(dataset):
    root, ids = dataset
    metas = [metadata(root, s) for s in ids]

    assert sum(1 for m in metas if all(weather(m))) == 1
    assert sum(1 for m in metas if m["twilight"]) == 1


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

    assert sorted(p.name for p in root.iterdir()) == ["cam_stereo_left_lut", "gt_labels", METADATA]
