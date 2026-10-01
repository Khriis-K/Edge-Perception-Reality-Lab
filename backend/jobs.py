"""Detection runs as background jobs.

Starting a run returns a job at once. For a Synthetic run, a worker thread decodes the video, degrades each frame,
runs the detector on both the clean and the degraded frame, and writes both to the cache so the
browser can fetch them by id. Each stage is timed (see backend/latency.py). For a Benchmark run, it runs the detector
once on every frame of the subset manifest and stores the detections with the frame's ground truth. A Synthetic run on
dataset frames does both: it degrades each frame of one clear condition of the manifest, runs the detector on the clean
and the degraded frame, and stores both with the ground truth. Only a run that finishes every frame becomes an
experiment.
A cancelled or failed run leaves nothing behind.

A run whose experiment is already cached is not run again: its job is completed from the start.
"""

import shutil
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import cv2
import numpy as np

from backend.benchmark import BenchmarkFrame
from backend.benchmark_run import BenchmarkExperiment, read_frame, run_warnings
from backend.class_mapping import CLASS_MAPPING_VERSION
from backend.conditions import CONDITIONS
from backend.degradations import degrade, parameters
from backend.detection import ModelRunner, TimedDetections
from backend.experiment import AppliedDegradation, DegradationSettings, Experiment, FrameResult, FrameVariant
from backend.experiment_cache import (
    ExperimentCache,
    benchmark_experiment_id,
    experiment_id,
    fingerprint,
    synthetic_frames_experiment_id,
)
from backend.latency import FrameTiming, summarize
from backend.samples import Sample
from backend.subset import Manifest
from backend.synthetic_frames import ClearCondition, SyntheticFrame, SyntheticFramesExperiment
from backend.video import VideoError, open_video

# Raw detections are kept down to this confidence, so the display threshold can be changed
# in the browser without re-running inference.
CONFIDENCE_FLOOR = 0.05

JobStatus = Literal["queued", "running", "completed", "cancelled", "failed"]
ACTIVE: tuple[JobStatus, ...] = ("queued", "running")
JobMode = Literal["synthetic", "benchmark", "synthetic-frames"]


class NoDetector(Exception):
    """No detector is loaded (its weights are missing), so runs can't start."""


@dataclass
class Job:
    id: str
    experiment_id: str
    mode: JobMode
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

    def benchmark_id_for(self, manifest: Manifest) -> str:
        """The id a Benchmark run of this manifest has, whether or not it has run."""
        if self.runner is None:
            raise NoDetector()
        return benchmark_experiment_id(
            manifest=manifest,
            model=self.runner.info,
            class_mapping_version=CLASS_MAPPING_VERSION,
            confidence_floor=CONFIDENCE_FLOOR,
        )

    def synthetic_frames_id_for(
        self, manifest: Manifest, condition: ClearCondition, degradation: DegradationSettings
    ) -> str:
        """The id a Synthetic run on these dataset frames has, whether or not it has run."""
        if self.runner is None:
            raise NoDetector()
        return synthetic_frames_experiment_id(
            manifest=manifest,
            condition=condition,
            model=self.runner.info,
            class_mapping_version=CLASS_MAPPING_VERSION,
            confidence_floor=CONFIDENCE_FLOOR,
            degradation=degradation,
        )

    def start(self, sample: Sample, degradation: DegradationSettings) -> Job:
        """A Synthetic run: see _start()."""

        def cached_frames(experiment_id: str) -> int | None:
            cached = self.cache.load(experiment_id)
            return None if cached is None else len(cached.frames)

        return self._start(
            "synthetic",
            self.experiment_id_for(sample, degradation),
            cached_frames,
            lambda job: self._run(job, sample, degradation),
        )

    def start_benchmark(self, dataset_root: Path, manifest: Manifest) -> Job:
        """A Benchmark run over every frame the manifest lists, which the caller has checked: see _start()."""

        def cached_frames(experiment_id: str) -> int | None:
            cached = self.cache.load_benchmark(experiment_id)
            return None if cached is None else sum(len(frames) for frames in cached.frames.values())

        return self._start(
            "benchmark",
            self.benchmark_id_for(manifest),
            cached_frames,
            lambda job: self._run_benchmark(job, dataset_root, manifest),
        )

    def start_synthetic_frames(
        self, dataset_root: Path, manifest: Manifest, condition: ClearCondition, degradation: DegradationSettings
    ) -> Job:
        """A Synthetic run on the frames the manifest lists under one clear condition, which the caller has checked:
        see _start()."""

        def cached_frames(experiment_id: str) -> int | None:
            cached = self.cache.load_synthetic_frames(experiment_id)
            return None if cached is None else len(cached.frames)

        return self._start(
            "synthetic-frames",
            self.synthetic_frames_id_for(manifest, condition, degradation),
            cached_frames,
            lambda job: self._run_synthetic_frames(job, dataset_root, manifest, condition, degradation),
        )

    def _start(
        self,
        mode: JobMode,
        job_experiment_id: str,
        cached_frames: Callable[[str], int | None],
        run: Callable[[Job], None],
    ) -> Job:
        """A job completed at once if the experiment is cached, the job already running it if there is one,
        or else a new job. `cached_frames` gives the cached experiment's frame count, or None if it isn't cached."""
        with self._starting:
            for job in self._jobs.values():
                # One being cancelled is not joined: it will end "cancelled". A fresh run beside it is safe,
                # since each job writes only to its own staging folder.
                cancelling = job.cancel_requested.is_set()
                if job.experiment_id == job_experiment_id and job.status in ACTIVE and not cancelling:
                    return job
            job = Job(id=uuid.uuid4().hex, experiment_id=job_experiment_id, mode=mode)
            frames = cached_frames(job_experiment_id)
            if frames is not None:
                job.status, job.cached = "completed", True
                job.frames_done = job.frames_total = frames
            self._jobs[job.id] = job
        if not job.cached:
            threading.Thread(target=run, args=(job,), daemon=True).start()
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

    def _run(self, job: Job, sample: Sample, settings: DegradationSettings) -> None:
        # One generator for the whole run, drawn in frame order: each frame gets its own noise,
        # and the same seed reproduces every frame.
        rng = np.random.default_rng(settings.seed)
        folder = self.cache.staging(job.id)
        try:
            self.cache.open_staging(job.id)
            with open_video(sample.path) as video:
                job.frames_total = video.frame_count
                job.status = "running"
                results, timings, size = [], [], (0, 0)
                started = time.perf_counter()  # reset after each frame, so reading the next is timed alone
                for index, image in enumerate(video.frames()):
                    read = time.perf_counter()
                    if job.cancel_requested.is_set():
                        break
                    degraded = degrade(image, settings.kind, settings.severity, rng)
                    degraded_at = time.perf_counter()
                    clean_run, clean_s = self._detect(image)
                    degraded_run, degraded_s = self._detect(degraded)
                    detected_at = time.perf_counter()
                    _write_frame(folder, "clean", index, image)
                    _write_frame(folder, "degraded", index, degraded)
                    written = time.perf_counter()
                    results.append(FrameResult(index=index, clean=clean_run.detections, degraded=degraded_run.detections))
                    timings.append(
                        FrameTiming(
                            read_s=read - started,
                            degrade_s=degraded_at - read,
                            inference_s=[clean_run.inference_s, degraded_run.inference_s],
                            processing_s=[clean_s - clean_run.inference_s, degraded_s - degraded_run.inference_s],
                            render_s=written - detected_at,
                        )
                    )
                    size = image.shape[1], image.shape[0]
                    job.frames_done = index + 1
                    started = time.perf_counter()

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
                    sample_id=sample.id,
                    degradation=AppliedDegradation(
                        **settings.model_dump(), parameters=parameters(settings.kind, settings.severity)
                    ),
                    model=self.runner.info,
                    confidence_floor=CONFIDENCE_FLOOR,
                    frame_width=size[0],
                    frame_height=size[1],
                    frames=results,
                    latency=summarize(timings),
                ),
            )
            job.status = "completed"  # only after the experiment is stored, so pollers never see a gap
        except Exception as exc:  # any failure must end the job, never leave it "running"
            job.error = f"The run stopped at frame {job.frames_done}: {exc}"
            _discard(job, folder, "failed")

    def _detect(self, image: np.ndarray) -> tuple[TimedDetections, float]:
        """The detections with their inference time, and the whole call's time."""
        start = time.perf_counter()
        timed = self.runner.detect_timed(image, CONFIDENCE_FLOOR)
        return timed, time.perf_counter() - start

    def _run_benchmark(self, job: Job, dataset_root: Path, manifest: Manifest) -> None:
        folder = self.cache.staging(job.id)
        # Vocabulary order, so progress walks the conditions in the order the tree lists them.
        work = [(condition, sample_id) for condition in CONDITIONS for sample_id in manifest.frames.get(condition, [])]
        try:
            folder.mkdir(parents=True)
            job.frames_total = len(work)
            job.status = "running"
            frames: dict[str, list[BenchmarkFrame]] = {c: [] for c in CONDITIONS if c in manifest.frames}
            for condition, sample_id in work:
                if job.cancel_requested.is_set():
                    break
                image, truths = read_frame(dataset_root, sample_id)
                predictions = self.runner.detect(image, CONFIDENCE_FLOOR)
                frames[condition].append(BenchmarkFrame(id=sample_id, predictions=predictions, truths=truths))
                job.frames_done += 1

            if job.cancel_requested.is_set():
                _discard(job, folder, "cancelled")
                return
            self.cache.commit(
                folder,
                BenchmarkExperiment(
                    id=job.experiment_id,
                    manifest=manifest,
                    model=self.runner.info,
                    class_mapping_version=CLASS_MAPPING_VERSION,
                    confidence_floor=CONFIDENCE_FLOOR,
                    frames=frames,
                    warnings=run_warnings([f for listed in frames.values() for f in listed]),
                ),
            )
            job.status = "completed"  # only after the experiment is stored, so pollers never see a gap
        except Exception as exc:  # any failure must end the job, never leave it "running"
            job.error = f"The run stopped at frame {job.frames_done}: {exc}"
            _discard(job, folder, "failed")

    def _run_synthetic_frames(
        self,
        job: Job,
        dataset_root: Path,
        manifest: Manifest,
        condition: ClearCondition,
        settings: DegradationSettings,
    ) -> None:
        # As on video: one generator, drawn in manifest order, so the same seed reproduces every frame.
        rng = np.random.default_rng(settings.seed)
        folder = self.cache.staging(job.id)
        sample_ids = manifest.frames[condition]
        try:
            folder.mkdir(parents=True)
            job.frames_total = len(sample_ids)
            job.status = "running"
            frames = []
            for sample_id in sample_ids:
                if job.cancel_requested.is_set():
                    break
                image, truths = read_frame(dataset_root, sample_id)
                degraded = degrade(image, settings.kind, settings.severity, rng)
                frames.append(
                    SyntheticFrame(
                        id=sample_id,
                        clean=self.runner.detect(image, CONFIDENCE_FLOOR),
                        degraded=self.runner.detect(degraded, CONFIDENCE_FLOOR),
                        truths=truths,
                    )
                )
                job.frames_done += 1

            if job.cancel_requested.is_set():
                _discard(job, folder, "cancelled")
                return
            self.cache.commit(
                folder,
                SyntheticFramesExperiment(
                    id=job.experiment_id,
                    manifest=manifest,
                    condition=condition,
                    degradation=AppliedDegradation(
                        **settings.model_dump(), parameters=parameters(settings.kind, settings.severity)
                    ),
                    model=self.runner.info,
                    class_mapping_version=CLASS_MAPPING_VERSION,
                    confidence_floor=CONFIDENCE_FLOOR,
                    frames=frames,
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
