"""Benchmark runs: ground truth read into 0-1 boxes, manifests checked before a run, warnings, and per-condition
results re-scored from stored detections at any display threshold."""

import pytest

from backend.benchmark import BenchmarkFrame, GroundTruth
from backend.benchmark_run import (
    BenchmarkExperiment,
    ManifestRefused,
    benchmark_results,
    check_manifest,
    ground_truth,
    run_warnings,
)
from backend.conditions import CONDITIONS, VOCABULARY_VERSION
from backend.dataset import Frame
from backend.detection import Box, Detection, ModelInfo
from backend.labels import Box as LabelBox
from backend.subset import Manifest

MODEL = ModelInfo(name="Stub detector", version="fixture-1", runtime="none")
FULL = Box(x1=0.0, y1=0.0, x2=0.5, y2=0.5)


def manifest(frames, vocabulary_version=VOCABULARY_VERSION):
    return Manifest(seed=0, cap=10, vocabulary_version=vocabulary_version, frames=frames)


def detection(label, confidence, box=FULL):
    return Detection(label=label, confidence=confidence, box=box)


def truth(label, box=FULL):
    return GroundTruth(label=label, box=box)


# --- ground truth ---------------------------------------------------------------------


def test_ground_truth_boxes_are_divided_by_the_image_size():
    [box] = ground_truth([LabelBox("PassengerCar", 16, 20, 48, 60)], width=160, height=80)

    assert box.label == "PassengerCar"
    assert (box.box.x1, box.box.y1, box.box.x2, box.box.y2) == pytest.approx((0.1, 0.25, 0.3, 0.75))


def test_ground_truth_boxes_running_off_the_image_are_clamped_to_it():
    # KITTI boxes of truncated objects can reach past the image edge.
    [box] = ground_truth([LabelBox("Pedestrian", -5, 70, 170, 90)], width=160, height=80)

    assert (box.box.x1, box.box.y1, box.box.x2, box.box.y2) == pytest.approx((0.0, 70 / 80, 1.0, 1.0))


def test_every_label_is_kept_whatever_its_role():
    # Scoring decides the roles; ignore regions and excluded labels must still reach it.
    labels = [LabelBox(name, 0, 0, 10, 10) for name in ("PassengerCar", "Vehicle", "DontCare", "train")]

    assert [t.label for t in ground_truth(labels, width=100, height=100)] == ["PassengerCar", "Vehicle", "DontCare", "train"]


# --- manifest checks ----------------------------------------------------------------------


INDEX = [
    Frame("2018-02-03_10-00-00_00100", "clear-day", {"PassengerCar": 1}),
    Frame("2018-02-04_21-00-00_00200", "fog-night", {"PassengerCar": 1}),
]


def test_a_manifest_of_frames_in_the_local_dataset_passes():
    check_manifest(manifest({"clear-day": ["2018-02-03_10-00-00_00100"], "fog-night": []}), INDEX)


def test_a_manifest_from_another_vocabulary_version_is_refused_in_plain_language():
    with pytest.raises(ManifestRefused) as refused:
        check_manifest(manifest({"clear-day": ["2018-02-03_10-00-00_00100"]}, vocabulary_version=99), INDEX)

    message = str(refused.value)
    assert "99" in message and str(VOCABULARY_VERSION) in message
    assert "new subset" in message


def test_frames_missing_from_the_local_dataset_are_named():
    missing = ["2018-02-09_10-00-00_00900", "2018-02-09_10-00-00_00901"]

    with pytest.raises(ManifestRefused) as refused:
        check_manifest(manifest({"clear-day": ["2018-02-03_10-00-00_00100", *missing]}), INDEX)

    message = str(refused.value)
    assert "2 frames" in message
    assert all(frame_id in message for frame_id in missing)


def test_a_frame_listed_under_another_condition_counts_as_missing():
    # The local metadata puts this frame in fog-night; scoring it as clear-day would mislabel its results.
    with pytest.raises(ManifestRefused, match="2018-02-04_21-00-00_00200"):
        check_manifest(manifest({"clear-day": ["2018-02-04_21-00-00_00200"]}), INDEX)


def test_a_long_list_of_missing_frames_is_shortened():
    missing = [f"2018-02-09_10-00-00_{n:05d}" for n in range(20)]

    with pytest.raises(ManifestRefused) as refused:
        check_manifest(manifest({"clear-day": missing}), INDEX)

    message = str(refused.value)
    assert "20 frames" in message
    assert missing[0] in message and missing[-1] not in message
    assert "and 15 more" in message


def test_unknown_conditions_are_refused():
    with pytest.raises(ManifestRefused, match="fog-chamber"):
        check_manifest(manifest({"clear-day": ["2018-02-03_10-00-00_00100"], "fog-chamber": []}), INDEX)


def test_a_manifest_with_no_frames_is_refused():
    with pytest.raises(ManifestRefused, match="no frames"):
        check_manifest(manifest({condition: [] for condition in CONDITIONS}), INDEX)


# --- warnings ---------------------------------------------------------------------------


def test_frames_whose_only_detections_are_unmapped_classes_are_warned_about():
    frames = [
        BenchmarkFrame(id="a", predictions=[detection("traffic light", 0.8), detection("dog", 0.4)], truths=[]),
        BenchmarkFrame(id="b", predictions=[detection("traffic light", 0.8), detection("car", 0.4)], truths=[]),
        BenchmarkFrame(id="c", predictions=[], truths=[]),
    ]

    [warning] = run_warnings(frames)

    assert "1 frame" in warning and "a" in warning.split(":")[-1]
    assert "b" not in warning.split(":")[-1] and "c" not in warning.split(":")[-1]


def test_no_warnings_when_every_frame_with_detections_has_a_mapped_one():
    frames = [BenchmarkFrame(id="a", predictions=[detection("car", 0.9)], truths=[])]

    assert run_warnings(frames) == []


# --- results ------------------------------------------------------------------------------


def experiment(frames):
    return BenchmarkExperiment(
        id="0" * 64,
        manifest=manifest({c: [f.id for f in frames.get(c, [])] for c in ("clear-day", "fog-day")}),
        model=MODEL,
        class_mapping_version=1,
        confidence_floor=0.05,
        frames=frames,
        warnings=[],
    )


def test_results_list_every_manifest_condition_in_vocabulary_order_even_when_empty():
    results = benchmark_results(experiment({"fog-day": [], "clear-day": []}), display_threshold=0.5)

    assert [c.condition for c in results.conditions] == ["clear-day", "fog-day"]
    assert results.conditions[0].map is None
    assert results.conditions[0].objects == 0
    assert results.conditions[0].low_n


def test_results_score_each_condition_on_its_own_frames():
    clear = BenchmarkFrame(id="a", predictions=[detection("car", 0.9)], truths=[truth("PassengerCar")])
    fog = BenchmarkFrame(id="b", predictions=[], truths=[truth("PassengerCar"), truth("Pedestrian")])

    results = benchmark_results(experiment({"clear-day": [clear], "fog-day": [fog]}), display_threshold=0.5)
    clear_day, fog_day = results.conditions

    assert (clear_day.map, clear_day.objects, clear_day.frames) == (1.0, 1, 1)
    assert (fog_day.map, fog_day.objects, fog_day.frames) == (0.0, 2, 1)


def test_precision_and_recall_follow_the_display_threshold():
    frame = BenchmarkFrame(
        id="a",
        predictions=[detection("car", 0.9), detection("car", 0.3, Box(x1=0.6, y1=0.6, x2=0.9, y2=0.9))],
        truths=[truth("PassengerCar")],
    )
    run = experiment({"clear-day": [frame]})

    high = benchmark_results(run, display_threshold=0.5).conditions[0].classes[0]
    low = benchmark_results(run, display_threshold=0.25).conditions[0].classes[0]

    assert (high.class_name, high.precision, high.recall) == ("PassengerCar", 1.0, 1.0)
    assert (low.precision, low.recall) == (0.5, 1.0)
    assert high.ap == low.ap  # AP doesn't depend on the display threshold


def test_results_carry_the_run_record():
    results = benchmark_results(experiment({"clear-day": []}), display_threshold=0.4)

    assert results.display_threshold == 0.4
    assert results.model == MODEL
    assert results.manifest.cap == 10
    assert results.class_mapping_version == 1
    assert results.iou_threshold == 0.5
    assert results.low_n_objects == 30
