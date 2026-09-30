"""The real detector's timing, runtime record and providers. Needs the fetched weights: run with `pytest -m model`.

The latency budget is a generous local tripwire for accidental regressions, not a claim about any hardware.
"""

import statistics

import onnxruntime as ort
import pytest

from backend.samples import SAMPLES
from backend.video import open_video
from backend.yolox_runner import CPU, MODEL_PATH, YoloxRunner, choose_providers
from scripts.make_sample_video import draw_frame

pytestmark = pytest.mark.model

WARM_UPS = 3
TIMED_RUNS = 20
# YOLOX-Nano at 416 px normally takes tens of milliseconds on a laptop CPU.
INFERENCE_BUDGET_S = 0.5
TOLERANCE = 1e-3


@pytest.fixture(scope="module")
def cpu_runner():
    return YoloxRunner(MODEL_PATH, providers=[CPU])


def test_inference_stays_within_a_generous_local_budget(cpu_runner):
    image = draw_frame(10)
    for _ in range(WARM_UPS):
        cpu_runner.detect_timed(image, 0.05)

    times = [cpu_runner.detect_timed(image, 0.05).inference_s for _ in range(TIMED_RUNS)]

    assert 0 < statistics.median(times) < INFERENCE_BUDGET_S


def test_timed_detection_returns_the_same_detections_as_detect(cpu_runner):
    image = draw_frame(10)

    assert cpu_runner.detect_timed(image, 0.05).detections == cpu_runner.detect(image, 0.05)


def test_the_model_record_names_its_size_runtime_and_provider(cpu_runner):
    info = cpu_runner.info

    assert info.size_bytes == MODEL_PATH.stat().st_size
    assert info.runtime == f"onnxruntime {ort.__version__}"
    assert info.provider == CPU


def test_the_providers_the_app_picks_give_the_cpu_detections_within_tolerance(cpu_runner):
    # On a machine with CUDA or DirectML this compares it with the CPU; on a CPU-only one, the default path with the
    # explicit CPU one.
    providers = choose_providers(ort.get_available_providers())
    chosen = YoloxRunner(MODEL_PATH)
    assert chosen.info.provider == providers[0]

    # Real frames: the synthetic ones give no detections, which would make the comparison [] == [].
    with open_video(SAMPLES["krakow-city-driving"].path) as video:
        every_tenth = list(video.frames())[::10]

    for image in every_tenth:
        expected = cpu_runner.detect(image, 0.3)
        actual = chosen.detect(image, 0.3)

        assert expected, "a frame with no detections compares nothing"
        assert [d.label for d in actual] == [d.label for d in expected]
        for a, e in zip(actual, expected):
            assert a.confidence == pytest.approx(e.confidence, abs=TOLERANCE)
            assert a.box.model_dump() == pytest.approx(e.box.model_dump(), abs=TOLERANCE)
