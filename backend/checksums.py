"""Verify downloaded SeeingThroughFog archives: python -m backend.checksums ARCHIVE_FOLDER

Checks each archive against SeeingThroughFog_sha256sum.txt, copied verbatim from the dataset's repository
(princeton-computational-imaging/SeeingThroughFog, commit 0b1b530). Prints PASS, FAIL or MISSING per archive
and exits 0 only if every archive passes.
"""

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

PUBLISHED_SUMS = Path(__file__).with_name("SeeingThroughFog_sha256sum.txt")

# sha256sum output: "<64 hex>  name" (text mode) or "<64 hex> *name" (binary mode).
SUM_LINE = re.compile(r"([0-9a-fA-F]{64}) [ *](.+)")
CHUNK = 1 << 20


@dataclass(frozen=True)
class ArchiveCheck:
    name: str
    status: Literal["pass", "fail", "missing"]


def parse_checksums(text: str) -> dict[str, str]:
    sums = {}
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        match = SUM_LINE.fullmatch(line.strip())
        if not match:
            raise ValueError(f"Malformed checksum on line {number}: {line!r}")
        sums[match[2]] = match[1].lower()
    return sums


def verify_archives(folder: Path, expected: dict[str, str]) -> list[ArchiveCheck]:
    results = []
    for name, digest in expected.items():
        archive = folder / name
        if not archive.is_file():
            results.append(ArchiveCheck(name, "missing"))
        else:
            results.append(ArchiveCheck(name, "pass" if _sha256(archive) == digest else "fail"))
    return results


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m backend.checksums", description=__doc__.splitlines()[0])
    parser.add_argument("folder", type=Path, help="folder containing the downloaded SeeingThroughFogCompressed.* files")
    parser.add_argument("--sums", type=Path, default=PUBLISHED_SUMS, help="sha256sum-format list (default: the published one)")
    args = parser.parse_args(argv)

    if not args.folder.is_dir():
        print(f"Archive folder not found: {args.folder}", file=sys.stderr)
        return 2

    results = verify_archives(args.folder, parse_checksums(args.sums.read_text()))
    notes = {"pass": "", "fail": "  (checksum does not match: download it again)", "missing": "  (not found in folder)"}
    for result in results:
        print(f"{result.status.upper():<8} {result.name}{notes[result.status]}")

    passed = sum(r.status == "pass" for r in results)
    print(f"{passed} of {len(results)} archives passed.")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
