"""Application factory: the API plus the built single-page frontend."""

from pathlib import Path
from threading import Lock

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse

from backend.api import router
from backend.detection import ModelRunner
from backend.experiment_cache import ExperimentCache
from backend.exports import ExportStore
from backend.jobs import JobManager

REPO = Path(__file__).resolve().parents[1]
DEFAULT_STATIC_DIR = REPO / "frontend" / "dist"
# Finished runs, kept across restarts. Derived frames for local use only; safe to delete.
DEFAULT_CACHE_DIR = REPO / "cache"
# Exported reports. Local only, like the cache; safe to delete.
DEFAULT_EXPORTS_DIR = REPO / "exports"

# Only the local Vite dev server may call the API cross-origin, and only in dev mode.
VITE_DEV_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


def create_app(
    static_dir: Path = DEFAULT_STATIC_DIR,
    dev: bool = False,
    runner: ModelRunner | None = None,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    dataset_root: Path | None = None,
    exports_dir: Path = DEFAULT_EXPORTS_DIR,
) -> FastAPI:
    """`runner` is the detector; None means no weights are installed, and runs are refused."""
    # No /docs or /redoc: they load Swagger UI and ReDoc from a CDN. /openapi.json stays.
    app = FastAPI(title="Edge Perception Reliability Lab", version="0.1.0", docs_url=None, redoc_url=None)
    app.state.jobs = JobManager(runner, ExperimentCache(cache_dir))
    app.state.exports = ExportStore(exports_dir)
    # Fixed for the app's lifetime: the browser never sends a filesystem path.
    app.state.dataset_root = dataset_root.resolve() if dataset_root else None
    # Built on first use: reading every label and metadata file of the real dataset takes minutes.
    app.state.dataset_index = None
    app.state.dataset_index_lock = Lock()
    app.include_router(router)
    app.add_exception_handler(RequestValidationError, _validation_error)

    if dev:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=VITE_DEV_ORIGINS,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    _serve_frontend(app, static_dir.resolve())
    return app


async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """FastAPI's 422, minus the echoed input: a rejected NaN can't be written back as JSON."""
    errors = [{key: value for key, value in error.items() if key != "input"} for error in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(errors)})


def _serve_frontend(app: FastAPI, static_dir: Path) -> None:
    """Serve built files as-is and index.html for every other client route."""

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404)

        index = static_dir / "index.html"
        if not index.is_file():
            return PlainTextResponse(
                f"Frontend build not found at {static_dir}.\n"
                "Build it with: cd frontend && npm install && npm run build",
                status_code=503,
            )

        file = (static_dir / path).resolve()
        if file.is_relative_to(static_dir) and file.is_file():
            return FileResponse(file)
        return FileResponse(index)
