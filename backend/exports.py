"""Exported reports on local disk: <exports>/<export id>/ holds the chosen files of report.html, metrics.json and frames.csv;
export.json stands in for metrics.json's header when that wasn't chosen.

An export is written into a staging folder and renamed into place once every file is written, so a failed export never
leaves a complete-looking folder. The export id names the time and the run (20261001-154612-<12 hex of the run id>),
with -2, -3... when one run is exported twice in a second. The browser only ever names an export by that id and a file
by one of the three names: never a path. Exports are for local use only; deleting the folder is always safe.
"""

import json
import os
import re
import shutil
from pathlib import Path
from threading import Lock
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ValidationError

from backend.report import ExportHeader

EXPORT_ID = re.compile(r"\d{8}-\d{6}-[0-9a-f]{12}(-\d+)?")
ExportFileName = Literal["report.html", "metrics.json", "frames.csv"]
MEDIA_TYPES: dict[ExportFileName, str] = {
    "report.html": "text/html; charset=utf-8",
    "metrics.json": "application/json",
    "frames.csv": "text/csv; charset=utf-8",
}
HEADER_FILE: ExportFileName = "metrics.json"  # its "export" object says what the export is
HEADER_ONLY_FILE = "export.json"  # just that object, for an export saved without metrics.json; never served


class ExportedFile(BaseModel):
    name: ExportFileName
    size_bytes: int


class ExportSummary(ExportHeader):
    id: str
    files: list[ExportedFile]  # in MEDIA_TYPES order


class ExportStore:
    def __init__(self, root: Path):
        self.root = root
        self._naming = Lock()  # so two exports in the same second can't both take one name

    def save(self, header: ExportHeader, files: dict[ExportFileName, str]) -> ExportSummary:
        staging = self.root / f".staging-{uuid4().hex}"
        staging.mkdir(parents=True)
        try:
            for name, text in files.items():
                (staging / name).write_text(text, encoding="utf-8", newline="")
            if HEADER_FILE not in files:
                (staging / HEADER_ONLY_FILE).write_text(header.model_dump_json(indent=2), encoding="utf-8")
            with self._naming:
                export_id = self._free_id(f"{header.created_at:%Y%m%d-%H%M%S}-{header.experiment_id[:12]}")
                os.rename(staging, self.root / export_id)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        return self._summary(export_id, header)

    def exports(self) -> list[ExportSummary]:
        """Every complete export, newest first. A folder edited by hand into something unreadable is left out."""
        if not self.root.is_dir():
            return []
        found = []
        for folder in self.root.iterdir():
            if not EXPORT_ID.fullmatch(folder.name):
                continue
            try:
                header = _header(folder)
            except (OSError, ValueError, KeyError, TypeError, ValidationError):
                continue
            found.append(self._summary(folder.name, header))
        return sorted(found, key=lambda e: (e.created_at, e.id), reverse=True)

    def file(self, export_id: str, name: ExportFileName) -> Path | None:
        """One of an export's files, or None. The id is checked before any path is built from it."""
        if not EXPORT_ID.fullmatch(export_id) or name not in MEDIA_TYPES:
            return None
        path = self.root / export_id / name
        return path if path.is_file() else None

    def _free_id(self, stem: str) -> str:
        export_id, n = stem, 1
        while (self.root / export_id).exists():
            n += 1
            export_id = f"{stem}-{n}"
        return export_id

    def _summary(self, export_id: str, header: ExportHeader) -> ExportSummary:
        folder = self.root / export_id
        files = [
            ExportedFile(name=name, size_bytes=(folder / name).stat().st_size)
            for name in MEDIA_TYPES
            if (folder / name).is_file()
        ]
        return ExportSummary(**header.model_dump(), id=export_id, files=files)


def _header(folder: Path) -> ExportHeader:
    if (folder / HEADER_FILE).is_file():
        return ExportHeader.model_validate(json.loads((folder / HEADER_FILE).read_bytes())["export"])
    return ExportHeader.model_validate_json((folder / HEADER_ONLY_FILE).read_bytes())
