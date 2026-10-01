"""The built frontend is committed so reviewers need only Python. Its stamp says which sources it was built from."""

from pathlib import Path

import pytest

from scripts.frontend_bundle import BUILD_INPUTS, FRONTEND, STAMP, is_current, source_digest, stamp


@pytest.fixture
def frontend(tmp_path) -> Path:
    root = tmp_path / "frontend"
    (root / "src").mkdir(parents=True)
    (root / "e2e").mkdir()
    for name in BUILD_INPUTS:
        (root / name).write_text(f"{name}\n")
    (root / "src" / "main.tsx").write_text("render();\n")
    (root / "src" / "overlay.ts").write_text("export const x = 1;\n")
    (root / "dist").mkdir()
    (root / "dist" / "index.html").write_text("built\n")
    return root


def test_the_digest_is_stable(frontend):
    assert source_digest(frontend) == source_digest(frontend)


def test_editing_a_source_changes_the_digest(frontend):
    before = source_digest(frontend)

    (frontend / "src" / "overlay.ts").write_text("export const x = 2;\n")

    assert source_digest(frontend) != before


def test_adding_or_renaming_a_source_changes_the_digest(frontend):
    before = source_digest(frontend)

    (frontend / "src" / "overlay.ts").rename(frontend / "src" / "overlays.ts")

    assert source_digest(frontend) != before


def test_a_dependency_change_changes_the_digest(frontend):
    before = source_digest(frontend)

    (frontend / "package-lock.json").write_text('{"lockfileVersion": 3}\n')

    assert source_digest(frontend) != before


@pytest.mark.parametrize("path", ["src/overlay.test.ts", "e2e/run.spec.ts", "dist/assets/index.js"])
def test_files_that_never_reach_the_bundle_are_ignored(frontend, path):
    before = source_digest(frontend)

    (frontend / path).parent.mkdir(parents=True, exist_ok=True)
    (frontend / path).write_text("anything\n")

    assert source_digest(frontend) == before


@pytest.mark.parametrize("path", ["src/.DS_Store", "src/.overlay.ts.swp"])
def test_hidden_clutter_in_the_sources_is_ignored(frontend, path):
    """Untracked OS and editor files must not make a correct bundle look stale."""
    before = source_digest(frontend)

    (frontend / path).write_text("clutter\n")

    assert source_digest(frontend) == before


def test_a_missing_build_input_fails_loudly(frontend):
    """A renamed config (say vite.config.mts) must not silently drop out of the digest."""
    (frontend / "vite.config.ts").unlink()

    with pytest.raises(FileNotFoundError, match="vite.config.ts"):
        source_digest(frontend)


def test_line_endings_dont_matter(frontend):
    """A Windows checkout with autocrlf has CRLF sources; the committed stamp must still match."""
    before = source_digest(frontend)

    (frontend / "src" / "main.tsx").write_bytes(b"render();\r\n")

    assert source_digest(frontend) == before


def test_a_stamped_bundle_is_current_until_a_source_changes(frontend):
    stamp(frontend)
    assert is_current(frontend)

    (frontend / "src" / "main.tsx").write_text("render(app);\n")

    assert not is_current(frontend)


def test_a_bundle_without_a_stamp_is_not_current(frontend):
    assert not is_current(frontend)


def test_the_stamp_lives_in_the_bundle(frontend):
    stamp(frontend)

    assert (frontend / "dist" / STAMP).read_text().strip() == source_digest(frontend)


def test_the_committed_bundle_matches_the_frontend_sources():
    """Fails when the frontend changed without a rebuild. Fix: `npm --prefix frontend run build`, commit dist/."""
    assert (FRONTEND / "dist" / "index.html").is_file(), "frontend/dist is missing: run `npm --prefix frontend run build`"
    assert is_current(FRONTEND), "frontend/dist is stale: run `npm --prefix frontend run build` and commit frontend/dist"
