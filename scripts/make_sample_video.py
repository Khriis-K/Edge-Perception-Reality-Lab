"""Generate the synthetic sample video: one bright "car" block driving across a dark road.

It is both the bundled sample and the canonical test fixture. The stub runner finds the block,
so tests know exactly where the detections should be. Regenerate with:

    .venv/Scripts/python.exe scripts/make_sample_video.py
"""

import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.samples import SAMPLES  # noqa: E402

WIDTH, HEIGHT = 320, 192
FRAMES = 48
FPS = 12
CAR_W, CAR_H = 60, 30
CAR_Y = 120


def car_box(index: int) -> tuple[int, int, int, int]:
    """Pixel box (x1, y1, x2, y2) of the car in frame `index`; it moves 5 px per frame."""
    x = 10 + 5 * index
    return x, CAR_Y, x + CAR_W, CAR_Y + CAR_H


def draw_frame(index: int) -> np.ndarray:
    frame = np.full((HEIGHT, WIDTH, 3), 30, np.uint8)
    frame[100:170] = 70  # road
    x1, y1, x2, y2 = car_box(index)
    frame[y1:y2, x1:x2] = 240
    return frame


def write_synthetic_video(path: Path, frames: int = FRAMES) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (WIDTH, HEIGHT))
    for index in range(frames):
        writer.write(draw_frame(index))
    writer.release()


if __name__ == "__main__":
    target = SAMPLES["synthetic-traffic"].path
    write_synthetic_video(target)
    print(f"Wrote {target}")
