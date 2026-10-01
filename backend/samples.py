"""Sample videos bundled with the project. The API refers to them by id, never by path."""

from dataclasses import dataclass
from pathlib import Path

SAMPLES_DIR = Path(__file__).resolve().parents[1] / "samples"


@dataclass(frozen=True)
class Credit:
    """What a licence requires a report to say when it shows a sample's frames; mirrors samples/CREDITS.md."""

    work: str
    author: str
    licence: str
    licence_url: str
    source_url: str
    changes: str


@dataclass(frozen=True)
class Sample:
    id: str
    title: str
    path: Path
    credit: Credit | None = None


SAMPLES = {
    sample.id: sample
    for sample in [
        # First, so the Synthetic screen opens on real footage the detector finds objects in.
        Sample(
            id="krakow-city-driving",
            title="City driving, Kraków (CC BY 3.0)",
            path=SAMPLES_DIR / "krakow_city_driving.mp4",
            credit=Credit(
                work="City Driving 4K- Kraków Poland 2024",
                author="Relaxing Roads 4K",
                licence="CC BY 3.0",
                licence_url="https://creativecommons.org/licenses/by/3.0/",
                source_url="https://commons.wikimedia.org/wiki/File:City_Driving_4K-_Krak%C3%B3w_Poland_2024.webm",
                changes="cut to 7:30–7:50 of the original, resized to 960×540, reduced from 60 to 15 fps and re-encoded "
                "as MPEG-4",
            ),
        ),
        Sample(
            id="synthetic-traffic",
            title="Synthetic traffic (generated)",
            path=SAMPLES_DIR / "synthetic_traffic.mp4",
        ),
    ]
}
