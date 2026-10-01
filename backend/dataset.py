"""SeeingThroughFog dataset adapter: which parts are present, where a sample's camera image lives, and which
condition each sample belongs to.

The dataset folder is fixed at startup. Nothing here takes a path from the browser: frames are looked up by
sample id, and an id must match the dataset's naming scheme, so it can never name a file outside the folder.
"""

import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from backend.conditions import Excluded, assign_condition
from backend.labels import MAIN_CLASSES, Box, parse_labels

DATASET_ENV_VAR = "EDGE_LAB_DATASET"

# Sample ids look like 2018-02-12_15-39-23_00100 (recording date_time_frame).
SAMPLE_ID = re.compile(r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_\d{5}")


@dataclass(frozen=True)
class RequiredPart:
    key: str
    name: str
    folder: str  # relative to the dataset root, with forward slashes
    suffix: str


CAMERA = RequiredPart("camera", "Tone-mapped left camera images (8-bit)", "cam_stereo_left_lut", ".png")
LABELS = RequiredPart("labels", "Ground-truth labels", "gt_labels/cam_left_labels_TMP", ".txt")
# The refined metadata, not the original labeltool_labels: see backend/conditions.py.
METADATA = RequiredPart(
    "metadata", "Environment metadata, refined (fog, precipitation, daytime)", "labeltool_labels_refined", ".json"
)
REQUIRED_PARTS = [CAMERA, LABELS, METADATA]

NO_LABEL_FILE = "no label file"
MALFORMED_LABELS = "malformed label line"
METADATA_UNREADABLE = "metadata unreadable"
LABELS_UNREADABLE = "label file unreadable"

# Everything else in the download. Skipping these saves most of the storage.
NOT_NEEDED = [
    "Lidar point clouds (lidar_hdl64_*, lidar_vlp32_*)",
    "Radar targets (radar_targets)",
    "Gated NIR camera images (gated*)",
    "Thermal / far-infrared camera (fir_axis)",
    "12-bit raw camera images and history frames (cam_stereo_left, cam_stereo_left_raw_history_*)",
    "Road friction and weather station logs (road_friction, weather_station)",
]


@dataclass(frozen=True)
class PartStatus:
    key: str
    name: str
    folder: str
    checked: bool  # False when the dataset folder itself is unset or unusable
    present: bool
    message: str  # plain language, for the user
    detail: str  # what exactly was checked, for development


@dataclass(frozen=True)
class DatasetStatus:
    configured: bool
    root: str | None
    ready: bool
    message: str
    parts: list[PartStatus]
    not_needed: list[str]


@dataclass(frozen=True)
class Frame:
    """A usable sample: its condition is determined and its labels parsed cleanly."""

    id: str
    condition: str
    class_counts: dict[str, int]  # main classes only


@dataclass(frozen=True)
class DatasetIndex:
    frames: list[Frame]  # usable samples, each with a determined condition
    excluded: dict[str, int]  # reason -> number of samples
    problems: list[str]  # located messages for unreadable files and malformed label lines


class FrameNotFound(LookupError):
    pass


def check_readiness(root: Path | None) -> DatasetStatus:
    """Check the dataset folder for each required part. Reads the disk on every call."""
    if root is None:
        return _unchecked(
            None,
            "No dataset folder is configured. Start the app with --dataset PATH or set "
            f"{DATASET_ENV_VAR}, then restart. Synthetic mode works without the dataset.",
            reason="no dataset folder configured",
        )
    if not root.exists():
        return _unchecked(root, f"Dataset folder not found: {root}", reason="dataset folder not found")
    if not root.is_dir():
        return _unchecked(root, f"The dataset path is not a folder: {root}", reason="dataset path is not a folder")

    parts = [_check_part(root, part) for part in REQUIRED_PARTS]
    missing = [p.name for p in parts if not p.present]
    message = "Missing: " + "; ".join(missing) + "." if missing else "All three required parts are present."
    return DatasetStatus(True, str(root), not missing, message, parts, NOT_NEEDED)


def camera_image(root: Path | None, sample_id: str) -> Path:
    """The tone-mapped camera image for a sample, or FrameNotFound."""
    if root is None:
        raise FrameNotFound("No dataset folder is configured.")
    if not SAMPLE_ID.fullmatch(sample_id):
        raise FrameNotFound(f"Not a dataset sample id: {sample_id!r}")
    image = root / CAMERA.folder / f"{sample_id}{CAMERA.suffix}"
    if not image.is_file():
        raise FrameNotFound(f"No camera image for sample {sample_id} in the dataset.")
    return image


def read_labels(root: Path, sample_id: str) -> list[Box]:
    """A sample's ground-truth boxes, in pixels. Raises FrameNotFound, OSError, or ValueError on a malformed line:
    a silently dropped box would turn a correct detection into a false alarm."""
    if not SAMPLE_ID.fullmatch(sample_id):
        raise FrameNotFound(f"Not a dataset sample id: {sample_id!r}")
    label_file = root / LABELS.folder / f"{sample_id}{LABELS.suffix}"
    boxes, bad_lines = parse_labels(label_file.read_text(encoding="utf-8"))
    if bad_lines:
        raise ValueError(f"{label_file.name} {bad_lines[0].message}")
    return boxes


def index_dataset(root: Path) -> DatasetIndex:
    """Every sample's condition and main-class object counts. Reads every metadata and label file, so it is slow on
    the real dataset (minutes on a cold disk): callers should build it once."""
    frames, excluded, problems = [], Counter(), []
    for meta_file in sorted((root / METADATA.folder).glob(f"*{METADATA.suffix}")):
        sample_id = meta_file.stem
        if not SAMPLE_ID.fullmatch(sample_id):
            continue
        result = _index_sample(root, meta_file)
        if isinstance(result, Frame):
            frames.append(result)
        else:
            reason, messages = result
            excluded[reason] += 1
            problems.extend(messages)
    return DatasetIndex(frames, dict(excluded), problems)


def _index_sample(root: Path, meta_file: Path) -> Frame | tuple[str, list[str]]:
    """The sample's Frame, or why it is excluded plus any located problem messages."""
    try:
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        return METADATA_UNREADABLE, [f"{meta_file.name}: {error}"]
    condition = assign_condition(meta)
    if isinstance(condition, Excluded):
        return condition.reason, []

    label_file = root / LABELS.folder / f"{meta_file.stem}{LABELS.suffix}"
    try:
        boxes, bad_lines = parse_labels(label_file.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return NO_LABEL_FILE, []
    except (OSError, UnicodeDecodeError) as error:
        return LABELS_UNREADABLE, [f"{label_file.name}: {error}"]
    if bad_lines:
        # The whole frame goes: a silently dropped ground-truth box would turn a correct detection into a false alarm.
        return MALFORMED_LABELS, [f"{label_file.name} {p.message}" for p in bad_lines]

    counts = Counter(b.label for b in boxes if b.label in MAIN_CLASSES)
    return Frame(meta_file.stem, condition, dict(counts))


def _check_part(root: Path, part: RequiredPart) -> PartStatus:
    folder = root / part.folder
    zipped = folder.with_name(folder.name + ".zip")

    if not folder.is_dir():
        if zipped.is_file():
            message = f"{part.name} is still zipped. Extract {zipped.name} into the dataset folder."
        else:
            message = f"Missing: {part.name}. Expected a {part.folder} folder in the dataset folder."
        return _status(part, False, message, f"Checked {folder}: not a folder.")

    count = sum(1 for f in folder.iterdir() if f.suffix == part.suffix and f.is_file())
    if count == 0:
        message = f"{part.name}: the {part.folder} folder is empty (no {part.suffix} files)."
        return _status(part, False, message, f"Checked {folder}: 0 {part.suffix} files.")
    return _status(part, True, f"Found {count} {part.suffix} files.", f"Checked {folder}: {count} {part.suffix} files.")


def _status(part: RequiredPart, present: bool, message: str, detail: str) -> PartStatus:
    return PartStatus(part.key, part.name, part.folder, True, present, message, detail)


def _unchecked(root: Path | None, message: str, reason: str) -> DatasetStatus:
    """Every part reported as not checked, because the dataset folder itself is unset or unusable."""
    detail = f"Checked {root}: {reason}." if root else f"{DATASET_ENV_VAR} and --dataset are both unset."
    parts = [
        PartStatus(part.key, part.name, part.folder, False, False, f"Not checked: {reason}.", detail)
        for part in REQUIRED_PARTS
    ]
    return DatasetStatus(root is not None, None if root is None else str(root), False, message, parts, NOT_NEEDED)
