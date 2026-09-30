"""What a finished run records: its settings, the model, and both variants' detections for every frame."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.degradations import DegradationKind
from backend.detection import Detection, ModelInfo

FrameVariant = Literal["clean", "degraded"]


class DegradationSettings(BaseModel):
    """The one degradation an experiment applies. Extra fields are refused, so a second can't sneak in."""

    model_config = ConfigDict(extra="forbid")

    kind: DegradationKind
    severity: float = Field(ge=0, le=1, allow_inf_nan=False)
    # Stored with every experiment; only randomized kinds (noise) draw from it.
    seed: int = Field(ge=0, le=2**32 - 1)


class AppliedDegradation(DegradationSettings):
    """The settings plus the transform parameters derived from the severity."""

    parameters: dict[str, float]


class FrameResult(BaseModel):
    index: int
    clean: list[Detection]
    degraded: list[Detection]


class Experiment(BaseModel):
    id: str
    sample_id: str
    degradation: AppliedDegradation
    model: ModelInfo
    confidence_floor: float
    frame_width: int
    frame_height: int
    frames: list[FrameResult]
