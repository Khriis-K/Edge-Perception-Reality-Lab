"""Sample videos bundled with the project. The API refers to them by id, never by path."""

from dataclasses import dataclass
from pathlib import Path

SAMPLES_DIR = Path(__file__).resolve().parents[1] / "samples"


@dataclass(frozen=True)
class Sample:
    id: str
    title: str
    path: Path


SAMPLES = {
    sample.id: sample
    for sample in [
        # First, so the Synthetic screen opens on real footage the detector finds objects in.
        Sample(
            id="krakow-city-driving",
            title="City driving, Kraków (CC BY 3.0)",
            path=SAMPLES_DIR / "krakow_city_driving.mp4",
        ),
        Sample(
            id="synthetic-traffic",
            title="Synthetic traffic (generated)",
            path=SAMPLES_DIR / "synthetic_traffic.mp4",
        ),
    ]
}
