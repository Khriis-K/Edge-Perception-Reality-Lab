"""HTTP API routes. Pydantic models here define the OpenAPI schema the frontend types come from."""

from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.benchmark_run import (
    BenchmarkExperiment,
    BenchmarkResults,
    FrameDetail,
    ManifestRefused,
    benchmark_results,
    check_manifest,
    find_frame,
    frame_detail,
)
from backend.class_mapping import CLASS_MAPPING, ClassMapping
from backend.conditions import condition_name
from backend.dataset import DatasetIndex, FrameNotFound, camera_image, check_readiness, index_dataset
from backend.degradations import KINDS, RANDOMIZED, TITLES, DegradationKind, parameters
from backend.detection import ModelInfo
from backend.experiment import AppliedDegradation, DegradationSettings, Experiment, FrameVariant
from backend.exports import MEDIA_TYPES, ExportFileName, ExportStore, ExportSummary
from backend.findings import (
    BENCHMARK_FINDINGS,
    HEADLINE_LENGTH,
    VIDEO_FINDINGS,
    BenchmarkFindings,
    FindingKey,
    VideoFindings,
    benchmark_findings,
    video_findings,
)
from backend.jobs import Job, JobManager, JobMode, JobStatus, NoDetector
from backend.report import BenchmarkReport, ExportHeader, Report, VideoReport, frames_csv, input_fingerprint, metrics_json
from backend.report_html import report_html
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
    degradation_title,
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


def get_exports(request: Request) -> ExportStore:
    return request.app.state.exports


Exports = Annotated[ExportStore, Depends(get_exports)]


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


class FindingsRun(BaseModel):
    """A run Findings can open: a Benchmark run, or a Synthetic run on video. A Synthetic run on clear dataset frames
    is part of its Benchmark run's findings, not a document of its own."""

    id: str
    kind: Literal["benchmark", "video"]
    title: str
    saved_at: datetime


Findings = Annotated[BenchmarkFindings | VideoFindings, Field(discriminator="kind")]


class HeadlineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Written by the user, from the results. Blank clears it.
    text: str = Field(max_length=HEADLINE_LENGTH)


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


@router.get("/findings")
def list_findings_runs(jobs: Jobs) -> list[FindingsRun]:
    """The runs Findings can open, newest first: Benchmark runs and Synthetic runs on video."""
    return [
        FindingsRun(
            id=entry.experiment.id,
            kind="benchmark" if isinstance(entry.experiment, BenchmarkExperiment) else "video",
            title=_run_title(entry.experiment),
            saved_at=entry.saved_at,
        )
        for entry in jobs.cache.entries((BenchmarkExperiment, Experiment))
    ]


@router.get("/findings/{experiment_id}")
def get_findings(
    experiment_id: str,
    jobs: Jobs,
    display_threshold: Annotated[float, Query(ge=0, le=1, allow_inf_nan=False)],
) -> Findings:
    """A finished run's findings, as data for the Findings screen's charts, scored from the stored detections. A
    Benchmark run's has sim-to-real, the condition-by-class heatmap and worst frames at the display threshold; a video
    run's has the reliability timeline and worst frames, and ignores the threshold."""
    run = _findings_run(jobs, experiment_id)
    headlines = jobs.cache.headlines(experiment_id)
    if isinstance(run, BenchmarkExperiment):
        return benchmark_findings(run, jobs.cache.synthetic_frames_runs(), display_threshold, headlines)
    return video_findings(run, _sample_title(run.sample_id), headlines)


@router.put("/findings/{experiment_id}/headlines/{key}")
def put_headline(experiment_id: str, key: FindingKey, body: HeadlineRequest, jobs: Jobs) -> dict[FindingKey, str]:
    """Store the headline the user wrote for one finding of a run, with the run. Blank text clears it. Returns every
    headline the run now has. A finding the run doesn't have (a timeline on a Benchmark run) is refused (422)."""
    run = _findings_run(jobs, experiment_id)
    keys = BENCHMARK_FINDINGS if isinstance(run, BenchmarkExperiment) else VIDEO_FINDINGS
    if key not in keys:
        raise HTTPException(status_code=422, detail=f"This run has no {key} finding.")
    headlines = {k: v for k, v in jobs.cache.headlines(experiment_id).items() if k in keys}
    text = body.text.strip()
    if text:
        headlines[key] = text
    else:
        headlines.pop(key, None)
    jobs.cache.save_headlines(experiment_id, headlines)
    return headlines


def _findings_run(jobs: JobManager, experiment_id: str) -> BenchmarkExperiment | Experiment:
    """The Benchmark or video run Findings can open under this id, or a 404."""
    run = jobs.cache.load_benchmark(experiment_id) or jobs.experiment(experiment_id)
    if run is None:
        raise HTTPException(status_code=404, detail="No completed Benchmark or video run with that id.")
    return run


def _run_title(run: BenchmarkExperiment | Experiment) -> str:
    if isinstance(run, BenchmarkExperiment):
        return f"Benchmark: seed {run.manifest.seed}, up to {run.manifest.cap} frames per condition"
    return f"{degradation_title(run.degradation)} on {_sample_title(run.sample_id)}"


def _sample_title(sample_id: str) -> str:
    sample = SAMPLES.get(sample_id)
    return sample.title if sample else sample_id


@router.post("/findings/{experiment_id}/exports", status_code=201)
def export_report(
    experiment_id: str,
    jobs: Jobs,
    exports: Exports,
    display_threshold: Annotated[float, Query(ge=0, le=1, allow_inf_nan=False)],
) -> ExportSummary:
    """Save a finished run's report under exports/: report.html, metrics.json and frames.csv, built from the same
    findings and results these endpoints return at this display threshold. Nothing re-runs. A video run ignores the
    threshold, as its findings do."""
    run = _findings_run(jobs, experiment_id)
    headlines = jobs.cache.headlines(experiment_id)
    created_at = datetime.now(UTC)
    report: Report
    if isinstance(run, BenchmarkExperiment):
        runs = jobs.cache.synthetic_frames_runs()
        header = ExportHeader(
            experiment_id=run.id, kind="benchmark", title=_run_title(run), display_threshold=display_threshold,
            created_at=created_at,
        )  # fmt: skip
        report = BenchmarkReport(
            export=header,
            findings=benchmark_findings(run, runs, display_threshold, headlines),
            results=benchmark_results(run, display_threshold, benchmark_rows(run, runs, display_threshold)),
        )
    else:
        sample = SAMPLES.get(run.sample_id)
        header = ExportHeader(
            experiment_id=run.id, kind="video", title=_run_title(run), display_threshold=None, created_at=created_at
        )
        report = VideoReport(
            export=header,
            input_fingerprint=input_fingerprint(run, sample.path) if sample else None,
            findings=video_findings(run, _sample_title(run.sample_id), headlines),
            results=stability_report(run.frames),
        )
    files: dict[ExportFileName, str] = {
        "report.html": report_html(report),
        "metrics.json": metrics_json(report),
        "frames.csv": frames_csv(report),
    }
    return exports.save(header, files)


@router.get("/exports")
def list_exports(exports: Exports) -> list[ExportSummary]:
    """Every saved export, newest first, with its files and their sizes. Read from the exports folder."""
    return exports.exports()


@router.get(
    "/exports/{export_id}/{name}",
    response_class=FileResponse,
    responses={200: {"content": {media: {} for media in MEDIA_TYPES.values()}}},
)
def get_export_file(export_id: str, name: ExportFileName, exports: Exports) -> FileResponse:
    """One file of a saved export, by the export's id and the file's name: never a path."""
    path = exports.file(export_id, name)
    if path is None:
        raise HTTPException(status_code=404, detail="No such export file.")
    return FileResponse(path, media_type=MEDIA_TYPES[name])


@router.get("/benchmark/experiments/{experiment_id}/frames/{frame_id}")
def get_benchmark_frame(experiment_id: str, frame_id: str, jobs: Jobs) -> FrameDetail:
    """One frame's predictions and labels, matched at every display threshold, so the frame viewer can change
    threshold or toggle overlays without asking again. Its image is /api/dataset/frames/{frame_id}."""
    experiment = jobs.cache.load_benchmark(experiment_id)
    if experiment is None:
        raise HTTPException(status_code=404, detail="No completed benchmark with that id.")
    found = find_frame(experiment, frame_id)
    if found is None:
        raise HTTPException(status_code=404, detail="No such frame in this benchmark.")
    return frame_detail(*found)


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
