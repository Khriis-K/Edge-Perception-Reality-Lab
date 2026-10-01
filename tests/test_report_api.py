"""API contract tests for report export: a finished run's findings saved under exports/ as report.html, metrics.json and
frames.csv, without re-running anything, and the list of previous exports.

The fixture is the one the findings tests use (see tests/test_findings_api.py): the fixture dataset with the stub
runner for a Benchmark run, plus a synthetic fog run on its clear-day frames; the bundled synthetic clip for a video run.
"""

import csv
import io
import json
import re
from html import unescape
from typing import get_args

import pytest
from fastapi.testclient import TestClient
from test_benchmark_api import results as benchmark_results
from test_benchmark_api import root, subset_manifest  # noqa: F401 (root: fixture)
from test_benchmark_api import run_to_completion as run_benchmark
from test_experiments_api import run_to_completion as run_video
from test_findings_api import findings, put_headline
from test_synthetic_frames_api import FOG
from test_synthetic_frames_api import run_to_completion as run_synthetic_frames

from backend.app import create_app
from backend.class_mapping import IGNORE_RULE
from backend.experiment_cache import fingerprint
from backend.findings import BENCHMARK_FINDINGS, BENCHMARK_LIMITATIONS, VIDEO_FINDINGS, VIDEO_LIMITATIONS, FindingKey
from backend.report_html import BENCHMARK_RENDERERS, CITATION, VIDEO_RENDERERS
from backend.samples import SAMPLES
from backend.stub_runner import StubRunner

FILES = ["report.html", "metrics.json", "frames.csv"]


def make_client(tmp_path, root=None):
    app = create_app(
        static_dir=tmp_path / "no-dist",
        runner=StubRunner(),
        cache_dir=tmp_path / "cache",
        exports_dir=tmp_path / "exports",
        dataset_root=root,
    )
    return TestClient(app)


@pytest.fixture
def client(tmp_path, root):
    return make_client(tmp_path, root)


@pytest.fixture
def video_client(tmp_path):
    return make_client(tmp_path)


def export(client, experiment_id, display_threshold=0.25):
    response = client.post(f"/api/findings/{experiment_id}/exports", params={"display_threshold": display_threshold})
    assert response.status_code == 201, response.text
    return response.json()


def file_text(client, export_id, name):
    response = client.get(f"/api/exports/{export_id}/{name}")
    assert response.status_code == 200, response.text
    return response.text


@pytest.fixture
def benchmark(client):
    run = run_benchmark(client)
    fog = run_synthetic_frames(client, degradation=FOG)
    return {"id": run["experiment_id"], "fog_id": fog["experiment_id"]}


def text_of(html):
    """The report's visible text, tags removed and whitespace collapsed, so assertions read like the page."""
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", html)))


# --- what every report contains ---------------------------------------------------------------------------


def test_a_benchmark_report_holds_config_manifest_mapping_definitions_limitations_and_citation(client, benchmark):
    manifest = subset_manifest(client)
    saved = export(client, benchmark["id"])

    html = file_text(client, saved["id"], "report.html")
    text = text_of(html)

    # The subset manifest: seed, cap, vocabulary version and every frame id.
    assert f"seed {manifest['seed']}" in text
    assert f"cap {manifest['cap']}" in text
    assert all(frame_id in text for ids in manifest["frames"].values() for frame_id in ids)
    # The model and runtime versions.
    assert "Stub detector" in text and "fixture-1" in text and "none (deterministic stub)" in text
    # The class mapping and ignore-region rule.
    assert "car → PassengerCar" in text and "motorcycle → RidableVehicle" in text
    assert IGNORE_RULE in text
    # Degradation settings: the synthetic fog run beside the Benchmark, with its severity, seed and parameters.
    assert "Synthetic fog 0.60" in text
    assert benchmark["fog_id"] in text
    assert f"seed {FOG['seed']}" in text
    # Metric definitions, and the sample sizes behind them: clear-day's 1 frame and 2 objects, low n under 30.
    assert "Average precision" in text and "IoU ≥ 0.5" in text and "display threshold 0.25" in text
    assert re.search(r"Clear · day 1 2 low n", text)
    assert "fewer than 30 objects" in text
    # Limitations and the dataset citation.
    assert all(limitation in text for limitation in BENCHMARK_LIMITATIONS)
    assert CITATION in text


def test_a_video_report_holds_the_input_fingerprint_degradation_model_definitions_limitations_and_citation(
    video_client,
):
    job = run_video(video_client)
    saved = export(video_client, job["experiment_id"])

    text = text_of(file_text(video_client, saved["id"], "report.html"))

    # The input fingerprint: the bundled clip's sha256, confirmed to be the file the run read.
    assert fingerprint(SAMPLES["synthetic-traffic"].path) in text
    assert "Synthetic traffic (generated)" in text
    assert "Stub detector" in text and "fixture-1" in text
    # Degradation settings, with the transform parameters the severity gave.
    assert "Gaussian blur — severity 0.10, seed 0" in text
    # The class mapping and ignore rule are always shown, with what they mean for a run with no labels.
    assert "car → PassengerCar" in text and IGNORE_RULE in text
    # Stability definitions and sample size: every frame of the clip.
    assert "stability threshold 0.25" in text and "IoU ≥ 0.5" in text
    assert "48 frames" in text
    assert all(limitation in text for limitation in VIDEO_LIMITATIONS)
    assert CITATION in text


def test_a_video_report_says_so_when_the_clip_is_no_longer_the_one_the_run_read(video_client, tmp_path, monkeypatch):
    job = run_video(video_client)
    changed = tmp_path / "changed.mp4"
    changed.write_bytes(b"not the clip the run read")
    sample = SAMPLES["synthetic-traffic"]
    monkeypatch.setitem(SAMPLES, sample.id, type(sample)(id=sample.id, title=sample.title, path=changed))

    text = text_of(file_text(video_client, export(video_client, job["experiment_id"])["id"], "report.html"))

    assert fingerprint(changed) not in text
    assert "can't be confirmed" in text


def test_headlines_appear_when_the_user_has_written_them_and_none_are_generated(client, benchmark):
    put_headline(client, benchmark["id"], "where-it-fails", "Snow by day costs the most.")

    text = text_of(file_text(client, export(client, benchmark["id"])["id"], "report.html"))

    assert "Snow by day costs the most." in text
    assert text.count("No headline written") == len(BENCHMARK_FINDINGS) - 1


def test_worst_frames_are_named_by_frame_id_only(client, benchmark):
    worst = findings(client, benchmark["id"])["worst_frames"]

    text = text_of(file_text(client, export(client, benchmark["id"])["id"], "report.html"))

    assert worst
    assert all(f"{frame['id']} {frame['score']:.2f}" in text for frame in worst)


# --- self-contained: opens offline, no imagery ------------------------------------------------------------


@pytest.mark.parametrize("kind", ["benchmark", "video"])
def test_the_html_holds_no_images_and_loads_nothing_from_outside(kind, client, tmp_path):
    experiment_id = run_benchmark(client)["experiment_id"] if kind == "benchmark" else run_video(client)["experiment_id"]

    html = file_text(client, export(client, experiment_id)["id"], "report.html").lower()

    assert "<img" not in html and "<image" not in html and "<picture" not in html and "<video" not in html
    assert "data:image" not in html
    assert "<link" not in html and "<script" not in html and "<iframe" not in html
    assert "src=" not in html and "url(" not in html and "@import" not in html
    assert "http://" not in html and "https://" not in html


# --- every finding renders --------------------------------------------------------------------------------


def test_every_finding_kind_has_a_renderer():
    assert set(BENCHMARK_RENDERERS) == set(BENCHMARK_FINDINGS)
    assert set(VIDEO_RENDERERS) == set(VIDEO_FINDINGS)
    assert set(BENCHMARK_RENDERERS) | set(VIDEO_RENDERERS) == set(get_args(FindingKey))


def test_every_benchmark_finding_renders_numbered_in_findings_order(client, benchmark):
    html = file_text(client, export(client, benchmark["id"])["id"], "report.html")

    positions = [html.index(f'id="{key}"') for key in BENCHMARK_FINDINGS]
    assert positions == sorted(positions)
    text = text_of(html)
    assert "Finding 01 · Sim-to-real" in text
    assert "Finding 02 · Where it fails" in text
    assert "Finding 03 · Precision–recall" in text


def test_the_video_finding_renders(video_client):
    job = run_video(video_client)

    html = file_text(video_client, export(video_client, job["experiment_id"])["id"], "report.html")

    assert all(f'id="{key}"' in html for key in VIDEO_FINDINGS)
    assert "Finding 01 · Reliability timeline" in text_of(html)


def test_sim_to_real_is_a_table_of_per_class_drops(client, benchmark):
    text = text_of(file_text(client, export(client, benchmark["id"])["id"], "report.html"))

    # Clear-day car AP 1.00, synthetic fog keeps it (drop 0.00); real fog has no cars, so no drop: never a 0.
    assert re.search(r"PassengerCar 1\.00 \(1\) 1\.00 \(1\) 0\.00\* — \(0\) —", text)


def test_the_heatmap_is_a_shaded_table_with_low_n_cells_marked_by_the_same_legend(client, benchmark):
    html = file_text(client, export(client, benchmark["id"])["id"], "report.html")

    heatmap = html[html.index('id="where-it-fails"'):html.index('id="precision-recall"')]
    assert "<svg" not in heatmap
    assert re.search(r'<td style="background:[^"]+">1\.00\*', heatmap)
    assert "* fewer than 30 objects (low n): read as noise. — no objects of that class." in text_of(heatmap)


def test_precision_recall_is_an_inline_svg_with_curves_labelled_in_text_and_the_threshold_marked(client, benchmark):
    html = file_text(client, export(client, benchmark["id"])["id"], "report.html")

    pr = html[html.index('id="precision-recall"'):]
    pr = pr[:pr.index("</section>")]
    assert pr.count("<svg role=\"img\"") == 4  # one plot per main class
    car = pr[pr.index("PassengerCar"):]
    car = car[:car.index("</figure>")]
    for title in ("Clear · day", "Synthetic fog 0.60", "Real fog · day"):
        assert title in text_of(car)
    assert 'class="threshold"' in car
    assert "display threshold 0.25" in text_of(pr)


def test_without_a_synthetic_run_the_report_says_so_rather_than_leaving_a_gap(client):
    benchmark_id = run_benchmark(client)["experiment_id"]

    text = text_of(file_text(client, export(client, benchmark_id)["id"], "report.html"))

    assert "No synthetic fog run on the Clear · day frames yet." in text
    assert "Synthetic fog: not run on the Clear · day frames yet" in text
    assert "Real fog · day: AP 0.00 over 1 object (low n); nothing predicted, so no curve" in text


def test_without_clear_day_frames_every_finding_still_renders_with_its_reason(client):
    manifest = subset_manifest(client)
    manifest["frames"]["clear-day"] = []
    benchmark_id = run_benchmark(client, manifest)["experiment_id"]

    html = file_text(client, export(client, benchmark_id)["id"], "report.html")

    assert all(f'id="{key}"' in html for key in BENCHMARK_FINDINGS)
    assert text_of(html).count("no Clear · day frames, so there is nothing to compare against") == 2
    assert '<svg role="img"' not in html


# --- metrics.json and frames.csv: the app's own numbers -----------------------------------------------------


def test_metrics_json_is_the_findings_and_results_the_api_returns_at_the_same_threshold(client, benchmark):
    saved = export(client, benchmark["id"], display_threshold=0.5)

    metrics = json.loads(file_text(client, saved["id"], "metrics.json"))

    assert metrics["findings"] == findings(client, benchmark["id"], display_threshold=0.5)
    assert metrics["results"] == benchmark_results(client, benchmark["id"], display_threshold=0.5)
    assert metrics["export"]["experiment_id"] == benchmark["id"]
    assert metrics["export"]["display_threshold"] == 0.5


def test_frames_csv_is_every_frames_score_as_the_results_api_returns_it(client, benchmark):
    saved = export(client, benchmark["id"], display_threshold=0.5)
    scored = benchmark_results(client, benchmark["id"], display_threshold=0.5)

    rows = list(csv.DictReader(io.StringIO(file_text(client, saved["id"], "frames.csv"))))

    expected = [
        (row["condition"], "", f["id"], f["score"], f["hits"], f["misses"], f["false_alarms"], f["class_confusions"], f["ignored"])
        for row in scored["conditions"]
        for f in row["frame_scores"]
    ] + [
        (row["condition"], row["experiment_id"], f["id"], f["score"], f["hits"], f["misses"], f["false_alarms"],
         f["class_confusions"], f["ignored"])
        for row in scored["synthetic"]
        for f in row["frame_scores"]
    ]  # fmt: skip
    assert [
        (r["condition"], r["synthetic_run"], r["frame_id"], float(r["score"]), int(r["hits"]), int(r["misses"]),
         int(r["false_alarms"]), int(r["class_confusions"]), int(r["ignored"]))
        for r in rows
    ] == expected  # fmt: skip


def test_a_video_runs_metrics_and_frames_are_its_findings_and_stability(video_client):
    job = run_video(video_client)
    saved = export(video_client, job["experiment_id"])
    body = findings(video_client, job["experiment_id"])

    metrics = json.loads(file_text(video_client, saved["id"], "metrics.json"))
    rows = list(csv.DictReader(io.StringIO(file_text(video_client, saved["id"], "frames.csv"))))

    assert metrics["findings"] == body
    assert metrics["results"] == video_client.get(f"/api/experiments/{job['experiment_id']}/stability").json()
    assert metrics["export"]["display_threshold"] is None  # a video run ignores it
    assert metrics["input_fingerprint"] == fingerprint(SAMPLES["synthetic-traffic"].path)
    assert [
        (int(r["index"]), float(r["score"]), int(r["retained"]), int(r["dropped"]), int(r["introduced"]),
         int(r["class_changes"]), float(r["confidence_loss"]))
        for r in rows
    ] == [
        (p["index"], p["score"], p["retained"], p["dropped"], p["introduced"], p["class_changes"], p["confidence_loss"])
        for p in body["timeline"]
    ]  # fmt: skip


# --- saved under exports/ and listed --------------------------------------------------------------------------


def test_an_export_is_saved_under_exports_with_its_three_files(client, benchmark, tmp_path):
    saved = export(client, benchmark["id"])

    folder = tmp_path / "exports" / saved["id"]
    assert sorted(p.name for p in folder.iterdir()) == sorted(FILES)
    assert [(f["name"], f["size_bytes"]) for f in saved["files"]] == [(n, (folder / n).stat().st_size) for n in FILES]
    assert (saved["experiment_id"], saved["kind"], saved["display_threshold"]) == (benchmark["id"], "benchmark", 0.25)
    assert not any(p.name.startswith(".") for p in (tmp_path / "exports").iterdir())  # nothing staged is left


def test_exports_are_listed_newest_first_with_their_files_and_sizes(tmp_path, root):
    client = make_client(tmp_path, root)
    benchmark_id = run_benchmark(client)["experiment_id"]
    video_id = run_video(client)["experiment_id"]
    first = export(client, benchmark_id)
    second = export(client, video_id)
    third = export(client, benchmark_id, display_threshold=0.5)

    listed = client.get("/api/exports").json()

    assert [e["id"] for e in listed] == [third["id"], second["id"], first["id"]]
    assert listed[1] == second
    assert listed[1]["kind"] == "video" and listed[1]["title"].startswith("Gaussian blur 0.10 on")
    assert len({e["id"] for e in listed}) == 3  # two exports of one run in a second are still two


def test_a_restarted_app_still_lists_its_exports(tmp_path, root):
    client = make_client(tmp_path, root)
    saved = export(client, run_benchmark(client)["experiment_id"])

    assert make_client(tmp_path, root).get("/api/exports").json() == [saved]


def test_no_exports_yet_is_an_empty_list(tmp_path):
    assert make_client(tmp_path).get("/api/exports").json() == []


def test_an_export_folder_damaged_by_hand_is_left_out_of_the_list(client, benchmark, tmp_path):
    saved = export(client, benchmark["id"])
    (tmp_path / "exports" / saved["id"] / "metrics.json").write_text("not json")
    (tmp_path / "exports" / "notes").mkdir()

    assert client.get("/api/exports").json() == []


# --- refusals ---------------------------------------------------------------------------------------------


def test_an_unknown_run_cannot_be_exported(client):
    response = client.post(f"/api/findings/{'0' * 64}/exports", params={"display_threshold": 0.25})

    assert response.status_code == 404


def test_a_benchmark_export_needs_a_display_threshold_in_range(client, benchmark):
    for params in ({}, {"display_threshold": 1.5}):
        assert client.post(f"/api/findings/{benchmark['id']}/exports", params=params).status_code == 422


@pytest.mark.parametrize("name", ["report.pdf", "..%2Fmetrics.json", "experiment.json"])
def test_only_an_exports_own_files_are_served(client, benchmark, name):
    saved = export(client, benchmark["id"])

    assert client.get(f"/api/exports/{saved['id']}/{name}").status_code in (404, 422)


@pytest.mark.parametrize("export_id", ["nope", "..", "20261001-000000-abc"])
def test_an_unknown_export_has_no_files(client, export_id):
    assert client.get(f"/api/exports/{export_id}/report.html").status_code == 404


def test_served_files_carry_their_media_types(client, benchmark):
    saved = export(client, benchmark["id"])

    types = {name: client.get(f"/api/exports/{saved['id']}/{name}").headers["content-type"] for name in FILES}

    assert types["report.html"].startswith("text/html")
    assert types["metrics.json"].startswith("application/json")
    assert types["frames.csv"].startswith("text/csv")
