"""HTTP API routes. Pydantic models here define the OpenAPI schema the frontend types come from."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, field_validator

from backend.dataset import DatasetIndex, FrameNotFound, camera_image, check_readiness, index_dataset
from backend.degradations import KINDS, RANDOMIZED, TITLES, DegradationKind, parameters
from backend.jobs import DegradationSettings, Experiment, FrameVariant, Job, JobManager, JobStatus, NoDetector
from backend.samples import SAMPLES
from backend.subset import DEFAULT_CAP, DEFAULT_SEED, LOW_N_OBJECTS, ConditionSummary, Manifest, draw_subset, summarize

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


class JobResponse(BaseModel):
    id: str
    experiment_id: str
    mode: Literal["synthetic"]
    status: JobStatus
    frames_done: int
    frames_total: int
    progress: float
    error: str | None

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
            mode="synthetic",
            status=job.status,
            frames_done=job.frames_done,
            frames_total=job.frames_total,
            progress=progress,
            error=job.error,
        )


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


@router.post("/jobs", status_code=202)
def start_run(body: StartRunRequest, jobs: Jobs) -> JobResponse:
    try:
        return JobResponse.of(jobs.start(SAMPLES[body.sample_id], body.degradation))
    except NoDetector:
        raise HTTPException(status_code=503, detail=NO_MODEL_MESSAGE)


@router.get("/jobs/{job_id}")
def get_job(job_id: str, jobs: Jobs) -> JobResponse:
    return JobResponse.of(_known_job(jobs.get(job_id)))


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str, jobs: Jobs) -> JobResponse:
    return JobResponse.of(_known_job(jobs.cancel(job_id)))


@router.get("/experiments/{experiment_id}")
def get_experiment(experiment_id: str, jobs: Jobs) -> Experiment:
    experiment = jobs.experiment(experiment_id)
    if experiment is None:
        raise HTTPException(status_code=404, detail="No completed experiment with that id.")
    return experiment


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
    cap: Annotated[int, Query(ge=1, le=100_000)] = DEFAULT_CAP,
) -> SubsetResponse:
    """The seeded per-condition subset: its manifest and the counts for the Subset table."""
    index = _dataset_index(request)
    manifest = draw_subset(index.frames, seed, cap)
    return SubsetResponse(
        manifest=manifest,
        conditions=summarize(index.frames, manifest),
        excluded_total=sum(index.excluded.values()),
        excluded=index.excluded,
        problems=index.problems,
        low_n_objects=LOW_N_OBJECTS,
    )


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
