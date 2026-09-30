"""Benchmark runs: the detector over every frame of a subset manifest, scored against the dataset's labels.

A run stores the raw detections (down to the confidence floor) and the ground truth of every frame, grouped by
condition. Results are scored from that record on request, so a new display threshold never re-runs inference.
"""

from pathlib import Path

import cv2
import numpy as np
from pydantic import BaseModel

from backend.benchmark import IOU_THRESHOLD, BenchmarkFrame, ClassMetrics, GroundTruth, evaluate_condition
from backend.class_mapping import dataset_class
from backend.conditions import CONDITIONS, VOCABULARY_VERSION
from backend.dataset import Frame, camera_image, read_labels
from backend.detection import Box, ModelInfo
from backend.labels import Box as LabelBox
from backend.subset import LOW_N_OBJECTS, Manifest

SHOWN_IDS = 5  # frame ids named in a message before the rest are counted


class ManifestRefused(ValueError):
    """The manifest can't be run against this app and dataset. The message says why, in plain language."""


class BenchmarkExperiment(BaseModel):
    id: str
    manifest: Manifest  # the whole manifest, not a hash: it is the run's configuration
    model: ModelInfo
    class_mapping_version: int
    confidence_floor: float
    frames: dict[str, list[BenchmarkFrame]]  # condition -> its frames, in manifest order
    warnings: list[str]


class ConditionResult(BaseModel):
    condition: str
    frames: int
    objects: int
    low_n: bool  # some class has fewer than low_n_objects objects
    map: float | None
    classes: list[ClassMetrics]


class BenchmarkResults(BaseModel):
    id: str
    manifest: Manifest
    model: ModelInfo
    class_mapping_version: int
    confidence_floor: float
    iou_threshold: float
    display_threshold: float
    low_n_objects: int
    conditions: list[ConditionResult]  # every condition in the manifest, in vocabulary order
    warnings: list[str]


def check_manifest(manifest: Manifest, frames: list[Frame]) -> None:
    """Raise ManifestRefused unless every frame the manifest lists is a usable local frame under the same condition."""
    if manifest.vocabulary_version != VOCABULARY_VERSION:
        raise ManifestRefused(
            f"This manifest was drawn with condition vocabulary version {manifest.vocabulary_version}, but this app "
            f"uses version {VOCABULARY_VERSION}, so its conditions may not mean the same thing. Draw a new subset in "
            "Setup."
        )
    unknown = sorted(set(manifest.frames) - set(CONDITIONS))
    if unknown:
        raise ManifestRefused(f"The manifest names conditions this app doesn't know: {', '.join(unknown)}.")
    if not any(manifest.frames.values()):
        raise ManifestRefused("The manifest lists no frames.")

    local = {(f.id, f.condition) for f in frames}
    missing = [i for condition, ids in manifest.frames.items() for i in ids if (i, condition) not in local]
    if missing:
        raise ManifestRefused(
            f"{_frames(len(missing))} in the manifest {'is' if len(missing) == 1 else 'are'} not in the local dataset "
            f"under {'its' if len(missing) == 1 else 'their'} condition: {_listed(missing)}. Check that the dataset "
            "is complete, or draw a new subset in Setup."
        )


def ground_truth(boxes: list[LabelBox], width: int, height: int) -> list[GroundTruth]:
    """Label boxes in pixels to 0-1 image coordinates, clamped to the image. Every label is kept, whatever its role."""
    return [
        GroundTruth(
            label=b.label,
            box=Box(x1=_unit(b.left / width), y1=_unit(b.top / height), x2=_unit(b.right / width), y2=_unit(b.bottom / height)),
        )
        for b in boxes
    ]


def read_frame(root: Path, sample_id: str) -> tuple[np.ndarray, list[GroundTruth]]:
    """A dataset frame's BGR image and its ground truth."""
    path = camera_image(root, sample_id)
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise OSError(f"Could not read the camera image {path.name}.")
    return image, ground_truth(read_labels(root, sample_id), width=image.shape[1], height=image.shape[0])


def run_warnings(frames: list[BenchmarkFrame]) -> list[str]:
    """What a run should flag: frames with detections, none of them of a class the mapping counts."""
    unmapped = [f.id for f in frames if f.predictions and all(dataset_class(p.label) is None for p in f.predictions)]
    if not unmapped:
        return []
    verb = "has" if len(unmapped) == 1 else "have"
    return [
        f"{_frames(len(unmapped))} {verb} detections, but only of classes outside the class mapping, so none of them "
        f"count: {_listed(unmapped)}"
    ]


def benchmark_results(experiment: BenchmarkExperiment, display_threshold: float) -> BenchmarkResults:
    """Every manifest condition scored at the display threshold, from the stored detections."""
    conditions = []
    for condition in (c for c in CONDITIONS if c in experiment.frames):
        metrics = evaluate_condition(experiment.frames[condition], display_threshold)
        conditions.append(
            ConditionResult(
                condition=condition,
                frames=metrics.frames,
                objects=metrics.objects,
                low_n=metrics.low_n,
                map=metrics.map,
                classes=metrics.classes,
            )
        )
    return BenchmarkResults(
        id=experiment.id,
        manifest=experiment.manifest,
        model=experiment.model,
        class_mapping_version=experiment.class_mapping_version,
        confidence_floor=experiment.confidence_floor,
        iou_threshold=IOU_THRESHOLD,
        display_threshold=display_threshold,
        low_n_objects=LOW_N_OBJECTS,
        conditions=conditions,
        warnings=experiment.warnings,
    )


def _frames(count: int) -> str:
    return f"{count} frame{'' if count == 1 else 's'}"


def _listed(ids: list[str]) -> str:
    shown = ", ".join(ids[:SHOWN_IDS])
    return shown if len(ids) <= SHOWN_IDS else f"{shown} and {len(ids) - SHOWN_IDS} more"


def _unit(value: float) -> float:
    return min(max(value, 0.0), 1.0)
