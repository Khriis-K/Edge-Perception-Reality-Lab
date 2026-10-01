"""Imagery in an exported report: dataset frames only when asked for, frames of a bundled clip as data URIs, and the
CC BY credit on any report that embeds the Kraków clip's frames."""

import re

import pytest
from test_benchmark_api import root, subset_manifest  # noqa: F401 (root: fixture)
from test_benchmark_api import run_to_completion as run_benchmark
from test_experiments_api import RUN, TERMINAL, wait_for
from test_experiments_api import run_to_completion as run_video
from test_report_api import client, file_text, make_client, text_of, video_client  # noqa: F401 (fixtures)

from backend.samples import SAMPLES, SAMPLES_DIR

DATA_IMAGE = re.compile(r'<img [^>]*src="data:image/jpeg;base64,[A-Za-z0-9+/=]+"')


def report_html(client, experiment_id, **params):
    params = {"display_threshold": 0.25, **params}
    response = client.get(f"/api/findings/{experiment_id}/report/report.html", params=params)
    assert response.status_code == 200, response.text
    return response.text


def worst_ids(client, experiment_id):
    return [f["id"] for f in client.get(f"/api/findings/{experiment_id}", params={"display_threshold": 0.25}).json()["worst_frames"]]


# --- dataset imagery: off unless asked for ----------------------------------------------------------------


def test_a_benchmark_report_holds_no_dataset_imagery_by_default(client):
    html = report_html(client, run_benchmark(client)["experiment_id"])

    assert "<img" not in html and "data:image" not in html
    assert "named by id only" in text_of(html)


def test_a_benchmark_report_embeds_its_worst_frames_when_dataset_imagery_is_on(client):
    experiment_id = run_benchmark(client)["experiment_id"]
    ids = worst_ids(client, experiment_id)

    html = report_html(client, experiment_id, dataset_imagery=True)

    assert ids
    assert len(DATA_IMAGE.findall(html)) == len(ids)
    assert all(f'alt="Frame {frame_id}"' in html for frame_id in ids)


def test_the_saved_export_follows_the_dataset_imagery_choice(client):
    experiment_id = run_benchmark(client)["experiment_id"]
    params = {"display_threshold": 0.25}

    plain = client.post(f"/api/findings/{experiment_id}/exports", params=params).json()
    with_images = client.post(f"/api/findings/{experiment_id}/exports", params={**params, "dataset_imagery": True}).json()

    assert "data:image" not in file_text(client, plain["id"], "report.html")
    assert "data:image" in file_text(client, with_images["id"], "report.html")
    assert file_text(client, plain["id"], "metrics.json") == file_text(client, plain["id"], "metrics.json")


def test_dataset_imagery_never_goes_into_the_data_files(client):
    experiment_id = run_benchmark(client)["experiment_id"]
    saved = client.post(
        f"/api/findings/{experiment_id}/exports", params={"display_threshold": 0.25, "dataset_imagery": True}
    ).json()

    assert "data:image" not in file_text(client, saved["id"], "metrics.json")
    assert "data:image" not in file_text(client, saved["id"], "frames.csv")


# --- frames of a bundled clip -----------------------------------------------------------------------------


def test_a_video_report_embeds_the_clean_and_degraded_worst_frames_as_data_uris(video_client):
    experiment_id = run_clip(video_client, "synthetic-traffic", 1.0)["experiment_id"]
    ids = worst_ids_video(video_client, experiment_id)

    html = report_html(video_client, experiment_id)

    assert ids
    assert len(DATA_IMAGE.findall(html)) == 2 * len(ids)
    assert "<link" not in html and "<script" not in html and "http://" not in html
    assert "https://" not in html  # a generated clip has no credit links either


def run_clip(client, sample_id, severity):
    response = client.post(
        "/api/jobs", json={"sample_id": sample_id, "degradation": {"kind": "darkness", "severity": severity, "seed": 0}}
    )
    assert response.status_code == 202, response.text
    return wait_for(client, response.json()["id"], lambda j: j["status"] in TERMINAL, timeout=120)


def worst_ids_video(client, experiment_id):
    return [f["index"] for f in client.get(f"/api/findings/{experiment_id}", params={"display_threshold": 0.25}).json()["worst_frames"]]


def test_a_report_on_the_generated_clip_carries_no_credit(video_client):
    experiment_id = run_clip(video_client, "synthetic-traffic", 1.0)["experiment_id"]
    text = text_of(report_html(video_client, experiment_id))

    assert "CC BY" not in text and "Relaxing Roads" not in text


def test_a_report_embedding_the_krakow_frames_carries_the_full_credit(video_client):
    job = run_clip(video_client, "krakow-city-driving", 0.1)
    html = report_html(video_client, job["experiment_id"])
    text = text_of(html)

    assert DATA_IMAGE.search(html)
    assert "Relaxing Roads 4K" in text
    assert "CC BY 3.0" in text
    assert 'href="https://creativecommons.org/licenses/by/3.0/"' in html
    assert 'href="https://commons.wikimedia.org/wiki/File:City_Driving_4K-_Krak%C3%B3w_Poland_2024.webm"' in html
    assert "modified" in text.lower()


def test_the_credit_in_samples_matches_samples_credits_md():
    credit = SAMPLES["krakow-city-driving"].credit
    notes = (SAMPLES_DIR / "CREDITS.md").read_text(encoding="utf-8")

    assert credit is not None
    assert credit.author in notes and credit.licence_url in notes and credit.source_url in notes
