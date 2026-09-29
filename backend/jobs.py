"""Detection runs as background jobs.

Starting a run returns a job at once; a worker thread decodes the video, runs the detector on
every frame, and writes each frame to the cache so the browser can fetch it by id. Only a run
that finishes every frame becomes an experiment. A cancelled or failed run leaves nothing behind.
"""

import shutil
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import cv2
from pydantic import BaseModel

from backend.detection import Detection, ModelInfo, ModelRunner
from backend.samples import Sample
from backend.video import VideoError, open_video

# Raw detections are kept down to this confidence, so the display threshold can be changed
# in the browser without re-running inference.
CONFIDENCE_FLOOR = 0.05

JobStatus = Literal["queued", "running", "completed", "cancelled", "failed"]


class FrameResult(BaseModel):
    index: int
    detections: list[Detection]


class Experiment(BaseModel):
    id: str
    sample_id: str
    model: ModelInfo
    confidence_floor: float
    frame_width: int
    frame_height: int
    frames: list[FrameResult]


class NoDetector(Exception):
    """No detector is loaded (its weights are missing), so runs can't start."""


@dataclass
class Job:
    id: str
    experiment_id: str
    sample: Sample
    status: JobStatus = "queued"
    frames_done: int = 0
    frames_total: int = 0
    error: str | None = None
    cancel_requested: threading.Event = field(default_factory=threading.Event)


class JobManager:
    def __init__(self, runner: ModelRunner | None, cache_dir: Path):
        self.runner = runner
        self.cache_dir = cache_dir
        self._jobs: dict[str, Job] = {}
        self._experiments: dict[str, Experiment] = {}

    def start(self, sample: Sample) -> Job:
        if self.runner is None:
            raise NoDetector()
        job = Job(id=uuid.uuid4().hex, experiment_id=uuid.uuid4().hex, sample=sample)
        self._jobs[job.id] = job
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
        return self._experiments.get(experiment_id)

    def frame_path(self, experiment_id: str, index: int) -> Path | None:
        """The cached image for a frame of a completed experiment, or None. Paths come only from known ids."""
        experiment = self._experiments.get(experiment_id)
        if experiment is None or not 0 <= index < len(experiment.frames):
            return None
        path = self._frame_file(experiment.id, index)
        return path if path.is_file() else None  # the cache may have been deleted by hand

    def _frame_file(self, experiment_id: str, index: int) -> Path:
        return self.cache_dir / experiment_id / "frames" / f"{index}.jpg"

    def _run(self, job: Job) -> None:
        try:
            with open_video(job.sample.path) as video:
                job.frames_total = video.frame_count
                job.status = "running"
                results, size = [], (0, 0)
                for index, image in enumerate(video.frames()):
                    if job.cancel_requested.is_set():
                        break
                    detections = self.runner.detect(image, CONFIDENCE_FLOOR)
                    path = self._frame_file(job.experiment_id, index)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    if not cv2.imwrite(str(path), image):
                        raise OSError(f"Could not write frame {index} to the cache at {path}.")
                    results.append(FrameResult(index=index, detections=detections))
                    size = image.shape[1], image.shape[0]
                    job.frames_done = index + 1

            if job.cancel_requested.is_set():
                self._discard(job, "cancelled")
                return
            if not results:
                raise VideoError("The video has no readable frames.")
            job.frames_total = len(results)  # the container's count is only an estimate
            self._experiments[job.experiment_id] = Experiment(
                id=job.experiment_id,
                sample_id=job.sample.id,
                model=self.runner.info,
                confidence_floor=CONFIDENCE_FLOOR,
                frame_width=size[0],
                frame_height=size[1],
                frames=results,
            )
            job.status = "completed"  # only after the experiment is stored, so pollers never see a gap
        except Exception as exc:  # any failure must end the job, never leave it "running"
            job.error = f"The run stopped at frame {job.frames_done}: {exc}"
            self._discard(job, "failed")

    def _discard(self, job: Job, status: JobStatus) -> None:
        shutil.rmtree(self.cache_dir / job.experiment_id, ignore_errors=True)
        job.status = status
