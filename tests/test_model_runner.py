"""Model-runner contract: every runner returns normalized, labelled detections and stable metadata.

The stub runs everywhere. The real YOLOX runner needs fetched weights, so its cases carry the
`model` marker and are deselected by default: run them with `pytest -m model`.
"""

import numpy as np
import pytest

from backend.detection import InvalidInput
from backend.stub_runner import StubRunner
from backend.yolox_runner import MODEL_PATH, YoloxRunner
from scripts.make_sample_video import HEIGHT, WIDTH, car_box, draw_frame


@pytest.fixture(params=["stub", pytest.param("yolox", marks=pytest.mark.model)])
def runner(request):
    return StubRunner() if request.param == "stub" else YoloxRunner(MODEL_PATH)


def black_image(height=HEIGHT, width=WIDTH):
    return np.zeros((height, width, 3), np.uint8)


# --- output shape -------------------------------------------------------------


def test_detections_have_label_confidence_and_normalized_box(runner):
    # Threshold 0 so the real model returns its raw boxes too; it finds nothing confident here.
    detections = runner.detect(draw_frame(10), confidence_threshold=0.0)

    assert detections  # otherwise the checks below pass vacuously
    for detection in detections:
        assert isinstance(detection.label, str) and detection.label
        assert 0 <= detection.confidence <= 1
        box = detection.box
        assert 0 <= box.x1 <= box.x2 <= 1
        assert 0 <= box.y1 <= box.y2 <= 1


def test_threshold_drops_lower_confidence_detections(runner):
    image = draw_frame(10)

    low = runner.detect(image, confidence_threshold=0.0)
    high = runner.detect(image, confidence_threshold=0.5)

    assert low
    assert all(d.confidence >= 0.5 for d in high)
    assert [d for d in low if d.confidence >= 0.5] == high


def test_an_empty_scene_gives_an_empty_list(runner):
    assert runner.detect(black_image(), confidence_threshold=0.5) == []


# --- invalid input --------------------------------------------------------------


@pytest.mark.parametrize(
    "image",
    [
        None,
        np.zeros((HEIGHT, WIDTH), np.uint8),  # grayscale
        np.zeros((HEIGHT, WIDTH, 4), np.uint8),  # BGRA
        np.zeros((0, 0, 3), np.uint8),  # empty
        np.zeros((HEIGHT, WIDTH, 3), np.float32),  # not 8-bit
    ],
    ids=["none", "grayscale", "four-channel", "empty", "float"],
)
def test_invalid_images_are_rejected(runner, image):
    with pytest.raises(InvalidInput):
        runner.detect(image, confidence_threshold=0.5)


@pytest.mark.parametrize("threshold", [-0.1, 1.5, float("nan")])
def test_thresholds_outside_zero_to_one_are_rejected(runner, threshold):
    with pytest.raises(InvalidInput):
        runner.detect(black_image(), confidence_threshold=threshold)


# --- metadata -------------------------------------------------------------------


def test_model_metadata_is_filled_in_and_stable(runner):
    before = runner.info.model_copy()

    runner.detect(draw_frame(0), confidence_threshold=0.1)

    assert runner.info == before
    assert before.name and before.version and before.runtime


# --- stub specifics -------------------------------------------------------------


@pytest.mark.parametrize("index", [0, 20, 47])
def test_stub_finds_the_fixture_car_where_it_was_drawn(index):
    [car] = [d for d in StubRunner().detect(draw_frame(index), 0.5) if d.label == "car"]

    x1, y1, x2, y2 = car_box(index)
    assert car.confidence == 0.9
    assert (car.box.x1, car.box.y1, car.box.x2, car.box.y2) == pytest.approx(
        (x1 / WIDTH, y1 / HEIGHT, x2 / WIDTH, y2 / HEIGHT)
    )


def test_stub_returns_the_same_detections_for_the_same_frame():
    assert StubRunner().detect(draw_frame(5), 0.01) == StubRunner().detect(draw_frame(5), 0.01)


def test_stub_reports_a_low_confidence_person_and_a_detection_below_the_default_floor():
    confidences = sorted(d.confidence for d in StubRunner().detect(draw_frame(5), 0.0))

    assert confidences == [0.02, 0.3, 0.9]
