"""Start the whole app on one local port: python -m backend"""

import argparse
import os
from pathlib import Path

import uvicorn

from backend.app import create_app
from backend.dataset import DATASET_ENV_VAR

# Hard-coded on purpose: the lab never listens beyond this machine.
HOST = "127.0.0.1"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m backend", description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--dev",
        action="store_true",
        help="allow cross-origin requests from the Vite dev server",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=os.environ.get(DATASET_ENV_VAR) or None,
        help=f"local SeeingThroughFog folder (default: ${DATASET_ENV_VAR}; optional, Synthetic mode works without it)",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    uvicorn.run(create_app(dev=args.dev, dataset_root=args.dataset), host=HOST, port=args.port)


if __name__ == "__main__":
    main()
