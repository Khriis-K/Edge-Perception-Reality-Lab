"""Model download: the file lands only if its checksum matches the pinned one."""

import hashlib

import pytest

from scripts.fetch_model import ChecksumMismatch, fetch

PAYLOAD = b"pretend these are onnx weights"


@pytest.fixture
def source(tmp_path):
    path = tmp_path / "source.onnx"
    path.write_bytes(PAYLOAD)
    return path.as_uri()


def test_a_matching_download_is_written(tmp_path, source):
    dest = tmp_path / "models" / "model.onnx"

    fetch(source, dest, hashlib.sha256(PAYLOAD).hexdigest())

    assert dest.read_bytes() == PAYLOAD


def test_a_mismatched_download_is_rejected_and_leaves_nothing_behind(tmp_path, source):
    dest = tmp_path / "models" / "model.onnx"

    with pytest.raises(ChecksumMismatch):
        fetch(source, dest, "0" * 64)

    assert list(dest.parent.iterdir()) == []


def test_an_existing_good_file_is_kept_without_downloading(tmp_path):
    dest = tmp_path / "model.onnx"
    dest.write_bytes(PAYLOAD)

    fetch("file:///does/not/exist.onnx", dest, hashlib.sha256(PAYLOAD).hexdigest())

    assert dest.read_bytes() == PAYLOAD
