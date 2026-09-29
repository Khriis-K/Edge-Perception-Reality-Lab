"""Print the backend's OpenAPI schema as JSON. The frontend generates its API types from this."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app import create_app  # noqa: E402

if __name__ == "__main__":
    print(json.dumps(create_app().openapi(), indent=2, sort_keys=True))
