"""HTTP API routes. Pydantic models here define the OpenAPI schema the frontend types come from."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api")


class HealthResponse(BaseModel):
    status: Literal["ok"]


@router.get("/health")
def health() -> HealthResponse:
    return HealthResponse(status="ok")
