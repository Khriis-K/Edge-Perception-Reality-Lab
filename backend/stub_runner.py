"""A deterministic stand-in detector, so tests and demos never need weights or a GPU.

It "detects" the bright block the synthetic sample video draws: a car around the block, plus a
low-confidence person and a very-low-confidence bicycle beside it, so thresholds have something
to filter. A frame with no bright block gives no detections.
"""

import time

import numpy as np

from backend.detection import Box, Detection, ModelInfo, TimedDetections, check_input

BRIGHT = 200  # the sample's car is drawn at 240; road and background are far darker


class StubRunner:
    def __init__(self, simulated_latency_s: float = 0.0):
        # Latency lets the browser tests watch a job make progress; unit tests leave it at 0.
        self.simulated_latency_s = simulated_latency_s
        self.info = ModelInfo(name="Stub detector", version="fixture-1", runtime="none (deterministic stub)")

    def detect_timed(self, image: np.ndarray, confidence_threshold: float) -> TimedDetections:
        """With no model session, the whole detect call counts as inference."""
        start = time.perf_counter()
        detections = self.detect(image, confidence_threshold)
        return TimedDetections(detections, time.perf_counter() - start)

    def detect(self, image: np.ndarray, confidence_threshold: float) -> list[Detection]:
        check_input(image, confidence_threshold)
        if self.simulated_latency_s:
            time.sleep(self.simulated_latency_s)

        rows, cols = np.nonzero(image.min(axis=2) >= BRIGHT)
        if rows.size == 0:
            return []

        height, width = image.shape[:2]
        car = Box(x1=cols.min() / width, y1=rows.min() / height, x2=(cols.max() + 1) / width, y2=(rows.max() + 1) / height)
        # Fixed offsets from the car, clamped to the frame.
        person = _clamped(car.x2 + 0.02, car.y1 - 0.15, car.x2 + 0.08, car.y2)
        bicycle = _clamped(car.x1 - 0.1, car.y1, car.x1 - 0.02, car.y2)
        detections = [
            Detection(label="car", confidence=0.9, box=car),
            Detection(label="person", confidence=0.3, box=person),
            Detection(label="bicycle", confidence=0.02, box=bicycle),
        ]
        return [d for d in detections if d.confidence >= confidence_threshold]


def _clamped(x1: float, y1: float, x2: float, y2: float) -> Box:
    return Box(x1=_unit(x1), y1=_unit(y1), x2=_unit(x2), y2=_unit(y2))


def _unit(value: float) -> float:
    return min(max(value, 0.0), 1.0)
