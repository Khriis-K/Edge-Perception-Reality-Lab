"""The dataset folder is set only at startup: --dataset, else the EDGE_LAB_DATASET environment variable."""

from pathlib import Path

import pytest

import backend.__main__ as entry


@pytest.fixture
def started(monkeypatch):
    """Capture the dataset root the app was created with, without starting a server."""
    seen = {}
    monkeypatch.setattr(entry.uvicorn, "run", lambda app, **kw: None)
    monkeypatch.setattr(entry, "create_app", lambda **kw: seen.update(kw))
    monkeypatch.delenv("EDGE_LAB_DATASET", raising=False)
    return seen


def test_no_dataset_by_default(started):
    entry.main([])

    assert started["dataset_root"] is None


def test_flag_sets_dataset_root(started, tmp_path):
    entry.main(["--dataset", str(tmp_path)])

    assert started["dataset_root"] == Path(tmp_path)


def test_environment_variable_sets_dataset_root(started, monkeypatch, tmp_path):
    monkeypatch.setenv("EDGE_LAB_DATASET", str(tmp_path))

    entry.main([])

    assert started["dataset_root"] == Path(tmp_path)


def test_flag_wins_over_environment_variable(started, monkeypatch, tmp_path):
    monkeypatch.setenv("EDGE_LAB_DATASET", str(tmp_path / "from-env"))

    entry.main(["--dataset", str(tmp_path / "from-flag")])

    assert started["dataset_root"] == tmp_path / "from-flag"


def test_empty_environment_variable_means_no_dataset(started, monkeypatch):
    monkeypatch.setenv("EDGE_LAB_DATASET", "")

    entry.main([])

    assert started["dataset_root"] is None
