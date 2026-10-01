"""Synthetic degradation on labelled dataset frames: scoring both variants against the ground truth with the
Benchmark's definitions, stability against the clean detections, the experiment id, and which Benchmark run a
synthetic run belongs beside."""

import pytest

from backend.benchmark import BenchmarkFrame, GroundTruth, evaluate_condition
from backend.benchmark_run import BenchmarkExperiment
from backend.detection import Box, Detection, ModelInfo
from backend.experiment import AppliedDegradation, DegradationSettings, FrameResult
from backend.experiment_cache import synthetic_frames_experiment_id
from backend.stability import stability_report
from backend.subset import Manifest
from backend.synthetic_frames import (
    SyntheticFrame,
    SyntheticFramesExperiment,
    benchmark_rows,
    synthetic_frames_results,
)

MODEL = ModelInfo(name="Stub detector", version="fixture-1", runtime="none")
MANIFEST = Manifest(seed=0, cap=300, vocabulary_version=1, frames={"clear-day": ["a", "b"], "fog-day": ["c"]})
FOG = DegradationSettings(kind="fog", severity=0.6, seed=0)
CAR = Box(x1=0.1, y1=0.1, x2=0.4, y2=0.4)
PERSON = Box(x1=0.6, y1=0.1, x2=0.7, y2=0.5)


def car(confidence=0.9, box=CAR):
    return Detection(label="car", confidence=confidence, box=box)


def frames():
    truths = [GroundTruth(label="PassengerCar", box=CAR), GroundTruth(label="Pedestrian", box=PERSON)]
    return [
        # The fog loses the car in frame a, and keeps it in frame b.
        SyntheticFrame(id="a", clean=[car()], degraded=[], truths=truths),
        SyntheticFrame(id="b", clean=[car()], degraded=[car(0.6)], truths=truths),
    ]


def experiment(**changes):
    fields = {
        "id": "x" * 64,
        "manifest": MANIFEST,
        "condition": "clear-day",
        "degradation": AppliedDegradation(**FOG.model_dump(), parameters={"transmission": 0.46, "airlight": 0.8}),
        "model": MODEL,
        "class_mapping_version": 1,
        "confidence_floor": 0.05,
        "frames": frames(),
    }
    return SyntheticFramesExperiment(**{**fields, **changes})


def benchmark(**changes):
    fields = {
        "id": "b" * 64,
        "manifest": MANIFEST,
        "model": MODEL,
        "class_mapping_version": 1,
        "confidence_floor": 0.05,
        "frames": {},
        "warnings": [],
    }
    return BenchmarkExperiment(**{**fields, **changes})


# --- results ------------------------------------------------------------------------


def test_both_variants_are_scored_against_the_ground_truth_with_the_benchmark_definitions():
    results = synthetic_frames_results(experiment(), display_threshold=0.25)

    as_benchmark = lambda variant: [BenchmarkFrame(id=f.id, predictions=getattr(f, variant), truths=f.truths) for f in frames()]
    clean = evaluate_condition(as_benchmark("clean"), 0.25)
    degraded = evaluate_condition(as_benchmark("degraded"), 0.25)
    assert results.clean.map == clean.map == pytest.approx(0.5)
    assert results.clean.classes == clean.classes
    assert results.degraded.map == degraded.map == pytest.approx(0.25)
    assert results.degraded.classes == degraded.classes
    assert (results.clean.frames, results.clean.objects) == (2, 4)
    assert (results.degraded.frames, results.degraded.objects) == (2, 4)


def test_stability_compares_the_degraded_detections_with_the_clean_ones():
    results = synthetic_frames_results(experiment(), display_threshold=0.25)

    expected = stability_report([FrameResult(index=i, clean=f.clean, degraded=f.degraded) for i, f in enumerate(frames())])
    assert results.stability == expected
    assert (results.stability.retention.count, results.stability.retention.total) == (1, 2)


def test_results_say_what_ran_and_how_it_was_scored():
    results = synthetic_frames_results(experiment(), display_threshold=0.4)

    assert results.condition == "clear-day"
    assert results.degradation.kind == "fog"
    assert results.title == "Synthetic fog 0.60"
    assert results.manifest == MANIFEST
    assert results.model == MODEL
    assert results.display_threshold == 0.4
    assert results.iou_threshold == 0.5


# --- experiment id ------------------------------------------------------------------


ID_BASE = {
    "manifest": MANIFEST,
    "condition": "clear-day",
    "model": MODEL,
    "class_mapping_version": 1,
    "confidence_floor": 0.05,
    "degradation": FOG,
}


def test_the_same_settings_give_the_same_id():
    assert synthetic_frames_experiment_id(**ID_BASE) == synthetic_frames_experiment_id(**ID_BASE)


@pytest.mark.parametrize(
    "change",
    [
        {"manifest": Manifest(seed=1, cap=300, vocabulary_version=1, frames=MANIFEST.frames)},
        {"manifest": Manifest(seed=0, cap=300, vocabulary_version=1, frames={"clear-day": ["a"], "fog-day": ["c"]})},
        {"condition": "clear-night"},
        {"degradation": DegradationSettings(kind="darkness", severity=0.6, seed=0)},
        {"degradation": DegradationSettings(kind="fog", severity=0.7, seed=0)},
        {"degradation": DegradationSettings(kind="fog", severity=0.6, seed=1)},
        {"model": MODEL.model_copy(update={"version": "fixture-2"})},
        {"class_mapping_version": 2},
        {"confidence_floor": 0.1},
    ],
)
def test_changing_any_result_affecting_setting_gives_another_id(change):
    assert synthetic_frames_experiment_id(**{**ID_BASE, **change}) != synthetic_frames_experiment_id(**ID_BASE)


def test_the_runtime_is_not_part_of_the_id():
    other_runtime = {**ID_BASE, "model": MODEL.model_copy(update={"runtime": "onnxruntime 9"})}

    assert synthetic_frames_experiment_id(**other_runtime) == synthetic_frames_experiment_id(**ID_BASE)


# --- rows beside a benchmark --------------------------------------------------------


def test_a_run_on_the_benchmarks_manifest_and_model_becomes_a_condition_row():
    rows = benchmark_rows(benchmark(), [experiment()], display_threshold=0.25)

    assert len(rows) == 1
    row = rows[0]
    assert row.experiment_id == "x" * 64
    assert row.title == "Synthetic fog 0.60"
    assert row.condition == "clear-day"
    assert row.degradation.severity == 0.6
    assert row.map == pytest.approx(0.25)
    assert (row.frames, row.objects, row.low_n) == (2, 4, True)


@pytest.mark.parametrize(
    "change",
    [
        {"manifest": Manifest(seed=1, cap=300, vocabulary_version=1, frames=MANIFEST.frames)},
        {"model": MODEL.model_copy(update={"version": "fixture-2"})},
        {"class_mapping_version": 2},
        {"confidence_floor": 0.1},
    ],
)
def test_a_run_on_another_manifest_or_model_is_not_a_row(change):
    assert benchmark_rows(benchmark(**change), [experiment()], display_threshold=0.25) == []


def test_rows_are_ordered_by_condition_kind_severity_and_seed():
    def run(condition, kind, severity, seed):
        settings = DegradationSettings(kind=kind, severity=severity, seed=seed)
        degradation = AppliedDegradation(**settings.model_dump(), parameters={})
        return experiment(id=f"{condition}{kind}{severity}{seed}", condition=condition, degradation=degradation)

    runs = [
        run("clear-night", "blur", 0.2, 0),
        run("clear-day", "fog", 0.6, 1),
        run("clear-day", "fog", 0.6, 0),
        run("clear-day", "fog", 0.3, 0),
        run("clear-day", "darkness", 0.9, 0),
    ]

    rows = benchmark_rows(benchmark(), runs, display_threshold=0.25)

    assert [(r.condition, r.degradation.kind, r.degradation.severity, r.degradation.seed) for r in rows] == [
        ("clear-day", "darkness", 0.9, 0),
        ("clear-day", "fog", 0.3, 0),
        ("clear-day", "fog", 0.6, 0),
        ("clear-day", "fog", 0.6, 1),
        ("clear-night", "blur", 0.2, 0),
    ]
