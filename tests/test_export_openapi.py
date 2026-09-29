"""The exported OpenAPI schema is the single source for the frontend's TypeScript types."""

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def export() -> str:
    return subprocess.run(
        [sys.executable, "scripts/export_openapi.py"],
        cwd=REPO, capture_output=True, text=True, check=True,
    ).stdout


def test_export_prints_the_app_schema():
    schema = json.loads(export())

    assert "/api/health" in schema["paths"]
    assert "HealthResponse" in schema["components"]["schemas"]


def test_export_is_deterministic():
    assert export() == export()
