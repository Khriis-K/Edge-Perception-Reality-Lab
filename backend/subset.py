"""Seeded per-condition subsets of the dataset, and the counts that say whether each is large enough to trust."""

import random
from dataclasses import dataclass

from backend.conditions import CONDITIONS, VOCABULARY_VERSION
from backend.dataset import Frame
from backend.labels import MAIN_CLASSES

DEFAULT_SEED = 0
DEFAULT_CAP = 300
MAX_CAP = 100_000
# A per-class AP over fewer objects than this is mostly noise, so the condition is flagged "low n".
# The stability metrics reuse it for detections: a rate near 80% over 30 is still about +/-15 points.
LOW_N_OBJECTS = 30


@dataclass(frozen=True)
class Manifest:
    seed: int
    cap: int
    vocabulary_version: int
    frames: dict[str, list[str]]  # condition -> sorted sample ids, every condition present


@dataclass(frozen=True)
class ConditionSummary:
    condition: str
    frames: int
    objects: int
    smallest_class: str
    smallest_class_count: int
    low_n: bool


def draw_subset(frames: list[Frame], seed: int, cap: int) -> Manifest:
    """Up to `cap` frames per condition, drawn with `seed`. The same inputs always give the same manifest."""
    if cap < 1:
        raise ValueError(f"The per-condition cap must be at least 1, got {cap}.")
    chosen = {}
    for condition in CONDITIONS:
        # Sorted, so the draw doesn't depend on the order the files were listed in; one generator per condition,
        # so adding frames to one condition leaves the others' draw unchanged.
        pool = sorted(f.id for f in frames if f.condition == condition)
        rng = random.Random(f"{seed}:{condition}")
        chosen[condition] = sorted(rng.sample(pool, min(cap, len(pool))))
    return Manifest(seed, cap, VOCABULARY_VERSION, chosen)


def summarize(frames: list[Frame], manifest: Manifest) -> list[ConditionSummary]:
    """Per condition, in vocabulary order: frames and main-class objects in the manifest, and the rarest class."""
    by_id = {f.id: f for f in frames}
    rows = []
    for condition in CONDITIONS:
        chosen = [by_id[i] for i in manifest.frames[condition]]
        counts = {c: sum(f.class_counts.get(c, 0) for f in chosen) for c in MAIN_CLASSES}
        smallest = min(MAIN_CLASSES, key=lambda c: counts[c])
        rows.append(
            ConditionSummary(
                condition=condition,
                frames=len(chosen),
                objects=sum(counts.values()),
                smallest_class=smallest,
                smallest_class_count=counts[smallest],
                low_n=counts[smallest] < LOW_N_OBJECTS,
            )
        )
    return rows
