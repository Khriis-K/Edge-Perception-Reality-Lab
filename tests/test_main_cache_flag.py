"""The cache folder is the repo's cache/ unless --cache-dir moves it (the e2e tests use a fresh one per run)."""

from pathlib import Path

import pytest

import backend.__main__ as entry
from backend.app import DEFAULT_CACHE_DIR


@pytest.fixture
def started(monkeypatch):
    """Capture the cache folder the app was created with, without starting a server."""
    seen = {}
    monkeypatch.setattr(entry.uvicorn, "run", lambda app, **kw: None)
    monkeypatch.setattr(entry, "create_app", lambda **kw: seen.update(kw))
    return seen


def test_the_repo_cache_folder_by_default(started):
    entry.main([])

    assert started["cache_dir"] == DEFAULT_CACHE_DIR


def test_flag_moves_the_cache_folder(started, tmp_path):
    entry.main(["--cache-dir", str(tmp_path)])

    assert started["cache_dir"] == Path(tmp_path)
