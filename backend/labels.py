"""KITTI-format ground-truth labels. Only the class and the 2D box are read; the 3D fields are ignored."""

import math
from dataclasses import dataclass

# KITTI's 15 standard fields: type truncated occluded alpha | left top right bottom | h w l x y z rotation_y.
# SeeingThroughFog appends more (rotation quaternion, per-sensor visibility), which are ignored too.
MIN_FIELDS = 15

# The dataset's four main classes, the ones metrics are scored on. Fallback classes (Vehicle, Obstacle), DontCare
# and the *_is_group variants are not among them.
MAIN_CLASSES = ("PassengerCar", "LargeVehicle", "RidableVehicle", "Pedestrian")


@dataclass(frozen=True)
class Box:
    label: str
    left: float
    top: float
    right: float
    bottom: float


@dataclass(frozen=True)
class LabelProblem:
    line: int  # 1-based
    message: str


def parse_labels(text: str) -> tuple[list[Box], list[LabelProblem]]:
    """The file's 2D boxes, plus one problem per line that could not be read. Never raises on bad input."""
    boxes, problems = [], []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        box, reason = _parse_line(line)
        if box is None:
            problems.append(LabelProblem(number, f"line {number}: {reason}: {line.strip()!r}"))
        else:
            boxes.append(box)
    return boxes, problems


def _parse_line(line: str) -> tuple[Box | None, str]:
    fields = line.split()
    if len(fields) < MIN_FIELDS:
        return None, f"expected at least {MIN_FIELDS} fields, found {len(fields)}"
    try:
        left, top, right, bottom = (float(f) for f in fields[4:8])
    except ValueError:
        return None, "the 2D box is not numeric"
    if not all(math.isfinite(v) for v in (left, top, right, bottom)):
        return None, "the 2D box is not finite"
    if right <= left or bottom <= top:
        return None, "the 2D box is empty"
    return Box(fields[0], left, top, right, bottom), ""
