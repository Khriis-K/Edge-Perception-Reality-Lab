"""Stability of detections under a degradation, relative to the clean frame: matching and metrics."""

from collections import Counter

import pytest

from backend.detection import Box, Detection
from backend.jobs import FrameResult
from backend.stability import WEIGHTS, match_frame, stability_report

LEFT = (0.1, 0.1, 0.3, 0.5)
RIGHT = (0.6, 0.1, 0.8, 0.5)


def det(label, confidence=0.9, box=LEFT):
    return Detection(label=label, confidence=confidence, box=Box(x1=box[0], y1=box[1], x2=box[2], y2=box[3]))


def shifted(box, dx):
    return (box[0] + dx, box[1], box[2] + dx, box[3])


def outcomes(matches):
    """(outcome, clean label, degraded label) per match, order-independent."""
    return Counter((m.outcome, m.clean and m.clean.label, m.degraded and m.degraded.label) for m in matches)


# Shifting a 0.2-wide box right by d leaves an overlap of 0.2 - d, so IoU = (0.2 - d) / (0.2 + d).
IOU_ONE_THIRD = 0.1  # shift giving IoU 1/3: no match
IOU_HALF = 0.2 / 3  # shift giving IoU exactly 0.5: the threshold itself
IOU_0_6 = 0.05  # shift giving IoU 0.6

MATCH_CASES = {
    "both frames empty": ([], [], []),
    "same box, same label": ([det("car")], [det("car", 0.7)], [("retained", "car", "car")]),
    "clean detection with nothing in the degraded frame": ([det("car")], [], [("dropped", "car", None)]),
    "degraded detection with nothing in the clean frame": ([], [det("car")], [("introduced", None, "car")]),
    "same box, different label": ([det("car")], [det("truck")], [("class_change", "car", "truck")]),
    "same label but too little overlap": (
        [det("car")],
        [det("car", box=shifted(LEFT, IOU_ONE_THIRD))],
        [("dropped", "car", None), ("introduced", None, "car")],
    ),
    "overlap exactly at the IoU threshold matches": (
        [det("car")],
        [det("car", box=shifted(LEFT, IOU_HALF))],
        [("retained", "car", "car")],
    ),
    "different label with too little overlap is not a class change": (
        [det("car")],
        [det("truck", box=shifted(LEFT, IOU_ONE_THIRD))],
        [("dropped", "car", None), ("introduced", None, "truck")],
    ),
    "two objects far apart, each kept": (
        [det("car", box=LEFT), det("person", box=RIGHT)],
        [det("person", box=RIGHT), det("car", box=LEFT)],
        [("retained", "car", "car"), ("retained", "person", "person")],
    ),
    "one clean box can match only one degraded box": (
        [det("car")],
        [det("car"), det("car", 0.5)],
        [("introduced", None, "car"), ("retained", "car", "car")],
    ),
    "overlapping clean boxes: the closer one keeps the single degraded box": (
        [det("car", box=LEFT), det("car", box=shifted(LEFT, 0.04))],
        [det("car", box=shifted(LEFT, 0.035))],
        [("dropped", "car", None), ("retained", "car", "car")],
    ),
    "a same-label match wins over a better-overlapping different label": (
        [det("car")],
        [det("truck"), det("car", box=shifted(LEFT, IOU_0_6))],
        [("introduced", None, "truck"), ("retained", "car", "car")],
    ),
    "leftover boxes after same-label matching can still be a class change": (
        [det("car", box=LEFT), det("person", box=RIGHT)],
        [det("car", box=LEFT), det("bicycle", box=RIGHT)],
        [("class_change", "person", "bicycle"), ("retained", "car", "car")],
    ),
}


@pytest.mark.parametrize(("clean", "degraded", "expected"), MATCH_CASES.values(), ids=MATCH_CASES.keys())
def test_match_frame(clean, degraded, expected):
    assert outcomes(match_frame(clean, degraded)) == Counter(expected)


def test_of_two_overlapping_clean_boxes_the_better_overlap_is_retained():
    near, far = det("car", 0.8, box=shifted(LEFT, 0.04)), det("car", 0.9, box=LEFT)
    matches = match_frame([far, near], [det("car", box=shifted(LEFT, 0.035))])

    [retained] = [m for m in matches if m.outcome == "retained"]
    assert retained.clean == near
    assert retained.iou == pytest.approx(0.195 / 0.205)


def test_a_match_records_its_iou_and_confidence_change():
    [match] = match_frame([det("car", 0.9)], [det("car", 0.6, box=shifted(LEFT, IOU_0_6))])

    assert match.iou == pytest.approx(0.6)
    assert match.confidence_change == pytest.approx(-0.3)


def test_unmatched_detections_have_no_iou_or_confidence_change():
    dropped, introduced = sorted(
        match_frame([det("car")], [det("person", box=RIGHT)]), key=lambda m: m.outcome
    )

    assert (dropped.outcome, dropped.iou, dropped.confidence_change) == ("dropped", None, None)
    assert (introduced.outcome, introduced.iou, introduced.confidence_change) == ("introduced", None, None)


def frame(index, clean, degraded):
    return FrameResult(index=index, clean=clean, degraded=degraded)


def test_detections_below_the_stability_threshold_are_left_out():
    report = stability_report([frame(0, [det("car", 0.9), det("person", 0.2, box=RIGHT)], [det("car", 0.9)])])

    assert report.confidence_threshold == 0.25
    assert [m.outcome for m in report.frames[0].matches] == ["retained"]
    assert (report.retention.count, report.retention.total) == (1, 1)


def test_an_unchanged_clip_is_perfectly_stable():
    """The null case: a degradation that changes nothing must score as no change, not as noise."""
    same = [det("car", 0.9), det("person", 0.4, box=RIGHT)]
    report = stability_report([frame(i, same, same) for i in range(3)])

    assert (report.retention.count, report.retention.total, report.retention.rate) == (6, 6, 1.0)
    assert (report.introduced.count, report.introduced.total, report.introduced.rate) == (0, 6, 0.0)
    assert (report.class_changes.count, report.class_changes.total) == (0, 6)
    assert (report.median_confidence_shift.value, report.median_confidence_shift.pairs) == (0.0, 6)
    assert [f.score for f in report.frames] == [0, 0, 0]


def test_a_clip_with_no_detections_has_no_rates_rather_than_perfect_ones():
    report = stability_report([frame(0, [], []), frame(1, [], [])])

    assert (report.retention.count, report.retention.total, report.retention.rate) == (0, 0, None)
    assert (report.introduced.count, report.introduced.total, report.introduced.rate) == (0, 0, None)
    assert (report.class_changes.count, report.class_changes.total, report.class_changes.rate) == (0, 0, None)
    assert (report.median_confidence_shift.value, report.median_confidence_shift.pairs) == (None, 0)
    assert [f.score for f in report.frames] == [0, 0]


def test_clip_metrics_count_every_frame():
    report = stability_report(
        [
            # retained (0.9 -> 0.5), dropped
            frame(0, [det("car", 0.9), det("person", 0.8, box=RIGHT)], [det("car", 0.5)]),
            # retained (0.6 -> 0.7), introduced
            frame(1, [det("car", 0.6)], [det("car", 0.7), det("person", 0.8, box=RIGHT)]),
            # class change, retained (0.8 -> 0.6)
            frame(
                2,
                [det("car", 0.9), det("person", 0.8, box=RIGHT)],
                [det("truck", 0.9), det("person", 0.6, box=RIGHT)],
            ),
        ]
    )

    # Every clean detection is retained, class-changed or dropped: 3 + 1 + 1 of 5.
    assert (report.retention.count, report.retention.total, report.retention.rate) == (3, 5, 0.6)
    assert (report.class_changes.count, report.class_changes.total, report.class_changes.rate) == (1, 5, 0.2)
    # 1 of the 5 degraded detections is new.
    assert (report.introduced.count, report.introduced.total, report.introduced.rate) == (1, 5, 0.2)
    # Retained shifts are -0.4, +0.1, -0.2: the median is -0.2. Class changes don't count.
    assert report.median_confidence_shift.value == pytest.approx(-0.2)
    assert report.median_confidence_shift.pairs == 3
    assert report.frames_evaluated == 3


def test_median_of_an_even_number_of_shifts_is_the_mean_of_the_middle_two():
    report = stability_report(
        [frame(0, [det("car", 0.9), det("person", 0.9, box=RIGHT)], [det("car", 0.8), det("person", 0.5, box=RIGHT)])]
    )

    assert report.median_confidence_shift.value == pytest.approx(-0.25)


def test_worst_frame_score_adds_each_weighted_contribution():
    report = stability_report(
        [
            frame(
                0,
                [det("car", 0.9, box=LEFT), det("person", 0.9, box=RIGHT), det("bus", 0.9, box=(0.1, 0.6, 0.3, 0.9))],
                [det("car", 0.6, box=LEFT), det("bicycle", 0.9, box=RIGHT), det("dog", 0.9, box=(0.6, 0.6, 0.8, 0.9))],
            )
        ]
    )

    [scored] = report.frames
    assert (scored.retained, scored.dropped, scored.introduced, scored.class_changes) == (1, 1, 1, 1)
    assert scored.confidence_loss == pytest.approx(0.3)
    assert scored.score == pytest.approx(3.3)
    assert report.weights == WEIGHTS


def test_a_class_change_also_adds_the_confidence_it_lost():
    report = stability_report([frame(0, [det("car", 0.9)], [det("truck", 0.4)])])

    [scored] = report.frames
    assert scored.class_changes == 1
    assert scored.confidence_loss == pytest.approx(0.5)
    assert scored.score == pytest.approx(1.5)


def test_a_confidence_gain_is_not_a_loss():
    report = stability_report([frame(0, [det("car", 0.6)], [det("car", 0.9)])])

    assert report.frames[0].confidence_loss == 0
    assert report.frames[0].score == 0


def test_weights_are_one_detection_each_and_one_per_unit_of_confidence_lost():
    assert WEIGHTS.model_dump() == {"dropped": 1.0, "introduced": 1.0, "class_changes": 1.0, "confidence_loss": 1.0}
