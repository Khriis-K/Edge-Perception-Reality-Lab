"""A frame's outcomes at every display threshold, so the frame viewer can change threshold without asking again."""

from backend.benchmark import (
    BenchmarkFrame,
    FrameScore,
    GroundTruth,
    evaluate_condition,
    frame_levels,
    match_indices,
)
from backend.class_mapping import map_detections
from backend.detection import Box, Detection

LEFT = (0.1, 0.1, 0.3, 0.5)
RIGHT = (0.6, 0.1, 0.8, 0.5)


def det(label, confidence, box=LEFT):
    return Detection(label=label, confidence=confidence, box=Box(x1=box[0], y1=box[1], x2=box[2], y2=box[3]))


def gt(label, box=LEFT):
    return GroundTruth(label=label, box=Box(x1=box[0], y1=box[1], x2=box[2], y2=box[3]))


def level_at(levels, threshold):
    """The lookup the frontend does: the last level, highest cutoff first, whose cutoff is at or above the threshold."""
    chosen = levels[0]
    for level in levels[1:]:
        if level.min_confidence >= threshold:
            chosen = level
    return chosen


def test_matches_point_into_the_frame_s_predictions_and_truths_by_index():
    truths = [gt("DontCare", RIGHT), gt("PassengerCar")]
    predictions = [det("PassengerCar", 0.4, RIGHT), det("PassengerCar", 0.9)]

    matches = match_indices(predictions, truths)

    assert [(m.outcome, m.prediction, m.truth) for m in matches] == [("hit", 1, 1), ("ignored", 0, 0)]
    assert matches[0].iou == 1.0


def test_a_miss_points_at_its_truth_only():
    matches = match_indices([], [gt("Pedestrian")])

    assert [(m.outcome, m.prediction, m.truth, m.iou) for m in matches] == [("miss", None, 0, None)]


def test_levels_start_with_nothing_shown_then_one_per_distinct_confidence_highest_first():
    predictions = [det("PassengerCar", 0.4, RIGHT), det("PassengerCar", 0.9), det("Pedestrian", 0.4)]

    levels = frame_levels("f", predictions, [gt("PassengerCar")])

    assert [level.min_confidence for level in levels] == [None, 0.9, 0.4]
    assert [(m.outcome, m.truth) for m in levels[0].matches] == [("miss", 0)]
    assert levels[0].score.misses == 1
    assert sorted(m.prediction for m in levels[2].matches if m.prediction is not None) == [0, 1, 2]


def test_a_level_is_matched_afresh_not_filtered_from_the_full_match():
    # Shown together, the car takes the PassengerCar as a hit and the truck is a false alarm. With only the truck
    # shown, the PassengerCar is free, so the truck is a class confusion.
    predictions = [det("LargeVehicle", 0.8), det("PassengerCar", 0.4)]

    levels = frame_levels("f", predictions, [gt("PassengerCar")])

    truck_only, both = levels[1], levels[2]
    assert [(m.outcome, m.prediction, m.truth) for m in truck_only.matches] == [("class_confusion", 0, 0)]
    assert sorted((m.outcome, m.prediction) for m in both.matches) == [("false_alarm", 0), ("hit", 1)]


def test_every_threshold_finds_the_same_score_the_condition_reports():
    raw = [det("truck", 0.8), det("car", 0.4), det("person", 0.3, RIGHT), det("cat", 0.6, RIGHT)]
    truths = [gt("PassengerCar"), gt("Pedestrian", (0.4, 0.6, 0.5, 0.9))]
    levels = frame_levels("f", map_detections(raw), truths)

    for threshold in (0.0, 0.05, 0.3, 0.35, 0.4, 0.5, 0.8, 0.85, 1.0):
        reported = evaluate_condition([BenchmarkFrame(id="f", predictions=raw, truths=truths)], threshold)
        expected = FrameScore(**reported.frame_results[0].model_dump(exclude={"matches"}))
        assert level_at(levels, threshold).score == expected, threshold
