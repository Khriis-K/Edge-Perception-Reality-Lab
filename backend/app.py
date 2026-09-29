"""Application factory: the API plus the built single-page frontend."""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse

from backend.api import router

DEFAULT_STATIC_DIR = Path(__file__).resolve().parents[1] / "frontend" / "dist"

# Only the local Vite dev server may call the API cross-origin, and only in dev mode.
VITE_DEV_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


def create_app(static_dir: Path = DEFAULT_STATIC_DIR, dev: bool = False) -> FastAPI:
    # No /docs or /redoc: they load Swagger UI and ReDoc from a CDN. /openapi.json stays.
    app = FastAPI(title="Edge Perception Reliability Lab", version="0.1.0", docs_url=None, redoc_url=None)
    app.include_router(router)

    if dev:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=VITE_DEV_ORIGINS,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    _serve_frontend(app, static_dir.resolve())
    return app


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
