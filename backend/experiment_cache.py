"""Finished experiments on local disk, under an id derived from every setting that affects results.

Starting a run whose id is already stored reuses the stored results instead of running inference again.
A job writes into its own staging folder and, once every frame is done, adds experiment.json and renames the
folder into place. So a cancelled, failed or crashed run never leaves a complete-looking entry, and a job only
ever deletes its own staging folder, never another job's results.

Layout: a Synthetic run is <cache>/<id>/experiment.json and <cache>/<id>/frames/<variant>/<index>.jpg; a Benchmark
run is <cache>/<id>/benchmark.json alone (its images stay in the dataset), and so is a Synthetic run on dataset frames
<cache>/<id>/synthetic_frames.json alone (its degraded images are not kept). Any entry may also hold headlines.json,
the Findings headlines the user wrote for it. Jobs in progress are under
<cache>/.staging/<job id>/.
Cached artifacts are for local use only. Deleting the folder, or any entry in it, is always safe.
"""

import hashlib
import json
import os
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import get_args

from pydantic import ValidationError

from backend.benchmark_run import BenchmarkExperiment
from backend.detection import ModelInfo
from backend.experiment import DegradationSettings, Experiment, FrameVariant
from backend.subset import Manifest
from backend.synthetic_frames import SyntheticFramesExperiment

# A sha256 hex digest, as experiment_id() makes. Checked before any path is built from an id, so an id from a
# URL can never name a file outside the cache (on Windows a backslash would otherwise act as a separator).
EXPERIMENT_ID = re.compile(r"[0-9a-f]{64}")

# The file each kind of experiment is stored in. An entry holds one of them.
RECORD_FILES = {
    Experiment: "experiment.json",
    BenchmarkExperiment: "benchmark.json",
    SyntheticFramesExperiment: "synthetic_frames.json",
}
Record = Experiment | BenchmarkExperiment | SyntheticFramesExperiment
# The user's Findings headlines for a run, beside its record. Not part of the record, so not part of the id.
HEADLINES_FILE = "headlines.json"
# The Synthetic runs, on video and on dataset frames: the run history lists both.
SyntheticRecord = Experiment | SyntheticFramesExperiment

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
    return _digest(key)


def benchmark_experiment_id(
    manifest: Manifest, model: ModelInfo, class_mapping_version: int, confidence_floor: float
) -> str:
    """Like experiment_id(), with the whole subset manifest as the input. The dataset's files are not fingerprinted:
    see docs/adr/0002-what-the-experiment-id-covers.md."""
    key = {
        "mode": "benchmark",
        "manifest": asdict(manifest),
        "model": {"name": model.name, "version": model.version},
        "class_mapping_version": class_mapping_version,
        "confidence_floor": confidence_floor,
    }
    return _digest(key)


def synthetic_frames_experiment_id(
    manifest: Manifest,
    condition: str,
    model: ModelInfo,
    class_mapping_version: int,
    confidence_floor: float,
    degradation: DegradationSettings,
) -> str:
    """Like benchmark_experiment_id(), plus the clear condition degraded and the degradation, seed included."""
    key = {
        "mode": "synthetic-frames",
        "manifest": asdict(manifest),
        "condition": condition,
        "model": {"name": model.name, "version": model.version},
        "class_mapping_version": class_mapping_version,
        "confidence_floor": confidence_floor,
        "degradation": degradation.model_dump(),
    }
    return _digest(key)


def _digest(key: dict) -> str:
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
    experiment: Record
    saved_at: datetime


class ExperimentCache:
    def __init__(self, root: Path):
        self.root = root
        # Parsed records by id and kind, with the file's mtime: every frame request needs its experiment.
        self._loaded: dict[tuple[str, type], tuple[int, Record]] = {}
        # Whatever is staged now was left by a server that stopped mid-run.
        shutil.rmtree(self.root / ".staging", ignore_errors=True)

    def load(self, experiment_id: str) -> Experiment | None:
        loaded = self._read(experiment_id, Experiment)
        return loaded[1] if loaded else None

    def load_benchmark(self, experiment_id: str) -> BenchmarkExperiment | None:
        loaded = self._read(experiment_id, BenchmarkExperiment)
        return loaded[1] if loaded else None

    def load_synthetic_frames(self, experiment_id: str) -> SyntheticFramesExperiment | None:
        loaded = self._read(experiment_id, SyntheticFramesExperiment)
        return loaded[1] if loaded else None

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

    def commit(self, folder: Path, experiment: Record) -> None:
        """Make a staged run a complete entry: its record first, then the whole folder moves into place."""
        folder.mkdir(parents=True, exist_ok=True)
        (folder / RECORD_FILES[type(experiment)]).write_text(experiment.model_dump_json())
        target = self.root / experiment.id
        shutil.rmtree(target, ignore_errors=True)  # an entry that no longer loaded, since it was re-run
        os.replace(folder, target)

    @staticmethod
    def frame_in(folder: Path, variant: FrameVariant, index: int) -> Path:
        return folder / "frames" / variant / f"{index}.jpg"

    def frame_file(self, experiment_id: str, variant: FrameVariant, index: int) -> Path:
        return self.frame_in(self.root / experiment_id, variant, index)

    def entries(self, kinds: tuple[type[Record], ...] = (Experiment, SyntheticFramesExperiment)) -> list[CacheEntry]:
        """Every complete run of these kinds, newest first: by default the Synthetic runs, on video or on dataset
        frames."""
        if not self.root.is_dir():
            return []
        entries = [
            CacheEntry(experiment=loaded[1], saved_at=datetime.fromtimestamp(loaded[0] / 1e9, UTC))
            for folder in self.root.iterdir()
            for kind in kinds
            if (loaded := self._read(folder.name, kind))
        ]
        return sorted(entries, key=lambda entry: entry.saved_at, reverse=True)

    def synthetic_frames_runs(self) -> list[SyntheticFramesExperiment]:
        """Every complete Synthetic run on dataset frames, in no particular order. Reads no other kind of record."""
        if not self.root.is_dir():
            return []
        return [loaded[1] for folder in self.root.iterdir() if (loaded := self._read(folder.name, SyntheticFramesExperiment))]

    def headlines(self, experiment_id: str) -> dict[str, str]:
        """The headlines the user wrote for a run's findings, by finding. Empty when none are written."""
        try:
            stored = json.loads(self._headlines_file(experiment_id).read_text(encoding="utf-8"))
        except (OSError, ValueError):  # none written yet, or the file was damaged by hand
            return {}
        if not isinstance(stored, dict):  # edited by hand into something else
            return {}
        return {key: text for key, text in stored.items() if isinstance(text, str)}

    def save_headlines(self, experiment_id: str, headlines: dict[str, str]) -> None:
        """Kept beside the run's record, never in it: the record is what the id was derived from. Written whole and
        then moved into place, so a crash never leaves half a file. The caller checks the run exists."""
        path = self._headlines_file(experiment_id)
        staged = path.with_suffix(".json.tmp")
        staged.write_text(json.dumps(headlines, ensure_ascii=False), encoding="utf-8")
        os.replace(staged, path)

    def _headlines_file(self, experiment_id: str) -> Path:
        if not EXPERIMENT_ID.fullmatch(experiment_id):
            raise ValueError(f"Not an experiment id: {experiment_id!r}")
        return self.root / experiment_id / HEADLINES_FILE

    def size_bytes(self) -> int:
        total = 0
        for path in self.root.rglob("*"):
            try:
                total += path.stat().st_size if path.is_file() else 0
            except OSError:  # removed while we walked
                pass
        return total

    def _read[T: (Experiment, BenchmarkExperiment, SyntheticFramesExperiment)](self, experiment_id: str, kind: type[T]) -> tuple[int, T] | None:
        """The entry's record of this kind and its file's mtime, or None."""
        if not EXPERIMENT_ID.fullmatch(experiment_id):
            return None
        path = self.root / experiment_id / RECORD_FILES[kind]
        key = (experiment_id, kind)
        try:
            mtime = path.stat().st_mtime_ns
            loaded = self._loaded.get(key)
            if loaded is None or loaded[0] != mtime:
                loaded = mtime, kind.model_validate_json(path.read_bytes())
                self._loaded[key] = loaded
        except (OSError, ValidationError):  # missing (never finished, or deleted by hand) or unreadable
            self._loaded.pop(key, None)
            return None
        return loaded
