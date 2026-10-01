"""What the Report screen needs from the API: a preview of the current run's report files, rendered without saving
anything, and an export of only the files the user chose, still listed with the others.

The fixtures are the report export tests' own (see tests/test_report_api.py).
"""

from datetime import datetime

import pytest
from test_benchmark_api import root  # noqa: F401 (fixture)
from test_experiments_api import run_to_completion as run_video
from test_report_api import FILES, benchmark, client, export, file_text, video_client  # noqa: F401 (fixtures)

import backend.api


def preview(client, experiment_id, name, display_threshold=0.25):
    response = client.get(
        f"/api/findings/{experiment_id}/report/{name}", params={"display_threshold": display_threshold}
    )
    assert response.status_code == 200, response.text
    return response


def export_files(client, experiment_id, files, display_threshold=0.25):
    return client.post(
        f"/api/findings/{experiment_id}/exports", params={"display_threshold": display_threshold, "include": files}
    )


# --- preview ----------------------------------------------------------------------------------------------


class FrozenClock(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 10, 1, 15, 46, 12, tzinfo=tz)


@pytest.mark.parametrize("name", FILES)
def test_the_preview_is_the_file_an_export_writes_at_the_same_threshold(client, benchmark, name, monkeypatch):
    monkeypatch.setattr(backend.api, "datetime", FrozenClock)  # so both are made at the same moment
    saved = export(client, benchmark["id"], display_threshold=0.5)

    shown = preview(client, benchmark["id"], name, display_threshold=0.5).text

    assert shown == file_text(client, saved["id"], name)


def test_a_preview_carries_the_files_media_types(client, benchmark):
    types = {name: preview(client, benchmark["id"], name).headers["content-type"] for name in FILES}

    assert types["report.html"].startswith("text/html")
    assert types["metrics.json"].startswith("application/json")
    assert types["frames.csv"].startswith("text/csv")


def test_a_video_run_previews_too(video_client):
    run_id = run_video(video_client)["experiment_id"]

    assert "Reliability timeline" in preview(video_client, run_id, "report.html").text


def test_a_preview_saves_nothing(client, benchmark, tmp_path):
    preview(client, benchmark["id"], "report.html")

    assert client.get("/api/exports").json() == []
    assert not (tmp_path / "exports").exists()


def test_an_unknown_run_or_file_has_no_preview(client, benchmark):
    assert client.get(f"/api/findings/{'0' * 64}/report/report.html?display_threshold=0.25").status_code == 404
    assert client.get(f"/api/findings/{benchmark['id']}/report/report.pdf?display_threshold=0.25").status_code == 422


# --- chosen files -----------------------------------------------------------------------------------------


def test_an_export_writes_only_the_chosen_files(client, benchmark, tmp_path):
    response = export_files(client, benchmark["id"], ["report.html", "frames.csv"])

    assert response.status_code == 201, response.text
    saved = response.json()
    assert [f["name"] for f in saved["files"]] == ["report.html", "frames.csv"]
    assert not (tmp_path / "exports" / saved["id"] / "metrics.json").exists()


def test_an_export_without_metrics_json_is_still_listed(client, benchmark):
    saved = export_files(client, benchmark["id"], ["report.html"]).json()

    assert client.get("/api/exports").json() == [saved]

