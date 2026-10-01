"""Report export: what a finished run's report holds, and its data files.

A report is the run's findings (backend/findings.py) beside its results, exactly as the API returns them for the same
run and display threshold: a Benchmark run's scored conditions and synthetic rows (backend/benchmark_run.py), or a
video run's stability report (backend/stability.py). Nothing is re-run and nothing is scored a second way: the data
files are those documents written out, and report.html (backend/report_html.py) is rendered from them.
- metrics.json: the whole report document;
- frames.csv: every frame's score, one row per frame, from the same documents.
"""

import csv
import io
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from backend.benchmark_run import BenchmarkResults
from backend.class_mapping import CLASS_MAPPING_VERSION
from backend.experiment import DegradationSettings, Experiment
from backend.experiment_cache import experiment_id, fingerprint
from backend.findings import BenchmarkFindings, VideoFindings
from backend.stability import StabilityReport


class ExportHeader(BaseModel):
    experiment_id: str
    kind: Literal["benchmark", "video"]
    title: str
    display_threshold: float | None  # None for a video run, which has no threshold to apply
    created_at: datetime


class BenchmarkReport(BaseModel):
    export: ExportHeader
    findings: BenchmarkFindings
    results: BenchmarkResults


class VideoReport(BaseModel):
    export: ExportHeader
    # The clip's sha256, when the file is still the one the run read. None when that can't be confirmed.
    input_fingerprint: str | None
    findings: VideoFindings
    results: StabilityReport


Report = BenchmarkReport | VideoReport

BENCHMARK_COLUMNS = [
    "condition", "synthetic_run", "frame_id", "score", "hits", "misses", "false_alarms", "class_confusions", "ignored",
]  # fmt: skip
VIDEO_COLUMNS = ["index", "score", "retained", "dropped", "introduced", "class_changes", "confidence_loss"]


def input_fingerprint(experiment: Experiment, path: Path) -> str | None:
    """The clip's fingerprint, if hashing it with the run's settings gives back the run's id: then it is the file the
    run read. None when the file is gone or has changed since."""
    if not path.is_file():
        return None
    found = fingerprint(path)
    settings = DegradationSettings(**experiment.degradation.model_dump(include={"kind", "severity", "seed"}))
    derived = experiment_id(found, experiment.model, CLASS_MAPPING_VERSION, experiment.confidence_floor, settings)
    return found if derived == experiment.id else None


def metrics_json(report: Report) -> str:
    return report.model_dump_json(indent=2)


def frames_csv(report: Report) -> str:
    """A Benchmark run's frame scores at the display threshold, its own conditions then each synthetic run (named by
    id); or a video run's reliability timeline, every frame in order."""
    out = io.StringIO()
    if isinstance(report, BenchmarkReport):
        writer = csv.DictWriter(out, BENCHMARK_COLUMNS)
        writer.writeheader()
        results = report.results
        rows = [(row, "") for row in results.conditions] + [(row, row.experiment_id) for row in results.synthetic]
        for row, run in rows:
            for frame in row.frame_scores:
                writer.writerow(
                    {"condition": row.condition, "synthetic_run": run, "frame_id": frame.id, **frame.model_dump(exclude={"id"})}
                )
    else:
        writer = csv.DictWriter(out, VIDEO_COLUMNS)
        writer.writeheader()
        for point in report.findings.timeline:
            writer.writerow(point.model_dump())
    return out.getvalue()
