"""The model-runner boundary: what any detector takes in and gives back.

A runner takes one BGR image and a confidence threshold and returns detections with boxes in
0-1 image coordinates, so nothing downstream depends on the model's input size.
Detections are model outputs, not facts.
"""

import math
from typing import Protocol

import numpy as np
from pydantic import BaseModel, Field


class InvalidInput(ValueError):
    """The image or threshold handed to a runner is unusable."""


class Box(BaseModel):
    """Corners in 0-1 image coordinates: (x1, y1) top-left, (x2, y2) bottom-right."""

    x1: float = Field(ge=0, le=1)
    y1: float = Field(ge=0, le=1)
    x2: float = Field(ge=0, le=1)
    y2: float = Field(ge=0, le=1)


class Detection(BaseModel):
    label: str
    confidence: float = Field(ge=0, le=1)
    box: Box


class ModelInfo(BaseModel):
    name: str
    version: str
    runtime: str


class ModelRunner(Protocol):
    info: ModelInfo

    def detect(self, image: np.ndarray, confidence_threshold: float) -> list[Detection]: ...


def check_input(image: object, confidence_threshold: float) -> None:
    """Raise InvalidInput unless `image` is a non-empty 8-bit BGR array and the threshold is in 0-1."""
    if not isinstance(image, np.ndarray) or image.ndim != 3 or image.shape[2] != 3:
        raise InvalidInput("Expected a color image (height x width x 3).")
    if image.dtype != np.uint8:
        raise InvalidInput(f"Expected an 8-bit image, got {image.dtype}.")
    if image.shape[0] == 0 or image.shape[1] == 0:
        raise InvalidInput("The image is empty.")
    if math.isnan(confidence_threshold) or not 0 <= confidence_threshold <= 1:
        raise InvalidInput(f"Confidence threshold must be between 0 and 1, got {confidence_threshold}.")
