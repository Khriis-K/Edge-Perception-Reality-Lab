"""Download the detector's weights into models/ and verify them against the pinned SHA-256.

    .venv/Scripts/python.exe scripts/fetch_model.py
"""

import hashlib
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.yolox_runner import MODEL_PATH, MODEL_SHA256, MODEL_URL  # noqa: E402


class ChecksumMismatch(Exception):
    pass


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch(url: str, dest: Path, sha256: str) -> None:
    """Download `url` to `dest` unless a file with the right checksum is already there.

    The download goes to a temporary file first, so `dest` only ever holds verified weights.
    """
    if dest.is_file() and sha256_of(dest) == sha256:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_suffix(dest.suffix + ".part")
    try:
        urllib.request.urlretrieve(url, partial)
        actual = sha256_of(partial)
        if actual != sha256:
            raise ChecksumMismatch(f"Downloaded file's SHA-256 is {actual}, expected {sha256}.")
        partial.replace(dest)
    finally:
        partial.unlink(missing_ok=True)


if __name__ == "__main__":
    print(f"Fetching {MODEL_URL}")
    fetch(MODEL_URL, MODEL_PATH, MODEL_SHA256)
    print(f"Verified {MODEL_PATH}")
