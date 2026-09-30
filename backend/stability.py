"""Stability of detections under a degradation, measured against the clean frame.

The clip has no labels, so nothing here is accuracy: the clean detections are the baseline, and
these numbers say how much the degraded detections differ from them.

Matching, per frame, on detections at or above STABILITY_THRESHOLD:
1. Same-label pairs with IoU >= IOU_THRESHOLD are matched greedily, highest IoU first: retained.
2. Leftover pairs with different labels and IoU >= IOU_THRESHOLD, the same way: class change.
3. Clean detections still unmatched are dropped; degraded ones still unmatched are introduced.
Each detection is in exactly one match, so clean = retained + class changes + dropped, and
degraded = retained + class changes + introduced.

Worst-frame score, per frame:
    dropped x 1 + introduced x 1 + class changes x 1 + confidence loss x 1
where confidence loss is the total confidence that spatially matched detections (retained or
class-changed) lost; gains count as 0. Dropped detections add nothing to it: they are already counted.
Each unit is one detection's worth: losing a full 1.0 of confidence weighs as much as one drop.
"""

import statistics
from itertools import product
from typing import Literal, get_args

from pydantic import BaseModel

from backend.detection import Box, Detection
from backend.jobs import FrameResult

# Fixed, so the metrics don't move with the viewer's display threshold. The raw detections go
# down to the confidence floor, where boxes flicker in and out; matching there would be mostly noise.
STABILITY_THRESHOLD = 0.25
IOU_THRESHOLD = 0.5

Outcome = Literal["retained", "dropped", "introduced", "class_change"]


class ScoreWeights(BaseModel):
    dropped: float
    introduced: float
    class_changes: float
    confidence_loss: float


WEIGHTS = ScoreWeights(dropped=1.0, introduced=1.0, class_changes=1.0, confidence_loss=1.0)


class Match(BaseModel):
    outcome: Outcome
    clean: Detection | None
    degraded: Detection | None
    iou: float | None = None  # only for a spatial match: retained or class change
    confidence_change: float | None = None  # degraded minus clean, for a spatial match


class FrameStability(BaseModel):
    index: int
    matches: list[Match]
    retained: int
    dropped: int
    introduced: int
    class_changes: int
    confidence_loss: float
    score: float  # the weighted sum of the four values above it, bar `retained`


class Count(BaseModel):
    count: int
    total: int
    rate: float | None  # None when there is nothing to count, never a flattering 0 or 1


class ConfidenceShift(BaseModel):
    value: float | None  # median of degraded minus clean over retained pairs
    pairs: int


class StabilityReport(BaseModel):
    confidence_threshold: float
    iou_threshold: float
    weights: ScoreWeights
    frames_evaluated: int
    retention: Count  # retained of all clean detections
    introduced: Count  # introduced of all degraded detections
    class_changes: Count  # class changes of all clean detections
    median_confidence_shift: ConfidenceShift
    frames: list[FrameStability]


def iou(a: Box, b: Box) -> float:
    width = min(a.x2, b.x2) - max(a.x1, b.x1)
    height = min(a.y2, b.y2) - max(a.y1, b.y1)
    if width <= 0 or height <= 0:
        return 0.0
    overlap = width * height
    union = (a.x2 - a.x1) * (a.y2 - a.y1) + (b.x2 - b.x1) * (b.y2 - b.y1) - overlap
    return overlap / union


def match_frame(clean: list[Detection], degraded: list[Detection]) -> list[Match]:
    """Match one frame's clean and degraded detections. Thresholding is the caller's job."""
    matches: list[Match] = []
    free_clean, free_degraded = set(range(len(clean))), set(range(len(degraded)))

    for same_label, outcome in ((True, "retained"), (False, "class_change")):
        pairs = []
        for i, j in product(free_clean, free_degraded):
            if (clean[i].label == degraded[j].label) == same_label:
                overlap = iou(clean[i].box, degraded[j].box)
                if overlap >= IOU_THRESHOLD - 1e-9:  # float slack, so exactly 0.5 counts
                    pairs.append((overlap, i, j))
        # Highest IoU first; indices break ties, so the result never depends on set order.
        for overlap, i, j in sorted(pairs, key=lambda p: (-p[0], p[1], p[2])):
            if i in free_clean and j in free_degraded:
                free_clean.remove(i)
                free_degraded.remove(j)
                change = degraded[j].confidence - clean[i].confidence
                matches.append(
                    Match(outcome=outcome, clean=clean[i], degraded=degraded[j], iou=overlap, confidence_change=change)
                )

    matches += [Match(outcome="dropped", clean=clean[i], degraded=None) for i in sorted(free_clean)]
    matches += [Match(outcome="introduced", clean=None, degraded=degraded[j]) for j in sorted(free_degraded)]
    return matches


def frame_stability(result: FrameResult) -> FrameStability:
    def confident(detections: list[Detection]) -> list[Detection]:
        return [d for d in detections if d.confidence >= STABILITY_THRESHOLD]

    matches = match_frame(confident(result.clean), confident(result.degraded))
    count = {outcome: sum(m.outcome == outcome for m in matches) for outcome in get_args(Outcome)}
    loss = sum(max(-m.confidence_change, 0.0) for m in matches if m.confidence_change is not None)
    score = (
        WEIGHTS.dropped * count["dropped"]
        + WEIGHTS.introduced * count["introduced"]
        + WEIGHTS.class_changes * count["class_change"]
        + WEIGHTS.confidence_loss * loss
    )
    return FrameStability(
        index=result.index,
        matches=matches,
        retained=count["retained"],
        dropped=count["dropped"],
        introduced=count["introduced"],
        class_changes=count["class_change"],
        confidence_loss=loss,
        score=score,
    )


def stability_report(results: list[FrameResult]) -> StabilityReport:
    frames = [frame_stability(result) for result in results]
    retained = sum(f.retained for f in frames)
    class_changes = sum(f.class_changes for f in frames)
    introduced = sum(f.introduced for f in frames)
    clean_total = retained + class_changes + sum(f.dropped for f in frames)
    degraded_total = retained + class_changes + introduced
    shifts = [m.confidence_change for f in frames for m in f.matches if m.outcome == "retained"]
    return StabilityReport(
        confidence_threshold=STABILITY_THRESHOLD,
        iou_threshold=IOU_THRESHOLD,
        weights=WEIGHTS,
        frames_evaluated=len(frames),
        retention=_count(retained, clean_total),
        introduced=_count(introduced, degraded_total),
        class_changes=_count(class_changes, clean_total),
        median_confidence_shift=ConfidenceShift(value=statistics.median(shifts) if shifts else None, pairs=len(shifts)),
        frames=frames,
    )


def _count(count: int, total: int) -> Count:
    return Count(count=count, total=total, rate=count / total if total else None)
