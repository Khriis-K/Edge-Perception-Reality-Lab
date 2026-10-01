"""HTTP API routes. Pydantic models here define the OpenAPI schema the frontend types come from."""

from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, field_validator

from backend.benchmark_run import BenchmarkResults, ManifestRefused, benchmark_results, check_manifest
from backend.class_mapping import CLASS_MAPPING, ClassMapping
from backend.conditions import condition_name
from backend.dataset import DatasetIndex, FrameNotFound, camera_image, check_readiness, index_dataset
from backend.degradations import KINDS, RANDOMIZED, TITLES, DegradationKind, parameters
from backend.detection import ModelInfo
from backend.experiment import AppliedDegradation, DegradationSettings, Experiment, FrameVariant
from backend.jobs import Job, JobManager, JobMode, JobStatus, NoDetector
from backend.samples import SAMPLES
from backend.stability import StabilityReport, stability_report
from backend.subset import (
    DEFAULT_CAP,
    DEFAULT_SEED,
    LOW_N_OBJECTS,
    MAX_CAP,
    ConditionSummary,
    Manifest,
    draw_subset,
    summarize,
)
from backend.synthetic_frames import (
    ClearCondition,
    SyntheticFramesExperiment,
    SyntheticFramesResults,
    benchmark_rows,
    synthetic_frames_results,
)

router = APIRouter(prefix="/api")

NO_MODEL_MESSAGE = (
    "The detector's weights are not installed. Fetch them with "
    "`.venv/Scripts/python.exe scripts/fetch_model.py`, then restart the app."
)


def get_jobs(request: Request) -> JobManager:
    return request.app.state.jobs


Jobs = Annotated[JobManager, Depends(get_jobs)]


class HealthResponse(BaseModel):
    status: Literal["ok"]


class SampleVideo(BaseModel):
    id: str
    title: str


class Degradation(BaseModel):
    kind: DegradationKind
    title: str
    # True when the seed changes the output.
    randomized: bool


class StartRunRequest(BaseModel):
    # Refuse unknown fields, so a second degradation can't ride along under another name.
    model_config = ConfigDict(extra="forbid")

    sample_id: str
    degradation: DegradationSettings

    @field_validator("sample_id")
    @classmethod
    def known_sample(cls, sample_id: str) -> str:
        if sample_id not in SAMPLES:
            raise ValueError(f"Unknown sample video: {sample_id!r}")
        return sample_id


class StartBenchmarkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # The manifest itself, as the Subset table draws it or as saved to a file. Never a path.
    manifest: Manifest


class StartSyntheticFramesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # The subset manifest, as for a Benchmark run; only the frames it lists under `condition` are degraded.
    manifest: Manifest
    condition: ClearCondition
    degradation: DegradationSettings


class JobResponse(BaseModel):
    id: str
    experiment_id: str
    mode: JobMode
    status: JobStatus
    frames_done: int
    frames_total: int
    progress: float
    error: str | None
    # True when the run's results were already cached: nothing ran, and the job is completed from the start.
    cached: bool

    @classmethod
    def of(cls, job: Job) -> "JobResponse":
        if job.status == "completed":
            progress = 1.0
        elif job.frames_total:
            # The container's frame count is an estimate, so never report past 100%.
            progress = min(job.frames_done / job.frames_total, 1.0)
        else:
            progress = 0.0
        return cls(
            id=job.id,
            experiment_id=job.experiment_id,
            mode=job.mode,
            status=job.status,
            frames_done=job.frames_done,
            frames_total=job.frames_total,
            progress=progress,
            error=job.error,
            cached=job.cached,
        )


class RunPreview(BaseModel):
    """What starting this run would do: reuse cached results, or start a new job."""

    experiment_id: str
    cached: bool


class ExperimentSummary(BaseModel):
    """A cached Synthetic run, for the run history. The frames themselves come from the experiment."""

    id: str
    # What the run degraded: a sample video, or the subset's frames of one clear condition.
    input: Literal["video", "dataset"]
    sample_id: str  # the video's id, or the condition for dataset frames
    sample_title: str
    degradation: AppliedDegradation
    model: ModelInfo
    frame_count: int
    saved_at: datetime


class CacheInfo(BaseModel):
    folder: str
    size_bytes: int


class DatasetPartStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: Literal["camera", "labels", "metadata"]
    name: str
    folder: str
    checked: bool
    present: bool
    message: str
    detail: str


class DatasetStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    configured: bool
    root: str | None
    ready: bool
    message: str
    parts: list[DatasetPartStatus]
    not_needed: list[str]


class SubsetResponse(BaseModel):
    manifest: Manifest
    conditions: list[ConditionSummary]
    excluded_total: int
    excluded: dict[str, int]  # reason -> samples, over the whole dataset
    problems: list[str]
    low_n_objects: int  # a condition whose rarest class has fewer objects is flagged low n
    max_cap: int  # the largest per-condition cap the server accepts


@router.get("/health")
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/samples")
def list_samples() -> list[SampleVideo]:
    return [SampleVideo(id=s.id, title=s.title) for s in SAMPLES.values()]


@router.get("/degradations")
def list_degradations() -> list[Degradation]:
    return [Degradation(kind=kind, title=TITLES[kind], randomized=kind in RANDOMIZED) for kind in KINDS]


@router.get("/degradations/{kind}/parameters")
def degradation_parameters(
    kind: DegradationKind, severity: Annotated[float, Query(ge=0, le=1, allow_inf_nan=False)]
) -> dict[str, float]:
    """The transform parameters a severity gives, exactly as a run would record them."""
    return parameters(kind, severity)


@router.post("/jobs", status_code=202, responses={200: {"description": "Cached: the results were reused"}})
def start_run(body: StartRunRequest, jobs: Jobs, response: Response) -> JobResponse:
    """Start a run, or reuse its cached results ("cached, results reused") if identical settings already ran."""
    try:
        job = jobs.start(SAMPLES[body.sample_id], body.degradation)
    except NoDetector:
        raise HTTPException(status_code=503, detail=NO_MODEL_MESSAGE)
    if job.cached:
        response.status_code = 200
    return JobResponse.of(job)


@router.post("/jobs/preview")
def preview_run(body: StartRunRequest, jobs: Jobs) -> RunPreview:
    """Whether this exact run request would reuse cached results or start a new job. Starts nothing."""
    try:
        experiment_id = jobs.experiment_id_for(SAMPLES[body.sample_id], body.degradation)
    except NoDetector:
        raise HTTPException(status_code=503, detail=NO_MODEL_MESSAGE)
    return RunPreview(experiment_id=experiment_id, cached=jobs.is_cached(experiment_id))


@router.get("/jobs/{job_id}")
def get_job(job_id: str, jobs: Jobs) -> JobResponse:
    return JobResponse.of(_known_job(jobs.get(job_id)))


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str, jobs: Jobs) -> JobResponse:
    return JobResponse.of(_known_job(jobs.cancel(job_id)))


@router.get("/experiments")
def list_experiments(jobs: Jobs) -> list[ExperimentSummary]:
    """Every cached Synthetic run, on video or on dataset frames, newest first, read from the cache folder."""
    summaries = []
    for entry in jobs.cache.entries():
        experiment = entry.experiment
        if isinstance(experiment, SyntheticFramesExperiment):
            source, source_id, title = "dataset", experiment.condition, f"{condition_name(experiment.condition)} frames"
        else:
            sample = SAMPLES.get(experiment.sample_id)
            source, source_id, title = "video", experiment.sample_id, sample.title if sample else experiment.sample_id
        summaries.append(
            ExperimentSummary(
                id=experiment.id,
                input=source,
                sample_id=source_id,
                sample_title=title,
                degradation=experiment.degradation,
                model=experiment.model,
                frame_count=len(experiment.frames),
                saved_at=entry.saved_at,
            )
        )
    return summaries


@router.get("/cache")
def cache_info(jobs: Jobs) -> CacheInfo:
    """The cache folder and how much it holds. Shown so it can be found and deleted; it is never set from here."""
    return CacheInfo(folder=str(jobs.cache.root.resolve()), size_bytes=jobs.cache.size_bytes())


@router.get("/experiments/{experiment_id}")
def get_experiment(experiment_id: str, jobs: Jobs) -> Experiment:
    return _known_experiment(jobs.experiment(experiment_id))


@router.get("/experiments/{experiment_id}/stability")
def get_stability(experiment_id: str, jobs: Jobs) -> StabilityReport:
    """How much the degraded detections differ from the clean ones, frame by frame and over the clip.
    Stability relative to the clean baseline: the clip has no labels, so this is not accuracy."""
    return stability_report(_known_experiment(jobs.experiment(experiment_id)).frames)


@router.get(
    "/experiments/{experiment_id}/frames/{variant}/{frame_index}",
    response_class=FileResponse,
    responses={200: {"content": {"image/jpeg": {}}}},
)
def get_frame_image(
    experiment_id: str, variant: FrameVariant, frame_index: Annotated[int, Path(ge=0)], jobs: Jobs
) -> FileResponse:
    """One cached clean or degraded frame of a completed experiment. Only known ids, never a file path."""
    path = jobs.frame_path(experiment_id, variant, frame_index)
    if path is None:
        raise HTTPException(status_code=404, detail="No such frame.")
    return FileResponse(path, media_type="image/jpeg")


def _known_experiment(experiment: Experiment | None) -> Experiment:
    if experiment is None:
        raise HTTPException(status_code=404, detail="No completed experiment with that id.")
    return experiment


def _known_job(job: Job | None) -> Job:
    if job is None:
        raise HTTPException(status_code=404, detail="No job with that id.")
    return job


@router.get("/dataset/status")
def dataset_status(request: Request) -> DatasetStatusResponse:
    """Re-check the dataset folder set at startup. The folder itself can't be changed from here."""
    return DatasetStatusResponse.model_validate(check_readiness(request.app.state.dataset_root))


@router.get(
    "/dataset/frames/{sample_id}",
    response_class=FileResponse,
    responses={200: {"content": {"image/png": {}}}, 404: {"description": "No such frame"}},
)
def dataset_frame(sample_id: str, request: Request) -> FileResponse:
    """A dataset sample's tone-mapped camera image, looked up by sample id only."""
    try:
        return FileResponse(camera_image(request.app.state.dataset_root, sample_id), media_type="image/png")
    except FrameNotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/dataset/subset", responses={409: {"description": "The dataset is not configured or not ready"}})
def dataset_subset(
    request: Request,
    seed: Annotated[int, Query(ge=0)] = DEFAULT_SEED,
    cap: Annotated[int, Query(ge=1, le=MAX_CAP)] = DEFAULT_CAP,
) -> SubsetResponse:
    """The seeded per-condition subset: its manifest and the counts for the Subset table. With no seed or cap,
    the defaults are used, and the manifest says which."""
    index = _dataset_index(request)
    manifest = draw_subset(index.frames, seed, cap)
    return SubsetResponse(
        manifest=manifest,
        conditions=summarize(index.frames, manifest),
        excluded_total=sum(index.excluded.values()),
        excluded=index.excluded,
        problems=index.problems,
        low_n_objects=LOW_N_OBJECTS,
        max_cap=MAX_CAP,
    )


@router.post(
    "/benchmark/jobs",
    status_code=202,
    responses={
        200: {"description": "Cached: the results were reused"},
        409: {"description": "The dataset is not configured or not ready"},
    },
)
def start_benchmark(body: StartBenchmarkRequest, request: Request, jobs: Jobs, response: Response) -> JobResponse:
    """Run the detector over every frame of the manifest and score it, or reuse the cached results. Poll and cancel
    it like any job. A manifest from another condition vocabulary, or listing frames the local dataset doesn't have
    under that condition, is refused (422) with the reason."""
    if jobs.runner is None:
        raise HTTPException(status_code=503, detail=NO_MODEL_MESSAGE)
    try:
        check_manifest(body.manifest, _dataset_index(request).frames)
    except ManifestRefused as refused:
        raise HTTPException(status_code=422, detail=str(refused)) from refused
    job = jobs.start_benchmark(request.app.state.dataset_root, body.manifest)
    if job.cached:
        response.status_code = 200
    return JobResponse.of(job)


@router.get("/benchmark/experiments/{experiment_id}")
def get_benchmark_results(
    experiment_id: str,
    jobs: Jobs,
    display_threshold: Annotated[float, Query(ge=0, le=1, allow_inf_nan=False)],
) -> BenchmarkResults:
    """Per condition and class: AP, precision and recall at the display threshold, and object and frame counts.
    Scored from the stored detections, so a new threshold never re-runs inference."""
    experiment = jobs.cache.load_benchmark(experiment_id)
    if experiment is None:
        raise HTTPException(status_code=404, detail="No completed benchmark with that id.")
    rows = benchmark_rows(experiment, jobs.cache.synthetic_frames_runs(), display_threshold)
    return benchmark_results(experiment, display_threshold, rows)


@router.post(
    "/synthetic-frames/jobs",
    status_code=202,
    responses={
        200: {"description": "Cached: the results were reused"},
        409: {"description": "The dataset is not configured or not ready"},
    },
)
def start_synthetic_frames(
    body: StartSyntheticFramesRequest, request: Request, jobs: Jobs, response: Response
) -> JobResponse:
    """Degrade the manifest's frames of one clear condition and run the detector on both variants, or reuse the
    cached results. The manifest is checked as for a Benchmark run, and must list frames under the condition."""
    if jobs.runner is None:
        raise HTTPException(status_code=503, detail=NO_MODEL_MESSAGE)
    try:
        check_manifest(body.manifest, _dataset_index(request).frames)
    except ManifestRefused as refused:
        raise HTTPException(status_code=422, detail=str(refused)) from refused
    if not body.manifest.frames.get(body.condition):
        raise HTTPException(
            status_code=422,
            detail=f"The manifest lists no {condition_name(body.condition)} frames to degrade. Draw a subset that has some.",
        )
    job = jobs.start_synthetic_frames(request.app.state.dataset_root, body.manifest, body.condition, body.degradation)
    if job.cached:
        response.status_code = 200
    return JobResponse.of(job)


@router.get("/synthetic-frames/experiments/{experiment_id}")
def get_synthetic_frames_results(
    experiment_id: str,
    jobs: Jobs,
    display_threshold: Annotated[float, Query(ge=0, le=1, allow_inf_nan=False)],
) -> SyntheticFramesResults:
    """Stability against the clean detections, and per-class AP, precision and recall for both the clean and the
    degraded frames against the ground truth, with the Benchmark's definitions. Scored from the stored detections."""
    experiment = jobs.cache.load_synthetic_frames(experiment_id)
    if experiment is None:
        raise HTTPException(status_code=404, detail="No completed synthetic run on dataset frames with that id.")
    return synthetic_frames_results(experiment, display_threshold)


@router.get("/benchmark/class-mapping")
def class_mapping() -> ClassMapping:
    """Which COCO classes count as which dataset class, and which labels are ignore regions. Both change the metrics,
    so Setup, Findings and the report show them."""
    return CLASS_MAPPING


def _dataset_index(request: Request) -> DatasetIndex:
    """The dataset's index, built once per app. The lock stops two first requests from both reading everything."""
    state = request.app.state
    with state.dataset_index_lock:
        if state.dataset_index is None:
            status = check_readiness(state.dataset_root)
            if not status.ready:
                raise HTTPException(status_code=409, detail=status.message)
            state.dataset_index = index_dataset(state.dataset_root)
        return state.dataset_index
