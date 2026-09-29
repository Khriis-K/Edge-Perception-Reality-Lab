"""Generate a tiny stand-in for SeeingThroughFog: python scripts/make_fixture_dataset.py OUT_DIR

Mirrors the three parts the app reads, as laid out in the real dataset:
    cam_stereo_left_lut/<id>.png            8-bit tone-mapped left camera image
    gt_labels/cam_left_labels_TMP/<id>.txt  KITTI-format labels (upstream adds 3D rotation and visibility columns)
    labeltool_labels/<id>.json              weather / daytime / road / illumination metadata

Everything is generated here, never copied from the real dataset. Output is byte-for-byte deterministic.
"""

import json
import struct
import sys
import zlib
from pathlib import Path

WIDTH, HEIGHT = 160, 80
WEATHERS = ["clear", "light_fog", "dense_fog", "rain", "snow"]
ROAD = {"clear": "dry", "light_fog": "dry", "dense_fog": "wet", "rain": "wet", "snow": "full_snow_coverage"}

# One sample per evaluation condition (both fog words, each in day and night overall), plus one sample
# whose weather is not recorded. Objects cover every mapped class, both fallback classes and one bad line.
MALFORMED = "PassengerCar 0.00 0 not-a-number"
SAMPLES = [
    ("2018-02-03_10-00-00_00100", "clear", "day", ["PassengerCar", "Pedestrian"]),
    ("2018-02-03_21-00-00_00100", "clear", "night", ["LargeVehicle"]),
    ("2018-02-04_10-00-00_00200", "light_fog", "day", ["RidableVehicle", "Vehicle"]),
    ("2018-02-04_21-00-00_00200", "dense_fog", "night", ["PassengerCar", "Obstacle"]),
    ("2018-02-05_10-00-00_00300", "rain", "day", ["Pedestrian", MALFORMED]),
    ("2018-02-05_21-00-00_00300", "rain", "night", ["PassengerCar"]),
    ("2018-02-06_10-00-00_00400", "snow", "day", ["LargeVehicle", "Pedestrian"]),
    ("2018-02-06_21-00-00_00400", "snow", "night", ["RidableVehicle"]),
    ("2018-02-07_10-00-00_00500", None, "day", ["PassengerCar"]),
]


def build_fixture_dataset(root: Path) -> list[str]:
    """Write the fixture under root (created if needed) and return its sample ids."""
    images = root / "cam_stereo_left_lut"
    labels = root / "gt_labels" / "cam_left_labels_TMP"
    metadata = root / "labeltool_labels"
    for folder in (images, labels, metadata):
        folder.mkdir(parents=True, exist_ok=True)

    for index, (sample_id, weather, daytime, objects) in enumerate(SAMPLES):
        (images / f"{sample_id}.png").write_bytes(_png(shade=40 + 20 * index))
        # newline="\n" keeps the files identical on Windows and elsewhere.
        label_text = "".join(_label_line(obj, i) + "\n" for i, obj in enumerate(objects))
        (labels / f"{sample_id}.txt").write_text(label_text, newline="\n")
        meta_text = json.dumps(_metadata(weather, daytime), indent=4, sort_keys=True)
        (metadata / f"{sample_id}.json").write_text(meta_text, newline="\n")

    return [sample_id for sample_id, *_ in SAMPLES]


def _label_line(obj: str, i: int) -> str:
    if obj == MALFORMED:
        return obj
    # identity truncated occlusion angle | 2D box: left top right bottom | 3D: h w l x y z orient3d
    # | rotx roty rotz score qx qy qz qw | visibleRGB visibleGated visibleLidar visibleRadar
    left, top = 10 + 45 * i, 20
    box = f"{left:.2f} {top:.2f} {left + 40:.2f} {top + 30:.2f}"
    return f"{obj} 0.00 0 -1.57 {box} 1.50 1.80 4.20 2.00 1.60 15.00 -1.57 0 0 0 1.0 0 0 0 1 1 1 1 0"


def _metadata(weather: str | None, daytime: str) -> dict:
    road = ROAD.get(weather, "dry")
    return {
        "bad_sensor": False,
        "daytime": {"day": daytime == "day", "night": daytime == "night"},
        "meta": {
            "environment": {k: k == road for k in ["dry", "full_snow_coverage", "slushy", "wet"]},
            "illumination": {
                "best_cv_weather": weather == "clear" and daytime == "day",
                "high_dynamic_range": False,
                "low_dynamic_range": False,
                "overall_dark": daytime == "night",
                "sunglare": False,
            },
            "infrastructure": {"highway": False, "in_city": True, "suburban": False, "tunnel": False},
        },
        "objects": {"no_objects": False},
        "rating": {"appropriate": True, "discard": False, "dispensable": False, "interpolate": False, "very_interesting": False},
        "weather": {w: w == weather for w in WEATHERS},
    }


def _png(shade: int) -> bytes:
    """A solid-colour 8-bit RGB PNG, built with the standard library only."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    row = b"\x00" + bytes([shade, shade, shade]) * WIDTH  # filter byte 0, then pixels
    header = struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(row * HEIGHT, 9)) + chunk(b"IEND", b"")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    ids = build_fixture_dataset(Path(sys.argv[1]))
    print(f"Wrote {len(ids)} fixture samples to {sys.argv[1]}")
