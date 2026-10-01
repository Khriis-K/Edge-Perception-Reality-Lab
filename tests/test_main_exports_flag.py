"""Exports go to the repo's exports/ unless --exports-dir moves them (the e2e tests use a fresh folder per run)."""

from pathlib import Path

import pytest

import backend.__main__ as entry
from backend.app import DEFAULT_EXPORTS_DIR


@pytest.fixture
def started(monkeypatch):
    """Capture the exports folder the app was created with, without starting a server."""
    seen = {}
    monkeypatch.setattr(entry.uvicorn, "run", lambda app, **kw: None)
    monkeypatch.setattr(entry, "create_app", lambda **kw: seen.update(kw))
    return seen


def test_the_repo_exports_folder_by_default(started):
    entry.main([])

    assert started["exports_dir"] == DEFAULT_EXPORTS_DIR


def test_flag_moves_the_exports_folder(started, tmp_path):
    entry.main(["--exports-dir", str(tmp_path)])

    assert started["exports_dir"] == Path(tmp_path)
