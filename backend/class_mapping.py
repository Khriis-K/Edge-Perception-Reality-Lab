"""How the detector's COCO classes and the dataset's labels enter Benchmark metrics.

Class mapping (version 1):

| COCO                | Dataset class  |
| ------------------- | -------------- |
| car                 | PassengerCar   |
| truck, bus          | LargeVehicle   |
| bicycle, motorcycle | RidableVehicle |
| person              | Pedestrian     |

Every other COCO class is excluded from benchmark metrics, though it stays in the raw detections.
Pedestrian is generic category detection only: no identity, attribute, facial or biometric analysis.

Ground-truth labels play one of three roles:
- object: one of the four main classes, scored as a hit or a miss;
- ignore region: the fallback classes Vehicle and Obstacle (the annotator could not tell the type), DontCare, and
  every *_is_group crowd box. They count as neither hits nor misses, and a prediction overlapping one at the matching
  IoU threshold is not a false alarm;
- excluded: anything else (a stray `person` or `train` in the real labels). It is dropped, like an unmapped class.

Changing the mapping or the ignore rule changes the metrics, so bump CLASS_MAPPING_VERSION with it.
"""

from typing import Literal

from pydantic import BaseModel

from backend.detection import Detection
from backend.labels import MAIN_CLASSES

CLASS_MAPPING_VERSION = 1

COCO_TO_DATASET = {
    "car": "PassengerCar",
    "truck": "LargeVehicle",
    "bus": "LargeVehicle",
    "bicycle": "RidableVehicle",
    "motorcycle": "RidableVehicle",
    "person": "Pedestrian",
}

IGNORE_CLASSES = ("Vehicle", "Obstacle", "DontCare")
GROUP_SUFFIX = "_is_group"

IGNORE_RULE = (
    "Objects labelled Vehicle or Obstacle (the dataset's fallback classes), DontCare, or a *_is_group crowd box are "
    "ignore regions: they count as neither hits nor misses, and a prediction overlapping one at the matching IoU "
    "threshold is not a false alarm."
)
UNMAPPED_RULE = "COCO classes with no counterpart are excluded from benchmark metrics but kept in the raw detections."

TruthRole = Literal["object", "ignore", "excluded"]


class MappingRow(BaseModel):
    coco: str
    dataset_class: str


class ClassMapping(BaseModel):
    version: int
    mapping: list[MappingRow]
    ignore_labels: list[str]
    ignore_rule: str
    unmapped_rule: str


CLASS_MAPPING = ClassMapping(
    version=CLASS_MAPPING_VERSION,
    mapping=[MappingRow(coco=coco, dataset_class=cls) for coco, cls in COCO_TO_DATASET.items()],
    ignore_labels=[*IGNORE_CLASSES, f"*{GROUP_SUFFIX}"],
    ignore_rule=IGNORE_RULE,
    unmapped_rule=UNMAPPED_RULE,
)


def dataset_class(coco_label: str) -> str | None:
    """The dataset class a COCO label counts as, or None when it has no counterpart."""
    return COCO_TO_DATASET.get(coco_label)


def truth_role(label: str) -> TruthRole:
    if label in MAIN_CLASSES:
        return "object"
    if label in IGNORE_CLASSES or (label.endswith(GROUP_SUFFIX) and label.removesuffix(GROUP_SUFFIX)):
        return "ignore"
    return "excluded"


def map_detections(detections: list[Detection]) -> list[Detection]:
    """Copies of the mappable detections, relabelled with their dataset class. Unmapped ones are left out."""
    return [d.model_copy(update={"label": COCO_TO_DATASET[d.label]}) for d in detections if d.label in COCO_TO_DATASET]
