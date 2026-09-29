"""Dataset adapter: readiness checks, frame lookup and the condition index, exercised against the generated fixture only."""

import shutil

import pytest

from backend.conditions import CONDITIONS
from backend.dataset import FrameNotFound, camera_image, check_readiness, index_dataset
from scripts.make_fixture_dataset import build_fixture_dataset


@pytest.fixture
def root(tmp_path):
    root = tmp_path / "SeeingThroughFog"
    build_fixture_dataset(root)
    return root


def part(status, key):
    return next(p for p in status.parts if p.key == key)


# --- readiness ----------------------------------------------------------------


def test_complete_fixture_is_ready(root):
    status = check_readiness(root)

    assert status.configured and status.ready
    assert [p.key for p in status.parts] == ["camera", "labels", "metadata"]
    assert all(p.present for p in status.parts)


def test_present_parts_report_how_many_files_were_found(root):
    count = len(list((root / "cam_stereo_left_lut").glob("*.png")))

    assert str(count) in part(check_readiness(root), "camera").message


@pytest.mark.parametrize(
    "key, folder, words",
    [
        ("camera", "cam_stereo_left_lut", "camera images"),
        ("labels", "gt_labels/cam_left_labels_TMP", "labels"),
        ("metadata", "labeltool_labels_refined", "metadata"),
    ],
)
def test_missing_part_is_named_in_plain_language(root, key, folder, words):
    shutil.rmtree(root / folder)

    status = check_readiness(root)
    missing = part(status, key)

    assert not status.ready
    assert not missing.present
    assert words in missing.message.lower()
    assert folder in missing.message  # tells the user which folder to extract
    assert str(root / folder) in missing.detail  # the exact path checked, for development
    assert words in status.message.lower()
    # The other parts are unaffected.
    assert all(p.present for p in status.parts if p.key != key)


def test_empty_part_folder_counts_as_missing(root):
    for image in (root / "cam_stereo_left_lut").iterdir():
        image.unlink()

    camera = part(check_readiness(root), "camera")

    assert not camera.present
    assert "empty" in camera.message.lower()
    assert ".png" in camera.message


def test_files_of_the_wrong_type_do_not_count(root):
    for image in (root / "cam_stereo_left_lut").iterdir():
        image.rename(image.with_suffix(".tiff"))

    assert not part(check_readiness(root), "camera").present


def test_metadata_left_zipped_says_to_extract_it(root):
    shutil.rmtree(root / "labeltool_labels_refined")
    (root / "labeltool_labels_refined.zip").write_bytes(b"PK")

    metadata = part(check_readiness(root), "metadata")

    assert not metadata.present
    assert "labeltool_labels_refined.zip" in metadata.message
    assert "extract" in metadata.message.lower()


def test_dataset_folder_that_does_not_exist(tmp_path):
    missing = tmp_path / "nowhere"

    status = check_readiness(missing)

    assert status.configured and not status.ready
    assert "not found" in status.message.lower()
    assert str(missing) in status.message
    assert not any(p.present for p in status.parts)


def test_parts_are_not_checked_when_the_folder_is_unusable(tmp_path):
    missing = tmp_path / "nowhere"

    status = check_readiness(missing)

    for p in status.parts:
        assert not p.checked
        assert str(missing) in p.detail  # says what was actually looked at


def test_parts_inside_a_usable_folder_are_checked(root):
    shutil.rmtree(root / "labeltool_labels_refined")

    assert all(p.checked for p in check_readiness(root).parts)


def test_dataset_path_that_is_a_file(tmp_path):
    file = tmp_path / "SeeingThroughFog.zip"
    file.write_bytes(b"PK")

    status = check_readiness(file)

    assert not status.ready
    assert "not a folder" in status.message.lower()


def test_no_dataset_configured_explains_how_to_set_one():
    status = check_readiness(None)

    assert not status.configured and not status.ready
    assert status.root is None
    assert "--dataset" in status.message
    assert "EDGE_LAB_DATASET" in status.message
    assert "synthetic" in status.message.lower()  # the demo path still works
    # The required parts are still listed, so the user knows what to get.
    assert len(status.parts) == 3 and not any(p.present for p in status.parts)


def test_names_the_parts_that_are_not_needed(root):
    not_needed = " ".join(check_readiness(root).not_needed).lower()

    for sensor in ["lidar", "radar", "gated", "thermal"]:
        assert sensor in not_needed


def test_root_is_reported_for_display(root):
    assert check_readiness(root).root == str(root)


# --- frame lookup ---------------------------------------------------------------


def test_camera_image_resolves_a_known_sample(root):
    sample = next((root / "cam_stereo_left_lut").iterdir()).stem

    assert camera_image(root, sample) == root / "cam_stereo_left_lut" / f"{sample}.png"


@pytest.mark.parametrize(
    "sample_id",
    ["..", "../secret", "..\\secret", "/etc/passwd", "C:\\Windows\\win.ini", "2018-02-12_15-39-23_00100/../../x", ""],
)
def test_camera_image_rejects_anything_that_is_not_a_sample_id(root, sample_id):
    with pytest.raises(FrameNotFound):
        camera_image(root, sample_id)


def test_camera_image_rejects_unknown_sample(root):
    with pytest.raises(FrameNotFound):
        camera_image(root, "1999-01-01_00-00-00_00000")


def test_camera_image_without_dataset():
    with pytest.raises(FrameNotFound):
        camera_image(None, "2018-02-12_15-39-23_00100")


# --- index: conditions, objects and exclusions ------------------------------------


def frame(index, sample_id):
    return next(f for f in index.frames if f.id == sample_id)


def test_index_gives_every_condition_one_fixture_frame(root):
    index = index_dataset(root)

    assert sorted(f.condition for f in index.frames) == sorted(CONDITIONS)


def test_index_excludes_and_counts_the_undeterminable_samples(root):
    index = index_dataset(root)

    assert index.excluded == {"fog with rain or snow": 1, "twilight": 1, "malformed label line": 1}


def test_malformed_label_line_is_reported_with_its_file_and_line(root):
    [problem] = index_dataset(root).problems

    assert "2018-02-08_10-00-00_00600.txt" in problem
    assert "line 2" in problem


def test_index_counts_main_class_objects_only(root):
    index = index_dataset(root)

    assert frame(index, "2018-02-03_10-00-00_00100").class_counts == {"PassengerCar": 1, "Pedestrian": 1}
    # Vehicle is a fallback class (an ignore region), not an object to score.
    assert frame(index, "2018-02-04_10-00-00_00200").class_counts == {"RidableVehicle": 1}


def test_a_sample_with_an_empty_label_file_is_kept_with_no_objects(root):
    (root / "gt_labels" / "cam_left_labels_TMP" / "2018-02-03_10-00-00_00100.txt").write_text("")

    assert frame(index_dataset(root), "2018-02-03_10-00-00_00100").class_counts == {}


def test_a_sample_without_a_label_file_is_excluded(root):
    (root / "gt_labels" / "cam_left_labels_TMP" / "2018-02-03_10-00-00_00100.txt").unlink()

    index = index_dataset(root)

    assert "2018-02-03_10-00-00_00100" not in {f.id for f in index.frames}
    assert index.excluded["no label file"] == 1


def test_unreadable_metadata_is_excluded_and_located(root):
    (root / "labeltool_labels_refined" / "2018-02-03_10-00-00_00100.json").write_text("{not json")

    index = index_dataset(root)

    assert index.excluded["metadata unreadable"] == 1
    assert any("2018-02-03_10-00-00_00100.json" in p for p in index.problems)


def test_files_that_are_not_samples_are_ignored(root):
    (root / "labeltool_labels_refined" / "notes.json").write_text("{}")

    index = index_dataset(root)

    assert len(index.frames) == 8 and sum(index.excluded.values()) == 3
