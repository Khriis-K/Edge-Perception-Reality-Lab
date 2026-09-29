"""HTTP API routes. Pydantic models here define the OpenAPI schema the frontend types come from."""

from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict

from backend.dataset import FrameNotFound, camera_image, check_readiness

router = APIRouter(prefix="/api")


class HealthResponse(BaseModel):
    status: Literal["ok"]


class DatasetPartStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: Literal["camera", "labels", "metadata"]
    name: str
    folder: str
    checked: bool
    present: bool
    message: str
    detail: str


class DatasetStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    configured: bool
    root: str | None
    ready: bool
    message: str
    parts: list[DatasetPartStatus]
    not_needed: list[str]


@router.get("/health")
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/dataset/status")
def dataset_status(request: Request) -> DatasetStatusResponse:
    """Re-check the dataset folder set at startup. The folder itself can't be changed from here."""
    return DatasetStatusResponse.model_validate(check_readiness(request.app.state.dataset_root))


@router.get(
    "/dataset/frames/{sample_id}",
    response_class=FileResponse,
    responses={200: {"content": {"image/png": {}}}, 404: {"description": "No such frame"}},
)
def dataset_frame(sample_id: str, request: Request) -> FileResponse:
    """A dataset sample's tone-mapped camera image, looked up by sample id only."""
    try:
        return FileResponse(camera_image(request.app.state.dataset_root, sample_id), media_type="image/png")
    except FrameNotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
