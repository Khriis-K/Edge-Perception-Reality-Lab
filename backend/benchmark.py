"""Benchmark scoring: detections against human-labelled ground truth. See backend/class_mapping.py for which classes
count and which labels are ignore regions.

Boxes are in 0-1 image coordinates on both sides. Matching, per frame, with predictions already mapped to dataset
classes, each pass taking predictions in descending confidence:
1. Hit: the prediction takes the unmatched object of its own class it overlaps most, at IoU >= IOU_THRESHOLD.
2. Class confusion: a prediction left over takes, the same way, an unmatched object of another class.
3. Ignored: a prediction still left over that overlaps an ignore region at IoU >= IOU_THRESHOLD. One region can
   forgive any number of predictions.
4. False alarm: any other prediction. Objects still unmatched are misses.
Hits come first, so a correct prediction is never shadowed by a more confident wrong-class one on the same object.

AP, per class: predictions ranked by confidence, a prediction counting as a true positive only when it is a hit.
A class confusion is a false positive for the predicted class and an unfound object of the true one. AP is the area
under the interpolated precision-recall curve (all points; precision at recall r is the best precision at any recall
>= r). Tied confidences form one point, so AP never depends on how ties are ordered. With no objects AP is undefined
(None); with objects but no hits it is 0. mAP is the mean over the classes whose AP is defined.

Worst-frame score, per frame, at the display threshold:
    misses x 1 + false alarms x 1 + class confusions x 1
Hits and ignored predictions add nothing.

Every metric carries its object and frame counts, and is flagged low n below LOW_N_OBJECTS objects.
"""

import math
from itertools import groupby
from typing import Literal, get_args

from pydantic import BaseModel

from backend.class_mapping import map_detections, truth_role
from backend.detection import Box, Detection
from backend.labels import MAIN_CLASSES
from backend.stability import iou
from backend.subset import LOW_N_OBJECTS

IOU_THRESHOLD = 0.5
IOU_SLACK = 1e-9  # float slack, so an overlap of exactly the threshold counts

Outcome = Literal["hit", "miss", "false_alarm", "class_confusion", "ignored"]


class ScoreWeights(BaseModel):
    misses: float
    false_alarms: float
    class_confusions: float


WEIGHTS = ScoreWeights(misses=1.0, false_alarms=1.0, class_confusions=1.0)


class GroundTruth(BaseModel):
    label: str  # the dataset's label, whatever its role
    box: Box


class BenchmarkFrame(BaseModel):
    id: str
    predictions: list[Detection]  # raw detector output, COCO labels, down to the confidence floor
    truths: list[GroundTruth]


class BenchmarkMatch(BaseModel):
    outcome: Outcome
    prediction: Detection | None  # labelled with its dataset class
    truth: GroundTruth | None  # the ignore region, for an ignored prediction
    iou: float | None = None  # for a spatial match: hit, class confusion or ignored


class FrameBenchmark(BaseModel):
    id: str
    matches: list[BenchmarkMatch]
    hits: int
    misses: int
    false_alarms: int
    class_confusions: int
    ignored: int
    score: float  # the weighted sum of misses, false alarms and class confusions


class PRPoint(BaseModel):
    threshold: float  # predictions at or above this confidence
    precision: float
    recall: float | None  # None when the class has no objects


class ClassMetrics(BaseModel):
    class_name: str
    objects: int
    frames: int
    low_n: bool
    ap: float | None
    predictions: int  # at or above the display threshold
    hits: int  # at or above the display threshold
    precision: float | None  # None when nothing is predicted at the display threshold
    recall: float | None  # None when there are no objects
    pr_curve: list[PRPoint]


class ConditionMetrics(BaseModel):
    iou_threshold: float
    display_threshold: float
    weights: ScoreWeights
    low_n_objects: int
    frames: int
    objects: int
    low_n: bool  # some class has fewer than low_n_objects objects
    map: float | None
    classes: list[ClassMetrics]  # in MAIN_CLASSES order
    frame_results: list[FrameBenchmark]  # in input order, scored at the display threshold


def match_frame(predictions: list[Detection], truths: list[GroundTruth]) -> list[BenchmarkMatch]:
    """Match one frame's predictions, already mapped to dataset classes, to its ground truth. Thresholding is the
    caller's job."""
    objects = [t for t in truths if truth_role(t.label) == "object"]
    regions = [t for t in truths if truth_role(t.label) == "ignore"]
    order = sorted(range(len(predictions)), key=lambda i: (-predictions[i].confidence, i))
    free = set(range(len(objects)))
    matched: dict[int, BenchmarkMatch] = {}

    for same_class, outcome in ((True, "hit"), (False, "class_confusion")):
        for i in order:
            if i in matched:
                continue
            best = _best_overlap(
                predictions[i].box, [(j, objects[j]) for j in free if (objects[j].label == predictions[i].label) == same_class]
            )
            if best is not None:
                j, overlap = best
                free.remove(j)
                matched[i] = BenchmarkMatch(outcome=outcome, prediction=predictions[i], truth=objects[j], iou=overlap)

    for i in order:
        if i in matched:
            continue
        best = _best_overlap(predictions[i].box, list(enumerate(regions)))
        if best is None:
            matched[i] = BenchmarkMatch(outcome="false_alarm", prediction=predictions[i], truth=None)
        else:
            j, overlap = best
            matched[i] = BenchmarkMatch(outcome="ignored", prediction=predictions[i], truth=regions[j], iou=overlap)

    misses = [BenchmarkMatch(outcome="miss", prediction=None, truth=objects[j]) for j in sorted(free)]
    return [matched[i] for i in order] + misses


def _best_overlap(box: Box, candidates: list[tuple[int, GroundTruth]]) -> tuple[int, float] | None:
    """The candidate overlapping `box` most at or above the threshold; the lowest index breaks ties."""
    best = None
    for j, truth in candidates:
        overlap = iou(box, truth.box)
        if overlap >= IOU_THRESHOLD - IOU_SLACK and (best is None or (overlap, -j) > (best[1], -best[0])):
            best = (j, overlap)
    return best


def frame_benchmark(frame_id: str, matches: list[BenchmarkMatch]) -> FrameBenchmark:
    count = {outcome: sum(m.outcome == outcome for m in matches) for outcome in get_args(Outcome)}
    score = (
        WEIGHTS.misses * count["miss"]
        + WEIGHTS.false_alarms * count["false_alarm"]
        + WEIGHTS.class_confusions * count["class_confusion"]
    )
    return FrameBenchmark(
        id=frame_id,
        matches=matches,
        hits=count["hit"],
        misses=count["miss"],
        false_alarms=count["false_alarm"],
        class_confusions=count["class_confusion"],
        ignored=count["ignored"],
        score=score,
    )


def pr_curve(scored: list[tuple[float, bool]], objects: int) -> list[PRPoint]:
    """One point per distinct confidence, highest first. `scored` is (confidence, is a hit) per prediction."""
    points, hits, predicted = [], 0, 0
    for confidence, group in groupby(sorted(scored, key=lambda s: -s[0]), key=lambda s: s[0]):
        group = list(group)
        predicted += len(group)
        hits += sum(hit for _, hit in group)
        points.append(PRPoint(threshold=confidence, precision=hits / predicted, recall=hits / objects if objects else None))
    return points


def average_precision(curve: list[PRPoint], objects: int) -> float | None:
    """All-point interpolated AP over a curve from pr_curve."""
    if objects == 0:
        return None
    # Interpolate: each point's precision becomes the best precision at it or any lower threshold (higher recall).
    precisions = [p.precision for p in curve]
    for k in range(len(precisions) - 2, -1, -1):
        precisions[k] = max(precisions[k], precisions[k + 1])
    ap, previous_recall = 0.0, 0.0
    for point, precision in zip(curve, precisions):
        ap += (point.recall - previous_recall) * precision
        previous_recall = point.recall
    return ap


def evaluate_condition(frames: list[BenchmarkFrame], display_threshold: float) -> ConditionMetrics:
    """Per-class AP, PR curves and precision/recall at the display threshold, plus each frame's worst-frame score."""
    if math.isnan(display_threshold) or not 0 <= display_threshold <= 1:
        raise ValueError(f"Display threshold must be between 0 and 1, got {display_threshold}.")

    scored: dict[str, list[tuple[float, bool]]] = {c: [] for c in MAIN_CLASSES}
    objects = dict.fromkeys(MAIN_CLASSES, 0)
    frame_results = []
    for frame in frames:
        predictions = map_detections(frame.predictions)
        # Greedy matching in confidence order means the hits above any threshold are the same whether or not the
        # predictions below it are there, so one full match serves AP and every threshold.
        for match in match_frame(predictions, frame.truths):
            if match.prediction is not None:
                scored[match.prediction.label].append((match.prediction.confidence, match.outcome == "hit"))
        for truth in frame.truths:
            if truth_role(truth.label) == "object":
                objects[truth.label] += 1
        # Frame outcomes are matched afresh: a confusion depends on which objects the shown predictions left free.
        shown = [p for p in predictions if p.confidence >= display_threshold]
        frame_results.append(frame_benchmark(frame.id, match_frame(shown, frame.truths)))

    classes = [_class_metrics(c, scored[c], objects[c], len(frames), display_threshold) for c in MAIN_CLASSES]
    aps = [c.ap for c in classes if c.ap is not None]
    return ConditionMetrics(
        iou_threshold=IOU_THRESHOLD,
        display_threshold=display_threshold,
        weights=WEIGHTS,
        low_n_objects=LOW_N_OBJECTS,
        frames=len(frames),
        objects=sum(objects.values()),
        low_n=any(c.low_n for c in classes),
        map=sum(aps) / len(aps) if aps else None,
        classes=classes,
        frame_results=frame_results,
    )


def _class_metrics(
    class_name: str, scored: list[tuple[float, bool]], objects: int, frames: int, display_threshold: float
) -> ClassMetrics:
    curve = pr_curve(scored, objects)
    shown = [hit for confidence, hit in scored if confidence >= display_threshold]
    hits = sum(shown)
    return ClassMetrics(
        class_name=class_name,
        objects=objects,
        frames=frames,
        low_n=objects < LOW_N_OBJECTS,
        ap=average_precision(curve, objects),
        predictions=len(shown),
        hits=hits,
        precision=hits / len(shown) if shown else None,
        recall=hits / objects if objects else None,
        pr_curve=curve,
    )
