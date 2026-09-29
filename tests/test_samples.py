"""Bundled sample videos: each one decodes, and the real clip gives the real detector something to find."""

import pytest

from backend.samples import SAMPLES
from backend.video import open_video
from backend.yolox_runner import MODEL_PATH, YoloxRunner


@pytest.mark.parametrize("sample_id", SAMPLES)
def test_every_bundled_sample_decodes(sample_id):
    with open_video(SAMPLES[sample_id].path) as video:
        first = next(video.frames())

    assert first.ndim == 3


@pytest.mark.model
def test_the_real_detector_finds_people_and_cars_throughout_the_city_clip():
    # The null-case check: a sample where the real model finds nothing can't show what degradation does.
    runner = YoloxRunner(MODEL_PATH)
    with open_video(SAMPLES["krakow-city-driving"].path) as video:
        every_tenth = list(video.frames())[::10]

    detections = [runner.detect(frame, confidence_threshold=0.3) for frame in every_tenth]

    assert all(detections), "some frames have no detections"
    labels = {d.label for frame in detections for d in frame}
    assert {"person", "car"} <= labels
