"""The images an exported report can embed, as data URIs so report.html stays one self-contained file.

Frames of a bundled clip are cached JPEGs and go in as they are. A dataset frame is a large tone-mapped PNG, so it is
shrunk to a JPEG first; it is only ever read when the user has switched dataset imagery on.
"""

import base64
from pathlib import Path

import cv2

from backend.dataset import FrameNotFound, camera_image

DATASET_FRAME_WIDTH = 640
JPEG_QUALITY = 80


def jpeg_uri(data: bytes) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii")


def cached_frame_uri(path: Path | None) -> str | None:
    """A cached frame as a data URI; None when the cache no longer has it (deleted by hand)."""
    return jpeg_uri(path.read_bytes()) if path is not None and path.is_file() else None


def dataset_frame_uri(root: Path | None, sample_id: str) -> str | None:
    """A dataset frame, scaled to DATASET_FRAME_WIDTH, as a data URI; None when it can't be read."""
    try:
        image = cv2.imread(str(camera_image(root, sample_id)), cv2.IMREAD_COLOR)
    except FrameNotFound:
        return None
    if image is None:
        return None
    height, width = image.shape[:2]
    if width > DATASET_FRAME_WIDTH:
        image = cv2.resize(image, (DATASET_FRAME_WIDTH, round(height * DATASET_FRAME_WIDTH / width)), interpolation=cv2.INTER_AREA)
    ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    return jpeg_uri(encoded.tobytes()) if ok else None
