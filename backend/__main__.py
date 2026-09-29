"""Start the whole app on one local port: python -m backend"""

import argparse
import os
import sys
from pathlib import Path

import uvicorn

from backend.app import create_app
from backend.dataset import DATASET_ENV_VAR
from backend.detection import ModelRunner
from backend.stub_runner import StubRunner
from backend.yolox_runner import MODEL_PATH, YoloxRunner

# Hard-coded on purpose: the lab never listens beyond this machine.
HOST = "127.0.0.1"

# Per-frame delay for --runner stub, so a browser can watch a run's progress.
STUB_LATENCY_S = 0.05


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m backend", description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--dev",
        action="store_true",
        help="allow cross-origin requests from the Vite dev server",
    )
    parser.add_argument(
        "--runner",
        choices=["yolox", "stub"],
        default="yolox",
        help="detector to run: YOLOX-Nano on CPU, or a deterministic stub for tests (default: yolox)",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=os.environ.get(DATASET_ENV_VAR) or None,
        help=f"local SeeingThroughFog folder (default: ${DATASET_ENV_VAR}; optional, Synthetic mode works without it)",
    )
    return parser


def build_runner(kind: str, model_path: Path) -> ModelRunner | None:
    """The chosen detector, or None when the real one's weights are missing (the app still starts)."""
    if kind == "stub":
        return StubRunner(simulated_latency_s=STUB_LATENCY_S)
    if not model_path.is_file():
        print(
            f"Detector weights not found at {model_path}; runs are disabled.\n"
            "Fetch them with: .venv/Scripts/python.exe scripts/fetch_model.py",
            file=sys.stderr,
        )
        return None
    return YoloxRunner(model_path)


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    runner = build_runner(args.runner, MODEL_PATH)
    uvicorn.run(create_app(dev=args.dev, runner=runner, dataset_root=args.dataset), host=HOST, port=args.port)


if __name__ == "__main__":
    main()
