"""Finished experiments on local disk, under an id derived from every setting that affects results.

Starting a run whose id is already stored reuses the stored results instead of running inference again.
A job writes into its own staging folder and, once every frame is done, adds experiment.json and renames the
folder into place. So a cancelled, failed or crashed run never leaves a complete-looking entry, and a job only
ever deletes its own staging folder, never another job's results.

Layout: <cache>/<id>/experiment.json and <cache>/<id>/frames/<variant>/<index>.jpg;
jobs in progress under <cache>/.staging/<job id>/.
Cached artifacts are for local use only. Deleting the folder, or any entry in it, is always safe.
"""

import hashlib
import json
import os
import re
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import get_args

from pydantic import ValidationError

from backend.detection import ModelInfo
from backend.experiment import DegradationSettings, Experiment, FrameVariant

# A sha256 hex digest, as experiment_id() makes. Checked before any path is built from an id, so an id from a
# URL can never name a file outside the cache (on Windows a backslash would otherwise act as a separator).
EXPERIMENT_ID = re.compile(r"[0-9a-f]{64}")

_fingerprints: dict[tuple[Path, int, int], str] = {}


def experiment_id(
    input_fingerprint: str,
    model: ModelInfo,
    class_mapping_version: int,
    confidence_floor: float,
    degradation: DegradationSettings,
) -> str:
    """The same settings always give the same id; changing any of them gives another. The model's runtime is left
    out: the same weights under another onnxruntime build are the same model version."""
    key = {
        "input": input_fingerprint,
        "model": {"name": model.name, "version": model.version},
        "class_mapping_version": class_mapping_version,
        "confidence_floor": confidence_floor,
        "degradation": degradation.model_dump(),
    }
    return hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()


def fingerprint(path: Path) -> str:
    """sha256 of the file's content. Remembered until the file's size or modification time changes."""
    stat = path.stat()
    key = (path.resolve(), stat.st_size, stat.st_mtime_ns)
    if key not in _fingerprints:
        digest = hashlib.sha256()
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1 << 20), b""):
                digest.update(chunk)
        _fingerprints[key] = digest.hexdigest()
    return _fingerprints[key]


@dataclass(frozen=True)
class CacheEntry:
    experiment: Experiment
    saved_at: datetime


class ExperimentCache:
    def __init__(self, root: Path):
        self.root = root
        # Parsed experiments by id, with the file's mtime: every frame request needs its experiment.
        self._loaded: dict[str, tuple[int, Experiment]] = {}
        # Whatever is staged now was left by a server that stopped mid-run.
        shutil.rmtree(self.root / ".staging", ignore_errors=True)

    def load(self, experiment_id: str) -> Experiment | None:
        entry = self._entry(experiment_id)
        return entry.experiment if entry else None

    def staging(self, job_id: str) -> Path:
        """Where a job writes its frames until it commits. Its name never matches an experiment id."""
        return self.root / ".staging" / job_id

    def open_staging(self, job_id: str) -> Path:
        """Make a job's staging folder, ready for frame_in(). Made once: if it is deleted mid-run, writing the next
        frame fails the run, rather than quietly recreating it and caching a run with frames missing."""
        folder = self.staging(job_id)
        for variant in get_args(FrameVariant):
            self.frame_in(folder, variant, 0).parent.mkdir(parents=True)
        return folder

    def commit(self, folder: Path, experiment: Experiment) -> None:
        """Make a staged run a complete entry: experiment.json first, then the whole folder moves into place."""
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "experiment.json").write_text(experiment.model_dump_json())
        target = self.root / experiment.id
        shutil.rmtree(target, ignore_errors=True)  # an entry that no longer loaded, since it was re-run
        os.replace(folder, target)

    @staticmethod
    def frame_in(folder: Path, variant: FrameVariant, index: int) -> Path:
        return folder / "frames" / variant / f"{index}.jpg"

    def frame_file(self, experiment_id: str, variant: FrameVariant, index: int) -> Path:
        return self.frame_in(self.root / experiment_id, variant, index)

    def entries(self) -> list[CacheEntry]:
        """Every complete experiment, newest first."""
        if not self.root.is_dir():
            return []
        entries = [entry for folder in self.root.iterdir() if (entry := self._entry(folder.name))]
        return sorted(entries, key=lambda entry: entry.saved_at, reverse=True)

    def size_bytes(self) -> int:
        total = 0
        for path in self.root.rglob("*"):
            try:
                total += path.stat().st_size if path.is_file() else 0
            except OSError:  # removed while we walked
                pass
        return total

    def _experiment_file(self, experiment_id: str) -> Path:
        return self.root / experiment_id / "experiment.json"

    def _entry(self, experiment_id: str) -> CacheEntry | None:
        if not EXPERIMENT_ID.fullmatch(experiment_id):
            return None
        path = self._experiment_file(experiment_id)
        try:
            mtime = path.stat().st_mtime_ns
            loaded = self._loaded.get(experiment_id)
            if loaded is None or loaded[0] != mtime:
                loaded = mtime, Experiment.model_validate_json(path.read_bytes())
                self._loaded[experiment_id] = loaded
        except (OSError, ValidationError):  # missing (never finished, or deleted by hand) or unreadable
            self._loaded.pop(experiment_id, None)
            return None
        return CacheEntry(experiment=loaded[1], saved_at=datetime.fromtimestamp(mtime / 1e9, UTC))
