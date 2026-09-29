"""Degradation behavior on known images: shape kept, seeded output reproducible, effects grow with severity."""

import cv2
import numpy as np
import pytest

from backend.degradations import KINDS, RANDOMIZED, degrade, parameters
from backend.samples import SAMPLES
from backend.video import open_video
from backend.yolox_runner import MODEL_PATH, YoloxRunner

SEVERITIES = [0.0, 0.25, 0.5, 0.75, 1.0]


def known_image(height=96, width=128):
    """Mid-gray 8 px checkerboard over a left-to-right ramp: edges to blur, levels to darken."""
    ys, xs = np.mgrid[:height, :width]
    checker = np.where((ys // 8 + xs // 8) % 2 == 0, 60, -60)
    ramp = xs * 80 // width
    gray = np.clip(128 + checker + ramp - 40, 0, 255).astype(np.uint8)
    return np.dstack([gray, gray, gray])


def run(kind, severity, image=None, seed=0):
    return degrade(known_image() if image is None else image, kind, severity, np.random.default_rng(seed))


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("severity", SEVERITIES)
def test_output_keeps_the_image_size_and_8_bit_color(kind, severity):
    image = known_image(height=90, width=131)  # odd sizes, so JPEG's 8x8 blocks don't line up

    out = degrade(image, kind, severity, np.random.default_rng(0))

    assert out.shape == image.shape
    assert out.dtype == np.uint8


@pytest.mark.parametrize("kind", ["darkness", "blur", "fog", "noise"])
def test_severity_zero_leaves_the_image_unchanged(kind):
    np.testing.assert_array_equal(run(kind, 0.0), known_image())


# --- seeds -------------------------------------------------------------------------


@pytest.mark.parametrize("kind", KINDS)
def test_the_same_seed_gives_identical_output(kind):
    np.testing.assert_array_equal(run(kind, 0.6, seed=7), run(kind, 0.6, seed=7))


def test_noise_depends_on_the_seed():
    assert not np.array_equal(run("noise", 0.6, seed=7), run("noise", 0.6, seed=8))


def test_randomized_kinds_are_exactly_the_ones_that_use_the_seed():
    varies = {kind for kind in KINDS if not np.array_equal(run(kind, 0.6, seed=1), run(kind, 0.6, seed=2))}

    assert varies == RANDOMIZED == {"noise"}


# --- effects grow with severity ------------------------------------------------------


def sharpness(image):
    return cv2.Laplacian(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()


def error(image):
    return np.abs(image.astype(float) - known_image()).mean()


def test_darkness_gets_monotonically_darker():
    means = [run("darkness", s).mean() for s in SEVERITIES]

    assert means == sorted(means, reverse=True)
    assert len(set(means)) == len(means)  # strictly: every step is darker
    assert means[-1] < 0.15 * means[0]


def test_blur_removes_more_detail_as_severity_rises():
    values = [sharpness(run("blur", s)) for s in SEVERITIES]

    assert values == sorted(values, reverse=True)
    assert len(set(values)) == len(values)


def test_jpeg_artifacts_grow_with_severity():
    errors = [error(run("jpeg", s)) for s in SEVERITIES]

    assert errors == sorted(errors)
    assert len(set(errors)) == len(errors)


def test_fog_washes_out_contrast_toward_the_airlight():
    contrasts = [run("fog", s).std() for s in SEVERITIES]

    assert contrasts == sorted(contrasts, reverse=True)
    assert contrasts[-1] < 0.15 * contrasts[0]
    assert run("fog", 1.0).mean() == pytest.approx(255 * 0.8, abs=20)


def test_noise_moves_pixels_further_as_severity_rises():
    errors = [error(run("noise", s)) for s in SEVERITIES]

    assert errors == sorted(errors)
    assert errors[0] == 0 < errors[1]


# --- parameters and severity range -----------------------------------------------------


@pytest.mark.parametrize(
    "kind, severity, expected",
    [
        ("darkness", 0.5, {"gain": 0.55}),
        ("blur", 0.5, {"sigma_px": 5.0}),
        ("fog", 1.0, {"transmission": 0.1, "airlight": 0.8}),
        ("noise", 0.2, {"sigma": 10.0}),
        ("jpeg", 0.0, {"quality": 95}),
        ("jpeg", 1.0, {"quality": 5}),
    ],
)
def test_parameters_are_derived_from_severity(kind, severity, expected):
    assert parameters(kind, severity) == pytest.approx(expected)


@pytest.mark.parametrize("severity", [-0.01, 1.01, float("nan")])
def test_severities_outside_zero_to_one_are_rejected(severity):
    with pytest.raises(ValueError, match="between 0 and 1"):
        run("fog", severity)


# --- the real detector notices ------------------------------------------------------------


@pytest.mark.model
@pytest.mark.parametrize("kind", ["darkness", "fog"])
def test_at_maximum_severity_the_real_detector_finds_clearly_fewer_objects(kind):
    # The stub returns the same boxes whatever the image, so only the real model can show that a
    # transform actually hides objects. A margin, not just "fewer", so a near no-op can't pass.
    runner = YoloxRunner(MODEL_PATH)
    with open_video(SAMPLES["krakow-city-driving"].path) as video:
        every_tenth = list(video.frames())[::10]
    rng = np.random.default_rng(0)

    clean = sum(len(runner.detect(frame, 0.3)) for frame in every_tenth)
    degraded = sum(len(runner.detect(degrade(frame, kind, 1.0, rng), 0.3)) for frame in every_tenth)

    assert clean > 0
    assert degraded < 0.75 * clean
