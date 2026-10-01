"""Findings: what a finished run shows a reviewer, as data for the Findings screen's charts.

Sim-to-real, for a Benchmark run. Per class, the change in AP from clear weather to synthetic fog, beside the change
from clear weather to real fog, all scored with the Benchmark's own definitions (backend/benchmark.py):
- reference: the run's clear-day frames;
- synthetic: each cached synthetic fog run on those same clear-day frames, with the run's manifest, model and
  scoring settings (backend/synthetic_frames.py lists them beside the run);
- real: the run's fog-day frames.
Both sides are daytime, to keep illumination out of the comparison. The real-fog frames are different scenes from
the clear ones, so the comparison is distributional, not paired. A drop is reference AP minus the other side's AP, and
is undefined (None) when either AP is: a class with no objects on one side has nothing to compare.

Precision-recall, for a Benchmark run: each class's PR curve on the same three sides, the Benchmark's own
(ClassMetrics.pr_curve, the curve its AP is computed from), with its precision and recall at the display threshold.

Where it fails, for a Benchmark run: AP per condition and class, day and night as separate conditions, with counts.

Worst frames: a Benchmark run's highest error scores at the display threshold over every condition, or a video run's
highest stability scores. A video run, being a continuous clip, also has a reliability timeline: every frame's
stability score in order. A dataset subset is not a sequence, so it has none.

Headlines are the user's own, one per numbered finding, stored beside the run (backend/experiment_cache.py). Nothing
here writes one.
"""

from typing import Literal, NamedTuple

from pydantic import BaseModel

from backend.benchmark import IOU_THRESHOLD, WEIGHTS, BenchmarkWeights, ClassMetrics, FrameScore
from backend.benchmark_run import BenchmarkExperiment, ConditionResult, SyntheticConditionResult, condition_result
from backend.class_mapping import CLASS_MAPPING, ClassMapping
from backend.conditions import CONDITIONS, condition_name
from backend.detection import ModelInfo
from backend.experiment import AppliedDegradation, Experiment
from backend.latency import LatencySummary
from backend.stability import STABILITY_THRESHOLD, ScoreWeights, stability_report
from backend.stability import IOU_THRESHOLD as STABILITY_IOU
from backend.stability import WEIGHTS as STABILITY_WEIGHTS
from backend.subset import LOW_N_OBJECTS, Manifest
from backend.synthetic_frames import SyntheticFramesExperiment, benchmark_rows

# The numbered findings, each led by a headline the user writes from the results. Nothing here ever writes one.
FindingKey = Literal["sim-to-real", "where-it-fails", "precision-recall", "reliability-timeline"]
BENCHMARK_FINDINGS: tuple[FindingKey, ...] = ("sim-to-real", "where-it-fails", "precision-recall")
VIDEO_FINDINGS: tuple[FindingKey, ...] = ("reliability-timeline",)
HEADLINE_LENGTH = 500  # one sentence, generously

REFERENCE = "clear-day"
REAL_FOG = "fog-day"
REAL_FOG_TITLE = "Real fog · day"
WORST_FRAMES = 6  # in the gallery; every frame is in the Benchmark's Frame table

# Said of every run, then each kind's own limits before them.
_EVERY_RUN = [
    "Latency is this machine's, with its execution provider: a comparison between runs, not a real-time claim.",
    "This is an educational robustness evaluation. It has not been validated for safety-critical or operational use.",
]
# "Read this first": what a reviewer must know before trusting a Benchmark run's findings.
BENCHMARK_LIMITATIONS = [
    "Sim-to-real is distributional, not paired: the real-fog frames are different scenes from the clear frames. Both "
    "sides are daytime to limit the lighting confound, but real fog also comes with other roads, traffic and light.",
    "A mismatch between the synthetic and the real drop is a finding about the simulation, not a failure of the "
    "evaluation.",
    f"A metric over fewer than {LOW_N_OBJECTS} objects is marked low n: at that size AP is mostly noise.",
    "The fog condition is mostly dense fog, and frames with fog together with snow are excluded, not guessed.",
    "Ignore regions (the fallback labels Vehicle and Obstacle, DontCare, and group boxes) count as neither hits nor "
    "misses, and the class mapping decides which detections count at all.",
    "Results hold for this subset, model and class mapping only, and say nothing beyond them.",
    *_EVERY_RUN,
]


class Side(BaseModel):
    """A condition's mAP with the counts behind it."""

    condition: str
    map: float | None
    objects: int
    frames: int
    low_n: bool


class ClassDrop(BaseModel):
    class_name: str
    reference_ap: float | None
    reference_objects: int
    ap: float | None
    objects: int
    drop: float | None  # reference_ap - ap; None when either is undefined
    low_n: bool  # either side has fewer than low_n_objects objects of this class


class Comparison(Side):
    """One degraded side against the reference."""

    title: str
    experiment_id: str | None  # the synthetic run's id; None for real fog, which is in the Benchmark run itself
    map_drop: float | None
    classes: list[ClassDrop]


class SimToReal(BaseModel):
    reference: Side | None  # None when the run has no clear-day frames, and then nothing is compared
    real: Comparison | None  # None without a reference or without fog-day frames
    synthetic: list[Comparison]  # one per synthetic fog run on the clear-day frames


class CurveSide(BaseModel):
    """One side's per-class PR curves, each with its precision and recall at the display threshold."""

    title: str
    condition: str
    experiment_id: str | None  # the synthetic run's id; None for the run's own conditions
    classes: list[ClassMetrics]  # in MAIN_CLASSES order


class PRCurves(BaseModel):
    reference: CurveSide | None  # None when the run has no clear-day frames, and then nothing is overlaid
    real: CurveSide | None
    synthetic: list[CurveSide]


class HeatmapCell(BaseModel):
    class_name: str
    ap: float | None  # None: the condition has no objects of this class
    objects: int
    frames: int
    low_n: bool


class HeatmapRow(Side):
    cells: list[HeatmapCell]  # in MAIN_CLASSES order


class WorstFrame(FrameScore):
    condition: str


VIDEO_LIMITATIONS = [
    "These are stability metrics relative to the clean baseline, not accuracy: the clip has no labels, so a "
    "detection kept under degradation may still be wrong.",
    f"Low n counts detections across frames. Consecutive frames of one object are not independent evidence, so on "
    f"video the low-n flag (under {LOW_N_OBJECTS}) under-warns.",
    "One degradation at one severity: other kinds or severities may behave differently.",
    *_EVERY_RUN,
]


class BenchmarkRecord(BaseModel):
    """What the run was: enough to reproduce it, and to read its numbers right."""

    frames: int
    objects: int  # main-class objects; ignore regions are not counted
    manifest: Manifest
    model: ModelInfo
    class_mapping: ClassMapping
    class_mapping_version: int
    match_iou: float
    confidence_floor: float
    weights: BenchmarkWeights  # of the worst-frame score
    low_n_objects: int


class BenchmarkFindings(BaseModel):
    kind: Literal["benchmark"] = "benchmark"
    id: str
    headlines: dict[FindingKey, str]  # only those the user has written
    display_threshold: float
    record: BenchmarkRecord
    latency: LatencySummary | None
    limitations: list[str]
    sim_to_real: SimToReal
    pr_curves: PRCurves
    conditions: list[HeatmapRow]  # every condition in the manifest, in vocabulary order: day and night apart
    worst_frames: list[WorstFrame]  # at the display threshold, worst first; frames with no errors are left out


def benchmark_findings(
    experiment: BenchmarkExperiment,
    runs: list[SyntheticFramesExperiment],
    display_threshold: float,
    headlines: dict[str, str],
) -> BenchmarkFindings:
    scored = [
        condition_result(condition, experiment.frames[condition], display_threshold)
        for condition in CONDITIONS
        if condition in experiment.frames
    ]
    sides = fog_sides(experiment, {row.condition: row for row in scored}, runs, display_threshold)
    return BenchmarkFindings(
        id=experiment.id,
        headlines=_own(headlines, BENCHMARK_FINDINGS),
        display_threshold=display_threshold,
        record=BenchmarkRecord(
            frames=sum(row.frames for row in scored),
            objects=sum(row.objects for row in scored),
            manifest=experiment.manifest,
            model=experiment.model,
            class_mapping=CLASS_MAPPING,
            class_mapping_version=experiment.class_mapping_version,
            match_iou=IOU_THRESHOLD,
            confidence_floor=experiment.confidence_floor,
            weights=WEIGHTS,
            low_n_objects=LOW_N_OBJECTS,
        ),
        latency=experiment.latency,
        limitations=BENCHMARK_LIMITATIONS,
        sim_to_real=sim_to_real(sides),
        pr_curves=pr_curves(sides),
        conditions=[HeatmapRow(**_side(row).model_dump(), cells=[_cell(c) for c in row.classes]) for row in scored],
        worst_frames=worst_frames(scored),
    )


class FrameReliability(BaseModel):
    """One video frame's stability against its clean frame: the reliability timeline's point."""

    index: int
    score: float  # the stability worst-frame score (backend/stability.py)
    retained: int
    dropped: int
    introduced: int
    class_changes: int
    confidence_loss: float


class VideoRecord(BaseModel):
    sample_id: str
    sample_title: str
    frames: int
    frame_width: int
    frame_height: int
    degradation: AppliedDegradation
    model: ModelInfo
    confidence_floor: float
    stability_threshold: float  # detections below it are left out of stability matching
    match_iou: float
    weights: ScoreWeights  # of the worst-frame score
    low_n_objects: int


class VideoFindings(BaseModel):
    """A video run has no labels, so no sim-to-real or heatmap. It is a continuous clip, so it has a timeline."""

    kind: Literal["video"] = "video"
    id: str
    headlines: dict[FindingKey, str]
    record: VideoRecord
    latency: LatencySummary | None
    limitations: list[str]
    timeline: list[FrameReliability]  # every frame, in order
    worst_frames: list[FrameReliability]  # worst first; frames with nothing changed are left out


def video_findings(experiment: Experiment, sample_title: str, headlines: dict[str, str]) -> VideoFindings:
    report = stability_report(experiment.frames)
    timeline = [FrameReliability(**f.model_dump(exclude={"matches"})) for f in report.frames]
    return VideoFindings(
        id=experiment.id,
        headlines=_own(headlines, VIDEO_FINDINGS),
        record=VideoRecord(
            sample_id=experiment.sample_id,
            sample_title=sample_title,
            frames=len(experiment.frames),
            frame_width=experiment.frame_width,
            frame_height=experiment.frame_height,
            degradation=experiment.degradation,
            model=experiment.model,
            confidence_floor=experiment.confidence_floor,
            stability_threshold=STABILITY_THRESHOLD,
            match_iou=STABILITY_IOU,
            weights=STABILITY_WEIGHTS,
            low_n_objects=LOW_N_OBJECTS,
        ),
        latency=experiment.latency,
        limitations=VIDEO_LIMITATIONS,
        timeline=timeline,
        worst_frames=sorted((p for p in timeline if p.score > 0), key=lambda p: -p.score)[:WORST_FRAMES],
    )


def worst_frames(conditions: list[ConditionResult]) -> list[WorstFrame]:
    """The WORST_FRAMES highest error scores over every condition. Sorting is stable, so ties keep vocabulary and
    then manifest order."""
    frames = [WorstFrame(**f.model_dump(), condition=row.condition) for row in conditions for f in row.frame_scores]
    ranked = sorted((f for f in frames if f.score > 0), key=lambda f: -f.score)
    return ranked[:WORST_FRAMES]


def _own(headlines: dict[str, str], keys: tuple[FindingKey, ...]) -> dict[FindingKey, str]:
    """The stored headlines of the findings this kind of run has, in finding order."""
    return {key: headlines[key] for key in keys if isinstance(headlines.get(key), str)}


def _cell(metrics: ClassMetrics) -> HeatmapCell:
    return HeatmapCell(
        class_name=metrics.class_name, ap=metrics.ap, objects=metrics.objects, frames=metrics.frames, low_n=metrics.low_n
    )


class FogSides(NamedTuple):
    """What both sim-to-real and precision-recall set side by side, already scored at the display threshold."""

    reference: ConditionResult
    real: ConditionResult | None  # None without fog-day frames
    synthetic: list[SyntheticConditionResult]  # each synthetic fog run on the clear-day frames


def fog_sides(
    experiment: BenchmarkExperiment,
    scored: dict[str, ConditionResult],
    runs: list[SyntheticFramesExperiment],
    display_threshold: float,
) -> FogSides | None:
    """`scored` is the run's own conditions. None when the run has no clear-day frames: nothing to compare against."""
    reference = scored.get(REFERENCE)
    if reference is None or reference.frames == 0:
        return None
    real = scored.get(REAL_FOG)
    synthetic = [
        row
        for row in benchmark_rows(experiment, runs, display_threshold)
        if row.degradation.kind == "fog" and row.condition == REFERENCE
    ]
    return FogSides(reference=reference, real=real if real and real.frames else None, synthetic=synthetic)


def sim_to_real(sides: FogSides | None) -> SimToReal:
    if sides is None:
        return SimToReal(reference=None, real=None, synthetic=[])
    reference = sides.reference
    return SimToReal(
        reference=_side(reference),
        real=None if sides.real is None else _compare(reference, sides.real, REAL_FOG_TITLE, None),
        synthetic=[_compare(reference, row, row.title, row.experiment_id) for row in sides.synthetic],
    )


def pr_curves(sides: FogSides | None) -> PRCurves:
    if sides is None:
        return PRCurves(reference=None, real=None, synthetic=[])
    return PRCurves(
        reference=_curves(sides.reference, condition_name(REFERENCE), None),
        real=None if sides.real is None else _curves(sides.real, REAL_FOG_TITLE, None),
        synthetic=[_curves(row, row.title, row.experiment_id) for row in sides.synthetic],
    )


def _curves(result: ConditionResult, title: str, experiment_id: str | None) -> CurveSide:
    return CurveSide(title=title, condition=result.condition, experiment_id=experiment_id, classes=result.classes)


def _side(result: ConditionResult) -> Side:
    return Side(condition=result.condition, map=result.map, objects=result.objects, frames=result.frames, low_n=result.low_n)


def _compare(reference: ConditionResult, other: ConditionResult, title: str, experiment_id: str | None) -> Comparison:
    before = {c.class_name: c for c in reference.classes}
    classes = [
        ClassDrop(
            class_name=c.class_name,
            reference_ap=before[c.class_name].ap,
            reference_objects=before[c.class_name].objects,
            ap=c.ap,
            objects=c.objects,
            drop=_difference(before[c.class_name].ap, c.ap),
            low_n=before[c.class_name].low_n or c.low_n,
        )
        for c in other.classes
    ]
    return Comparison(
        **_side(other).model_dump(),
        title=title,
        experiment_id=experiment_id,
        map_drop=_difference(reference.map, other.map),
        classes=classes,
    )


def _difference(before: float | None, after: float | None) -> float | None:
    return None if before is None or after is None else before - after
