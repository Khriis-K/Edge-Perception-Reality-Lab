"""Synthetic degradation on the subset's clear frames: the bridge between the two modes.

A run degrades every frame the manifest lists under one clear condition and runs the detector on both the clean and
the degraded frame. Because these frames are labelled, it is scored two ways, from the same stored detections:
- stability, the degraded detections against the clean ones, as on video (backend/stability.py);
- accuracy, each variant against the ground truth, with the Benchmark's definitions (backend/benchmark.py). The clean
  side is the Benchmark's own clear condition on the same frames, so its AP matches the Benchmark run's.

The degraded variant is also listed beside a Benchmark run on the same manifest, model and scoring settings, as an
extra condition (e.g. "Synthetic fog 0.60"), so synthetic and real degradation can be compared on one footing.
"""

from typing import Literal

from pydantic import BaseModel

from backend.benchmark import IOU_THRESHOLD, BenchmarkFrame, GroundTruth
from backend.benchmark_run import BenchmarkExperiment, ConditionResult, SyntheticConditionResult, condition_result
from backend.degradations import TITLES
from backend.detection import Detection, ModelInfo
from backend.experiment import AppliedDegradation, DegradationSettings, FrameResult, FrameVariant
from backend.stability import StabilityReport, stability_report
from backend.subset import LOW_N_OBJECTS, Manifest

# Only clear-weather frames: degrading frames that are already foggy or snowy would stack two degradations.
ClearCondition = Literal["clear-day", "clear-night"]


class SyntheticFrame(BaseModel):
    id: str
    clean: list[Detection]  # raw detector output, COCO labels, down to the confidence floor
    degraded: list[Detection]
    truths: list[GroundTruth]


class SyntheticFramesExperiment(BaseModel):
    id: str
    manifest: Manifest  # the whole manifest, as for a Benchmark run
    condition: ClearCondition
    degradation: AppliedDegradation
    model: ModelInfo
    class_mapping_version: int
    confidence_floor: float
    frames: list[SyntheticFrame]  # in manifest order


class SyntheticFramesResults(BaseModel):
    id: str
    manifest: Manifest
    condition: ClearCondition
    degradation: AppliedDegradation
    title: str  # e.g. "Synthetic fog 0.60", as the Benchmark condition tree names the degraded condition
    model: ModelInfo
    class_mapping_version: int
    confidence_floor: float
    iou_threshold: float
    display_threshold: float
    low_n_objects: int
    stability: StabilityReport  # degraded against clean detections; frames indexed in manifest order
    clean: ConditionResult  # against the ground truth
    degraded: ConditionResult


def synthetic_frames_results(experiment: SyntheticFramesExperiment, display_threshold: float) -> SyntheticFramesResults:
    """Stability, and both variants scored at the display threshold, from the stored detections."""
    stability = stability_report(
        [FrameResult(index=i, clean=f.clean, degraded=f.degraded) for i, f in enumerate(experiment.frames)]
    )
    return SyntheticFramesResults(
        id=experiment.id,
        manifest=experiment.manifest,
        condition=experiment.condition,
        degradation=experiment.degradation,
        title=degradation_title(experiment.degradation),
        model=experiment.model,
        class_mapping_version=experiment.class_mapping_version,
        confidence_floor=experiment.confidence_floor,
        iou_threshold=IOU_THRESHOLD,
        display_threshold=display_threshold,
        low_n_objects=LOW_N_OBJECTS,
        stability=stability,
        clean=_scored(experiment, "clean", display_threshold),
        degraded=_scored(experiment, "degraded", display_threshold),
    )


def benchmark_rows(
    benchmark: BenchmarkExperiment, runs: list[SyntheticFramesExperiment], display_threshold: float
) -> list[SyntheticConditionResult]:
    """The runs that belong beside this Benchmark run, as condition rows: same manifest, model and scoring settings.
    Ordered by condition, degradation, severity and seed."""
    same = [run for run in runs if _settings(run) == _settings(benchmark)]
    same.sort(key=lambda run: (run.condition, run.degradation.kind, run.degradation.severity, run.degradation.seed))
    return [
        SyntheticConditionResult(
            **_scored(run, "degraded", display_threshold).model_dump(),
            experiment_id=run.id,
            title=degradation_title(run.degradation),
            degradation=run.degradation,
        )
        for run in same
    ]


def degradation_title(degradation: DegradationSettings) -> str:
    """"Synthetic fog 0.60": the degradation and its severity, as the condition tree names it."""
    return f"{TITLES[degradation.kind]} {degradation.severity:.2f}"


def _scored(experiment: SyntheticFramesExperiment, variant: FrameVariant, display_threshold: float) -> ConditionResult:
    frames = [BenchmarkFrame(id=f.id, predictions=getattr(f, variant), truths=f.truths) for f in experiment.frames]
    return condition_result(experiment.condition, frames, display_threshold)


def _settings(run: SyntheticFramesExperiment | BenchmarkExperiment) -> tuple:
    return (run.manifest, run.model.name, run.model.version, run.class_mapping_version, run.confidence_floor)
