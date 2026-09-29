"""YOLOX pre- and post-processing, tested on hand-built tensors so no weights are needed."""

import math

import numpy as np
import pytest

from backend.yolox_runner import COCO_CLASSES, INPUT_SIZE, decode, letterbox

CAR = COCO_CLASSES.index("car")
PERSON = COCO_CLASSES.index("person")
ROWS = sum((INPUT_SIZE // stride) ** 2 for stride in (8, 16, 32))  # 3549 anchors at 416 px


def raw_output():
    """A raw YOLOX head output with nothing detected: objectness 0 everywhere."""
    return np.zeros((ROWS, 5 + len(COCO_CLASSES)), np.float32)


def put(raw, *, cell, offset=(0.5, 0.5), size_in_strides=4, obj=0.9, cls=CAR, cls_score=1.0):
    """Place one prediction on the stride-8 grid at `cell` = (column, row)."""
    column, row = cell
    anchor = row * (INPUT_SIZE // 8) + column
    raw[anchor, 0:2] = offset
    raw[anchor, 2:4] = math.log(size_in_strides)
    raw[anchor, 4] = obj
    raw[anchor, 5 + cls] = cls_score


# --- letterbox ------------------------------------------------------------------


def test_letterbox_scales_to_fit_and_pads_bottom_right_with_gray():
    image = np.full((208, 832, 3), 200, np.uint8)  # 4:1, so ratio is 416/832 = 0.5

    tensor, ratio = letterbox(image)

    assert tensor.shape == (1, 3, INPUT_SIZE, INPUT_SIZE)
    assert tensor.dtype == np.float32
    assert ratio == 0.5
    assert tensor[0, :, :104, :].min() == 200  # scaled image: 104 rows
    assert tensor[0, :, 104:, :].max() == 114  # padding below it


# --- decode ---------------------------------------------------------------------


def test_one_prediction_decodes_to_a_normalized_box():
    raw = raw_output()
    # Center (10.5, 5.5) cells * 8 px = (84, 44); size 4 strides * 8 px = 32 px.
    put(raw, cell=(10, 5))

    [detection] = decode(raw, ratio=1.0, width=INPUT_SIZE, height=INPUT_SIZE, confidence_threshold=0.5)

    assert detection.label == "car"
    assert detection.confidence == pytest.approx(0.9)
    box = detection.box
    assert (box.x1, box.y1, box.x2, box.y2) == pytest.approx(
        (68 / INPUT_SIZE, 28 / INPUT_SIZE, 100 / INPUT_SIZE, 60 / INPUT_SIZE)
    )


def test_boxes_are_mapped_back_through_the_letterbox_ratio():
    raw = raw_output()
    put(raw, cell=(10, 5))

    # The original image was twice the input size, so ratio 0.5: same normalized box.
    [detection] = decode(raw, ratio=0.5, width=2 * INPUT_SIZE, height=2 * INPUT_SIZE, confidence_threshold=0.5)

    assert detection.box.x1 == pytest.approx(68 / INPUT_SIZE)
    assert detection.box.y2 == pytest.approx(60 / INPUT_SIZE)


def test_confidence_is_objectness_times_class_score():
    raw = raw_output()
    put(raw, cell=(10, 5), obj=0.8, cls_score=0.5)

    assert decode(raw, 1.0, INPUT_SIZE, INPUT_SIZE, confidence_threshold=0.41) == []
    [detection] = decode(raw, 1.0, INPUT_SIZE, INPUT_SIZE, confidence_threshold=0.39)
    assert detection.confidence == pytest.approx(0.4)


def test_overlapping_boxes_of_one_class_are_suppressed_to_the_strongest():
    raw = raw_output()
    put(raw, cell=(10, 5), obj=0.9)
    put(raw, cell=(11, 5), obj=0.7, offset=(-0.4, 0.5))  # 0.8 px to the right of the first

    detections = decode(raw, 1.0, INPUT_SIZE, INPUT_SIZE, confidence_threshold=0.5)

    assert [d.confidence for d in detections] == [pytest.approx(0.9)]


def test_overlapping_boxes_of_different_classes_are_both_kept():
    raw = raw_output()
    put(raw, cell=(10, 5), obj=0.9, cls=CAR)
    put(raw, cell=(11, 5), obj=0.7, offset=(-0.4, 0.5), cls=PERSON)

    labels = sorted(d.label for d in decode(raw, 1.0, INPUT_SIZE, INPUT_SIZE, confidence_threshold=0.5))

    assert labels == ["car", "person"]


def test_boxes_past_the_image_edge_are_clipped_to_zero_one():
    raw = raw_output()
    put(raw, cell=(0, 0), offset=(0, 0), size_in_strides=4)  # centered on the corner

    [detection] = decode(raw, 1.0, INPUT_SIZE, INPUT_SIZE, confidence_threshold=0.5)

    assert (detection.box.x1, detection.box.y1) == (0.0, 0.0)


def test_nothing_above_threshold_gives_an_empty_list():
    assert decode(raw_output(), 1.0, INPUT_SIZE, INPUT_SIZE, confidence_threshold=0.05) == []
