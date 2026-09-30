"""Detection runs as background jobs.

Starting a run returns a job at once; a worker thread decodes the video, degrades each frame,
runs the detector on both the clean and the degraded frame, and writes both to the cache so the
browser can fetch them by id. Only a run that finishes every frame becomes an experiment.
A cancelled or failed run leaves nothing behind.

A run whose experiment is already cached is not run again: its job is completed from the start.
"""

import shutil
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import cv2
import numpy as np

from backend.class_mapping import CLASS_MAPPING_VERSION
from backend.degradations import degrade, parameters
from backend.detection import ModelRunner
from backend.experiment import AppliedDegradation, DegradationSettings, Experiment, FrameResult, FrameVariant
from backend.experiment_cache import ExperimentCache, experiment_id, fingerprint
from backend.samples import Sample
from backend.video import VideoError, open_video

# Raw detections are kept down to this confidence, so the display threshold can be changed
# in the browser without re-running inference.
CONFIDENCE_FLOOR = 0.05

JobStatus = Literal["queued", "running", "completed", "cancelled", "failed"]
ACTIVE: tuple[JobStatus, ...] = ("queued", "running")


class NoDetector(Exception):
    """No detector is loaded (its weights are missing), so runs can't start."""


@dataclass
class Job:
    id: str
    experiment_id: str
    sample: Sample
    degradation: DegradationSettings
    status: JobStatus = "queued"
    frames_done: int = 0
    frames_total: int = 0
    error: str | None = None
    # Completed from the cache: the results were reused and nothing ran.
    cached: bool = False
    cancel_requested: threading.Event = field(default_factory=threading.Event)


class JobManager:
    def __init__(self, runner: ModelRunner | None, cache: ExperimentCache):
        self.runner = runner
        self.cache = cache
        self._jobs: dict[str, Job] = {}
        # Held while deciding whether to start, so two identical requests can't both start a run.
        self._starting = threading.Lock()

    def experiment_id_for(self, sample: Sample, degradation: DegradationSettings) -> str:
        """The id a run with these settings has, whether or not it has run."""
        if self.runner is None:
            raise NoDetector()
        return experiment_id(
            input_fingerprint=fingerprint(sample.path),
            model=self.runner.info,
            class_mapping_version=CLASS_MAPPING_VERSION,
            confidence_floor=CONFIDENCE_FLOOR,
            degradation=degradation,
        )

    def is_cached(self, experiment_id: str) -> bool:
        return self.cache.load(experiment_id) is not None

    def start(self, sample: Sample, degradation: DegradationSettings) -> Job:
        """A job completed at once if the experiment is cached, the job already running it if there is one,
        or else a new job."""
        with self._starting:
            job_experiment_id = self.experiment_id_for(sample, degradation)
            for job in self._jobs.values():
                # One being cancelled is not joined: it will end "cancelled". A fresh run beside it is safe,
                # since each job writes only to its own staging folder.
                cancelling = job.cancel_requested.is_set()
                if job.experiment_id == job_experiment_id and job.status in ACTIVE and not cancelling:
                    return job
            job = Job(id=uuid.uuid4().hex, experiment_id=job_experiment_id, sample=sample, degradation=degradation)
            cached = self.cache.load(job_experiment_id)
            if cached is not None:
                job.status, job.cached = "completed", True
                job.frames_done = job.frames_total = len(cached.frames)
            self._jobs[job.id] = job
        if not job.cached:
            threading.Thread(target=self._run, args=(job,), daemon=True).start()
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def cancel(self, job_id: str) -> Job | None:
        """Ask a job to stop. It stops before its next frame; a finished job is left as it is."""
        job = self._jobs.get(job_id)
        if job is not None:
            job.cancel_requested.set()
        return job

    def experiment(self, experiment_id: str) -> Experiment | None:
        return self.cache.load(experiment_id)

    def frame_path(self, experiment_id: str, variant: FrameVariant, index: int) -> Path | None:
        """The cached image for a frame of a completed experiment, or None. Paths come only from known ids."""
        experiment = self.cache.load(experiment_id)
        if experiment is None or not 0 <= index < len(experiment.frames):
            return None
        path = self.cache.frame_file(experiment.id, variant, index)
        return path if path.is_file() else None  # the cache may have been deleted by hand

    def _run(self, job: Job) -> None:
        settings = job.degradation
        # One generator for the whole run, drawn in frame order: each frame gets its own noise,
        # and the same seed reproduces every frame.
        rng = np.random.default_rng(settings.seed)
        folder = self.cache.staging(job.id)
        try:
            self.cache.open_staging(job.id)
            with open_video(job.sample.path) as video:
                job.frames_total = video.frame_count
                job.status = "running"
                results, size = [], (0, 0)
                for index, image in enumerate(video.frames()):
                    if job.cancel_requested.is_set():
                        break
                    degraded = degrade(image, settings.kind, settings.severity, rng)
                    clean_detections = self.runner.detect(image, CONFIDENCE_FLOOR)
                    degraded_detections = self.runner.detect(degraded, CONFIDENCE_FLOOR)
                    _write_frame(folder, "clean", index, image)
                    _write_frame(folder, "degraded", index, degraded)
                    results.append(FrameResult(index=index, clean=clean_detections, degraded=degraded_detections))
                    size = image.shape[1], image.shape[0]
                    job.frames_done = index + 1

            if job.cancel_requested.is_set():
                _discard(job, folder, "cancelled")
                return
            if not results:
                raise VideoError("The video has no readable frames.")
            job.frames_total = len(results)  # the container's count is only an estimate
            self.cache.commit(
                folder,
                Experiment(
                    id=job.experiment_id,
                    sample_id=job.sample.id,
                    degradation=AppliedDegradation(
                        **settings.model_dump(), parameters=parameters(settings.kind, settings.severity)
                    ),
                    model=self.runner.info,
                    confidence_floor=CONFIDENCE_FLOOR,
                    frame_width=size[0],
                    frame_height=size[1],
                    frames=results,
                ),
            )
            job.status = "completed"  # only after the experiment is stored, so pollers never see a gap
        except Exception as exc:  # any failure must end the job, never leave it "running"
            job.error = f"The run stopped at frame {job.frames_done}: {exc}"
            _discard(job, folder, "failed")


def _write_frame(folder: Path, variant: FrameVariant, index: int, image: np.ndarray) -> None:
    path = ExperimentCache.frame_in(folder, variant, index)
    if not cv2.imwrite(str(path), image):
        raise OSError(f"Could not write {variant} frame {index} to the cache at {path}.")


def _discard(job: Job, folder: Path, status: JobStatus) -> None:
    """Only this job's own staging folder: an entry another run committed under the same id stays."""
    shutil.rmtree(folder, ignore_errors=True)
    job.status = status
