"""Benchmark scoring against ground truth: matching, the worst-frame score, AP and per-class metrics."""

from collections import Counter

import pytest

from backend.benchmark import (
    WEIGHTS,
    BenchmarkFrame,
    GroundTruth,
    average_precision,
    evaluate_condition,
    frame_benchmark,
    match_frame,
    pr_curve,
)
from backend.detection import Box, Detection
from backend.subset import LOW_N_OBJECTS

LEFT = (0.1, 0.1, 0.3, 0.5)
RIGHT = (0.6, 0.1, 0.8, 0.5)


def make_box(box):
    return Box(x1=box[0], y1=box[1], x2=box[2], y2=box[3])


def det(label, confidence=0.9, box=LEFT):
    return Detection(label=label, confidence=confidence, box=make_box(box))


def gt(label, box=LEFT):
    return GroundTruth(label=label, box=make_box(box))


def shifted(box, dx):
    return (box[0] + dx, box[1], box[2] + dx, box[3])


def outcomes(matches):
    """(outcome, predicted label, ground-truth label) per match, order-independent."""
    return Counter((m.outcome, m.prediction and m.prediction.label, m.truth and m.truth.label) for m in matches)


# Shifting a 0.2-wide box right by d leaves an overlap of 0.2 - d, so IoU = (0.2 - d) / (0.2 + d).
IOU_ONE_THIRD = 0.1  # no match
IOU_HALF = 0.2 / 3  # exactly the threshold
IOU_0_6 = 0.05

# --- matching ---------------------------------------------------------------

MATCH_CASES = {
    "empty frame": ([], [], []),
    "hit": ([det("PassengerCar")], [gt("PassengerCar")], [("hit", "PassengerCar", "PassengerCar")]),
    "miss": ([], [gt("Pedestrian")], [("miss", None, "Pedestrian")]),
    "false alarm": ([det("Pedestrian")], [], [("false_alarm", "Pedestrian", None)]),
    "class confusion": (
        [det("LargeVehicle")],
        [gt("PassengerCar")],
        [("class_confusion", "LargeVehicle", "PassengerCar")],
    ),
    "same class but too little overlap": (
        [det("PassengerCar", box=shifted(LEFT, IOU_ONE_THIRD))],
        [gt("PassengerCar")],
        [("false_alarm", "PassengerCar", None), ("miss", None, "PassengerCar")],
    ),
    "overlap exactly at the IoU threshold is a hit": (
        [det("PassengerCar", box=shifted(LEFT, IOU_HALF))],
        [gt("PassengerCar")],
        [("hit", "PassengerCar", "PassengerCar")],
    ),
    "different class with too little overlap is not a confusion": (
        [det("LargeVehicle", box=shifted(LEFT, IOU_ONE_THIRD))],
        [gt("PassengerCar")],
        [("false_alarm", "LargeVehicle", None), ("miss", None, "PassengerCar")],
    ),
    "prediction on a Vehicle fallback region is ignored": (
        [det("PassengerCar")],
        [gt("Vehicle")],
        [("ignored", "PassengerCar", "Vehicle")],
    ),
    "prediction on an Obstacle fallback region is ignored": (
        [det("Pedestrian")],
        [gt("Obstacle")],
        [("ignored", "Pedestrian", "Obstacle")],
    ),
    "prediction on a DontCare region is ignored": (
        [det("PassengerCar")],
        [gt("DontCare")],
        [("ignored", "PassengerCar", "DontCare")],
    ),
    "prediction on a group box is ignored": (
        [det("Pedestrian")],
        [gt("Pedestrian_is_group")],
        [("ignored", "Pedestrian", "Pedestrian_is_group")],
    ),
    "an ignore region nobody predicted on is neither hit nor miss": ([], [gt("Vehicle")], []),
    "too little overlap with an ignore region is still a false alarm": (
        [det("PassengerCar", box=shifted(LEFT, IOU_ONE_THIRD))],
        [gt("Vehicle")],
        [("false_alarm", "PassengerCar", None)],
    ),
    "one ignore region forgives several predictions": (
        [det("PassengerCar", 0.9), det("LargeVehicle", 0.8)],
        [gt("Vehicle")],
        [("ignored", "PassengerCar", "Vehicle"), ("ignored", "LargeVehicle", "Vehicle")],
    ),
    "labels outside the scheme are dropped, so a prediction on one is a false alarm": (
        [det("PassengerCar")],
        [gt("train")],
        [("false_alarm", "PassengerCar", None)],
    ),
    "a duplicate prediction on a hit object is a false alarm": (
        [det("PassengerCar", 0.9), det("PassengerCar", 0.6)],
        [gt("PassengerCar")],
        [("hit", "PassengerCar", "PassengerCar"), ("false_alarm", "PassengerCar", None)],
    ),
    "a hit beats a more confident wrong-class prediction on the same object": (
        [det("LargeVehicle", 0.9), det("PassengerCar", 0.5)],
        [gt("PassengerCar")],
        [("hit", "PassengerCar", "PassengerCar"), ("false_alarm", "LargeVehicle", None)],
    ),
    "a hit beats an ignore region under the same object": (
        [det("PassengerCar")],
        [gt("Vehicle"), gt("PassengerCar")],
        [("hit", "PassengerCar", "PassengerCar")],
    ),
    "a class confusion beats an ignore region": (
        [det("LargeVehicle")],
        [gt("Vehicle"), gt("PassengerCar")],
        [("class_confusion", "LargeVehicle", "PassengerCar")],
    ),
    "two objects far apart, each hit": (
        [det("Pedestrian", box=RIGHT), det("PassengerCar", box=LEFT)],
        [gt("PassengerCar", LEFT), gt("Pedestrian", RIGHT)],
        [("hit", "PassengerCar", "PassengerCar"), ("hit", "Pedestrian", "Pedestrian")],
    ),
}


@pytest.mark.parametrize("predictions, truths, expected", MATCH_CASES.values(), ids=MATCH_CASES.keys())
def test_match_frame(predictions, truths, expected):
    assert outcomes(match_frame(predictions, truths)) == Counter(expected)


def test_overlapping_objects_are_matched_greedily_by_confidence():
    # A overlaps both objects, B only the second. The more confident prediction picks its best object first.
    near, far = LEFT, shifted(LEFT, IOU_0_6)
    a = det("PassengerCar", 0.9, box=near)
    b = det("PassengerCar", 0.8, box=far)

    matches = match_frame([b, a], [gt("PassengerCar", far), gt("PassengerCar", near)])

    pairs = {(m.prediction.confidence, m.truth.box.x1) for m in matches}
    assert pairs == {(0.9, near[0]), (0.8, far[0])}
    assert all(m.outcome == "hit" for m in matches)


def test_the_more_confident_prediction_takes_a_contested_object():
    # The less confident prediction overlaps better, but confidence decides: that is how AP ranks them.
    loose = det("PassengerCar", 0.9, box=shifted(LEFT, IOU_0_6))
    tight = det("PassengerCar", 0.5, box=LEFT)

    matches = match_frame([tight, loose], [gt("PassengerCar")])

    hit = next(m for m in matches if m.outcome == "hit")
    assert hit.prediction.confidence == 0.9
    assert hit.iou == pytest.approx(0.6)


def test_spatial_matches_record_their_iou():
    matches = match_frame([det("LargeVehicle"), det("Pedestrian", box=RIGHT)], [gt("PassengerCar"), gt("Vehicle", RIGHT)])

    assert {m.outcome: m.iou for m in matches} == {"class_confusion": pytest.approx(1.0), "ignored": pytest.approx(1.0)}


# --- worst-frame score --------------------------------------------------------


def test_frame_benchmark_counts_each_outcome_and_weighs_the_score():
    matches = match_frame(
        [det("PassengerCar", box=LEFT), det("Pedestrian", box=(0.4, 0.6, 0.5, 0.9)), det("LargeVehicle", box=RIGHT)],
        [gt("PassengerCar", LEFT), gt("RidableVehicle", RIGHT), gt("Pedestrian", (0.0, 0.0, 0.05, 0.05))],
    )

    frame = frame_benchmark("f1", matches)

    assert (frame.hits, frame.misses, frame.false_alarms, frame.class_confusions, frame.ignored) == (1, 1, 1, 1, 0)
    assert frame.score == pytest.approx(
        WEIGHTS.misses * 1 + WEIGHTS.false_alarms * 1 + WEIGHTS.class_confusions * 1
    )
    assert frame.id == "f1"


def test_hits_and_ignored_predictions_do_not_add_to_the_score():
    frame = frame_benchmark("f", match_frame([det("PassengerCar"), det("Pedestrian", box=RIGHT)], [gt("PassengerCar"), gt("Vehicle", RIGHT)]))

    assert (frame.hits, frame.ignored, frame.score) == (1, 1, 0.0)


def test_weights_are_documented_values():
    assert (WEIGHTS.misses, WEIGHTS.false_alarms, WEIGHTS.class_confusions) == (1.0, 1.0, 1.0)


# --- PR curve and AP ---------------------------------------------------------


def test_hand_computed_average_precision():
    # 3 objects. Ranked: hit, false alarm, hit, false alarm; the third object is never found.
    # Points: (1, 1/3), (1/2, 1/3), (2/3, 2/3), (1/2, 2/3). Interpolated precision is 1 up to recall 1/3
    # and 2/3 up to recall 2/3, so AP = 1/3 * 1 + 1/3 * 2/3 = 5/9.
    scored = [(0.9, True), (0.8, False), (0.7, True), (0.6, False)]

    curve = pr_curve(scored, objects=3)

    assert [(p.threshold, p.precision, p.recall) for p in curve] == [
        (0.9, pytest.approx(1), pytest.approx(1 / 3)),
        (0.8, pytest.approx(1 / 2), pytest.approx(1 / 3)),
        (0.7, pytest.approx(2 / 3), pytest.approx(2 / 3)),
        (0.6, pytest.approx(1 / 2), pytest.approx(2 / 3)),
    ]
    assert average_precision(curve, objects=3) == pytest.approx(5 / 9)


def test_input_order_does_not_matter():
    scored = [(0.6, False), (0.9, True), (0.7, True), (0.8, False)]

    assert average_precision(pr_curve(scored, objects=3), objects=3) == pytest.approx(5 / 9)


@pytest.mark.parametrize("scored", [[(0.8, True), (0.8, False)], [(0.8, False), (0.8, True)]])
def test_tied_confidences_are_one_point_so_their_order_does_not_change_ap(scored):
    curve = pr_curve(scored, objects=1)

    assert [(p.threshold, p.precision, p.recall) for p in curve] == [(0.8, 0.5, 1.0)]
    assert average_precision(curve, objects=1) == pytest.approx(0.5)


def test_perfect_ranking_gives_ap_one():
    assert average_precision(pr_curve([(0.9, True), (0.5, True)], objects=2), objects=2) == pytest.approx(1.0)


def test_no_predictions_gives_ap_zero():
    # The null case: a detector that outputs nothing scores 0, not a flattering or missing value.
    assert average_precision(pr_curve([], objects=4), objects=4) == 0.0


def test_no_objects_leaves_ap_undefined():
    curve = pr_curve([(0.9, False)], objects=0)

    assert curve[0].recall is None
    assert average_precision(curve, objects=0) is None


# --- condition metrics -------------------------------------------------------


def frame(frame_id, predictions, truths):
    return BenchmarkFrame(id=frame_id, predictions=predictions, truths=truths)


def by_class(metrics):
    return {c.class_name: c for c in metrics.classes}


def test_condition_metrics_per_class():
    frames = [
        # COCO labels in, as the detector gives them.
        frame("a", [det("car", 0.9, LEFT), det("person", 0.4, RIGHT)], [gt("PassengerCar", LEFT), gt("Pedestrian", RIGHT)]),
        frame("b", [det("car", 0.8, RIGHT)], [gt("PassengerCar", LEFT)]),
    ]

    metrics = evaluate_condition(frames, display_threshold=0.5)
    car, pedestrian = by_class(metrics)["PassengerCar"], by_class(metrics)["Pedestrian"]

    assert (car.objects, car.frames, car.predictions, car.hits) == (2, 2, 2, 1)
    assert car.ap == pytest.approx(0.5)
    assert (car.precision, car.recall) == (pytest.approx(0.5), pytest.approx(0.5))
    # The pedestrian is hit at confidence 0.4: it counts for AP but not at the 0.5 display threshold.
    assert pedestrian.ap == pytest.approx(1.0)
    assert (pedestrian.predictions, pedestrian.hits, pedestrian.precision, pedestrian.recall) == (0, 0, None, 0.0)
    assert [c.class_name for c in metrics.classes] == ["PassengerCar", "LargeVehicle", "RidableVehicle", "Pedestrian"]


def test_classes_without_objects_have_no_ap_and_are_left_out_of_map():
    frames = [frame("a", [det("car", 0.9)], [gt("PassengerCar")]), frame("b", [det("person", 0.9)], [gt("PassengerCar")])]

    metrics = evaluate_condition(frames, display_threshold=0.5)

    assert by_class(metrics)["LargeVehicle"].ap is None
    assert by_class(metrics)["Pedestrian"].ap is None
    assert metrics.map == pytest.approx(0.5)  # PassengerCar alone: one hit of two objects at precision 1
    assert metrics.objects == 2
    assert metrics.frames == 2


def test_a_condition_with_no_objects_has_no_map():
    metrics = evaluate_condition([frame("a", [det("car")], [])], display_threshold=0.5)

    assert metrics.map is None


def test_low_n_flags_each_class_below_the_minimum_and_the_condition_with_it():
    enough = [frame(f"f{i}", [det("car")], [gt("PassengerCar")]) for i in range(LOW_N_OBJECTS)]
    too_few = enough[:-1]

    assert by_class(evaluate_condition(enough, 0.5))["PassengerCar"].low_n is False
    assert by_class(evaluate_condition(too_few, 0.5))["PassengerCar"].low_n is True
    # Other classes have no objects at all, so the condition as a whole is low n either way.
    assert by_class(evaluate_condition(enough, 0.5))["Pedestrian"].low_n is True
    assert evaluate_condition(enough, 0.5).low_n is True


def test_unmapped_predictions_are_not_false_alarms():
    metrics = evaluate_condition([frame("a", [det("dog", 0.9)], [gt("PassengerCar")])], display_threshold=0.5)

    result = metrics.frame_results[0]
    assert (result.false_alarms, result.misses) == (0, 1)
    assert sum(c.predictions for c in metrics.classes) == 0


def test_frame_results_use_the_display_threshold():
    frames = [frame("a", [det("car", 0.9, LEFT), det("car", 0.3, RIGHT)], [gt("PassengerCar", LEFT)])]

    strict = evaluate_condition(frames, display_threshold=0.5).frame_results[0]
    loose = evaluate_condition(frames, display_threshold=0.2).frame_results[0]

    assert (strict.hits, strict.false_alarms, strict.score) == (1, 0, 0.0)
    assert (loose.hits, loose.false_alarms, loose.score) == (1, 1, WEIGHTS.false_alarms)


def test_ignored_predictions_count_against_neither_precision_nor_ap():
    frames = [frame("a", [det("car", 0.9, LEFT), det("car", 0.95, RIGHT)], [gt("PassengerCar", LEFT), gt("Vehicle", RIGHT)])]

    car = by_class(evaluate_condition(frames, display_threshold=0.5))["PassengerCar"]

    assert (car.predictions, car.hits, car.precision) == (1, 1, 1.0)
    assert car.ap == pytest.approx(1.0)
    assert [(p.threshold, p.precision) for p in car.pr_curve] == [(0.9, 1.0)]


def test_class_frames_count_only_frames_holding_that_class():
    frames = [
        frame("a", [], [gt("PassengerCar"), gt("PassengerCar", RIGHT)]),
        frame("b", [], [gt("Pedestrian")]),
        frame("c", [], [gt("Vehicle")]),
    ]

    metrics = evaluate_condition(frames, display_threshold=0.5)

    assert {c.class_name: c.frames for c in metrics.classes} == {
        "PassengerCar": 1, "LargeVehicle": 0, "RidableVehicle": 0, "Pedestrian": 1,
    }
    assert metrics.frames == 3


def test_class_confusion_counts_against_both_classes_ap():
    # A car found as a truck: a false positive for LargeVehicle and an unfound PassengerCar.
    metrics = evaluate_condition([frame("a", [det("truck", 0.9)], [gt("PassengerCar")])], display_threshold=0.5)

    assert by_class(metrics)["PassengerCar"].ap == 0.0
    assert by_class(metrics)["LargeVehicle"].predictions == 1
    assert metrics.frame_results[0].class_confusions == 1
    assert metrics.frame_results[0].misses == 0


def test_the_result_records_its_settings():
    metrics = evaluate_condition([], display_threshold=0.4)

    assert metrics.display_threshold == 0.4
    assert metrics.iou_threshold == 0.5
    assert metrics.weights == WEIGHTS
    assert metrics.low_n_objects == LOW_N_OBJECTS


@pytest.mark.parametrize("threshold", [-0.1, 1.1, float("nan")])
def test_display_threshold_must_be_in_range(threshold):
    with pytest.raises(ValueError):
        evaluate_condition([], display_threshold=threshold)
