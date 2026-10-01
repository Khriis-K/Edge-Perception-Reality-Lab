"""Stamp the built frontend with a digest of the sources it was built from, or check that stamp.

frontend/dist is committed so reviewers can run the app with Python only. `npm run build` stamps it; pytest fails
when the sources have changed since, so a stale bundle can't be committed unnoticed.

    .venv/Scripts/python.exe scripts/frontend_bundle.py stamp
    .venv/Scripts/python.exe scripts/frontend_bundle.py check
"""

import hashlib
import sys
from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[1] / "frontend"
STAMP = "source-digest.txt"

# Everything the bundle is built from. Tests, e2e/ and dev scripts never reach it.
BUILD_INPUTS = ("index.html", "package.json", "package-lock.json", "tsconfig.json", "vite.config.ts")
SOURCE_DIRS = ("src", "public")


def _inputs(frontend: Path) -> list[Path]:
    files = [frontend / name for name in BUILD_INPUTS if (frontend / name).is_file()]
    for folder in SOURCE_DIRS:
        files += [p for p in (frontend / folder).rglob("*") if p.is_file() and ".test." not in p.name]
    return sorted(files, key=lambda p: p.relative_to(frontend).as_posix())


def source_digest(frontend: Path) -> str:
    """SHA-256 over each input's path and content. Line endings are normalized, so a CRLF checkout matches."""
    digest = hashlib.sha256()
    for path in _inputs(frontend):
        digest.update(path.relative_to(frontend).as_posix().encode() + b"\0")
        digest.update(path.read_bytes().replace(b"\r\n", b"\n") + b"\0")
    return digest.hexdigest()


def stamp(frontend: Path) -> None:
    (frontend / "dist" / STAMP).write_text(source_digest(frontend) + "\n")


def is_current(frontend: Path) -> bool:
    stamp_file = frontend / "dist" / STAMP
    return stamp_file.is_file() and stamp_file.read_text().strip() == source_digest(frontend)


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "stamp":
        stamp(FRONTEND)
    elif command == "check":
        if not is_current(FRONTEND):
            sys.exit("frontend/dist is stale: run `npm --prefix frontend run build` and commit frontend/dist")
        print("frontend/dist is current.")
    else:
        sys.exit(__doc__)
