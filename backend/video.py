"""Video decoding with OpenCV. Frames come out as 8-bit BGR arrays, in order."""

from collections.abc import Iterator
from pathlib import Path

import cv2
import numpy as np


class VideoError(Exception):
    """A video can't be decoded. The message is plain enough to show a user."""


class Video:
    def __init__(self, capture: cv2.VideoCapture):
        self._capture = capture
        # The container's count, used for progress. It can be off by a frame or two for some codecs.
        self.frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))

    def frames(self) -> Iterator[np.ndarray]:
        while True:
            ok, frame = self._capture.read()
            if not ok:
                return
            yield frame

    def __enter__(self) -> "Video":
        return self

    def __exit__(self, *exc) -> None:
        self._capture.release()


def open_video(path: Path) -> Video:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened() or capture.get(cv2.CAP_PROP_FRAME_COUNT) <= 0:
        capture.release()
        raise VideoError(f"The video {path.name} could not be opened. It may be missing, corrupted, or in an unsupported format.")
    return Video(capture)
