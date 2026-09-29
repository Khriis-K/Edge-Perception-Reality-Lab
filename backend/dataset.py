"""SeeingThroughFog dataset adapter: which parts are present, and where a sample's camera image lives.

The dataset folder is fixed at startup. Nothing here takes a path from the browser: frames are looked up by
sample id, and an id must match the dataset's naming scheme, so it can never name a file outside the folder.
"""

import re
from dataclasses import dataclass
from pathlib import Path

DATASET_ENV_VAR = "EDGE_LAB_DATASET"

# Sample ids look like 2018-02-12_15-39-23_00100 (recording date_time_frame).
SAMPLE_ID = re.compile(r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_\d{5}")


@dataclass(frozen=True)
class RequiredPart:
    key: str
    name: str
    folder: str  # relative to the dataset root, with forward slashes
    suffix: str


REQUIRED_PARTS = [
    RequiredPart("camera", "Tone-mapped left camera images (8-bit)", "cam_stereo_left_lut", ".png"),
    RequiredPart("labels", "Ground-truth labels", "gt_labels/cam_left_labels_TMP", ".txt"),
    RequiredPart("metadata", "Environment metadata (weather, road, illumination)", "labeltool_labels", ".json"),
]
CAMERA = REQUIRED_PARTS[0]

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


class FrameNotFound(LookupError):
    pass


def check_readiness(root: Path | None) -> DatasetStatus:
    """Check the dataset folder for each required part. Reads the disk on every call."""
    if root is None:
        return _unchecked(
            None,
            "No dataset folder is configured. Start the app with --dataset PATH or set "
            f"{DATASET_ENV_VAR}, then restart. Synthetic mode works without the dataset.",
            "Not checked: no dataset folder configured.",
        )
    if not root.exists():
        return _unchecked(root, f"Dataset folder not found: {root}", "Not checked: dataset folder not found.")
    if not root.is_dir():
        return _unchecked(root, f"The dataset path is not a folder: {root}", "Not checked: dataset path is not a folder.")

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
    return PartStatus(part.key, part.name, part.folder, present, message, detail)


def _unchecked(root: Path | None, message: str, part_message: str) -> DatasetStatus:
    parts = [_status(part, False, part_message, message) for part in REQUIRED_PARTS]
    return DatasetStatus(root is not None, None if root is None else str(root), False, message, parts, NOT_NEEDED)
