"""The checksum command verifies downloaded archives against the published SHA-256 list."""

import hashlib

import pytest

from backend.checksums import PUBLISHED_SUMS, main, parse_checksums, verify_archives


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def archives(tmp_path):
    """Two tiny stand-in archives and a sums file listing them plus one not downloaded."""
    (tmp_path / "Data.z01").write_bytes(b"part one")
    (tmp_path / "Data.zip").write_bytes(b"part two")
    sums = tmp_path / "sums.txt"
    sums.write_text(
        f"{sha(b'part one')}  Data.z01\n"
        f"{sha(b'part two')}  Data.zip\n"
        f"{sha(b'part three')}  Data.z02\n"
    )
    return tmp_path, sums


def test_parse_accepts_text_and_binary_mode_lines():
    text = f"{'a' * 64}  one.zip\n{'b' * 64} *two.z01\n\n"

    assert parse_checksums(text) == {"one.zip": "a" * 64, "two.z01": "b" * 64}


def test_parse_rejects_malformed_lines():
    with pytest.raises(ValueError, match="line 1"):
        parse_checksums("not a checksum line\n")


def test_published_list_covers_the_split_archive():
    published = parse_checksums(PUBLISHED_SUMS.read_text())

    assert "SeeingThroughFogCompressed.zip" in published
    assert "SeeingThroughFogCompressed.z01" in published


def test_reports_pass_fail_and_missing_per_archive(archives):
    folder, sums = archives
    (folder / "Data.zip").write_bytes(b"corrupted")

    results = verify_archives(folder, parse_checksums(sums.read_text()))

    assert {r.name: r.status for r in results} == {"Data.z01": "pass", "Data.zip": "fail", "Data.z02": "missing"}


def test_command_prints_a_line_per_archive_and_fails_if_any_do(archives, capsys):
    folder, sums = archives

    exit_code = main([str(folder), "--sums", str(sums)])
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "PASS" in out and "Data.z01" in out
    assert "MISSING" in out and "Data.z02" in out
    assert "2 of 3 archives passed" in out


def test_command_succeeds_when_every_archive_passes(archives, capsys):
    folder, sums = archives
    (folder / "Data.z02").write_bytes(b"part three")

    assert main([str(folder), "--sums", str(sums)]) == 0
    assert "3 of 3" in capsys.readouterr().out


def test_command_explains_a_missing_archive_folder(tmp_path, capsys):
    exit_code = main([str(tmp_path / "nowhere")])

    assert exit_code == 2
    assert "not found" in capsys.readouterr().err.lower()
