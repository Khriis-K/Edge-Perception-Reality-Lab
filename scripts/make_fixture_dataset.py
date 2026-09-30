"""Generate a tiny stand-in for SeeingThroughFog: python scripts/make_fixture_dataset.py OUT_DIR

Mirrors the three parts the app reads, as laid out in the real dataset:
    cam_stereo_left_lut/<id>.png            8-bit tone-mapped left camera image
    gt_labels/cam_left_labels_TMP/<id>.txt  KITTI-format labels (upstream adds 3D rotation and visibility columns)
    labeltool_labels_refined/<id>.json      fog / precipitation / daytime / twilight / road metadata

Everything is generated here, never copied from the real dataset. Output is byte-for-byte deterministic.

Images are a flat grey, except that a PassengerCar listed first is drawn as a bright block exactly over its label box.
The stub detector finds such a block as a car, so a Benchmark run on the fixture has hits, misses, a false alarm and
a forgiven (ignored) prediction to score.
"""

import json
import struct
import sys
import zlib
from pathlib import Path

WIDTH, HEIGHT = 160, 80
BRIGHT = 240  # at or above the stub detector's brightness cut
# One sample per evaluation condition (clear, fog, snow, rain; each by day and by night), using both fog words and
# both snow words. Then the cases the adapter must exclude and count: fog plus snow, twilight, and a malformed label
# line. Objects cover every mapped class and both fallback classes.
MALFORMED = "PassengerCar 0.00 0 not-a-number"
SAMPLES = [
    # id, fog, precipitation, daytime, twilight, objects
    ("2018-02-03_10-00-00_00100", None, None, "day", False, ["PassengerCar", "Pedestrian"]),
    ("2018-02-03_21-00-00_00100", None, None, "night", False, ["LargeVehicle"]),
    ("2018-02-04_10-00-00_00200", "lightFog", None, "day", False, ["RidableVehicle", "Vehicle"]),
    ("2018-02-04_21-00-00_00200", "denseFog", None, "night", False, ["PassengerCar", "Obstacle"]),
    ("2018-02-05_10-00-00_00300", None, "rain", "day", False, ["Pedestrian"]),
    ("2018-02-05_21-00-00_00300", None, "rain", "night", False, ["PassengerCar"]),
    ("2018-02-06_10-00-00_00400", None, "heavySnow", "day", False, ["LargeVehicle", "Pedestrian"]),
    ("2018-02-06_21-00-00_00400", None, "lightSnow", "night", False, ["RidableVehicle"]),
    ("2018-02-07_10-00-00_00500", "lightFog", "lightSnow", "day", False, ["PassengerCar"]),
    ("2018-02-07_17-00-00_00500", None, None, "day", True, ["Pedestrian"]),
    ("2018-02-08_10-00-00_00600", None, "rain", "day", False, ["PassengerCar", MALFORMED]),
]


def build_fixture_dataset(root: Path) -> list[str]:
    """Write the fixture under root (created if needed) and return its sample ids."""
    images = root / "cam_stereo_left_lut"
    labels = root / "gt_labels" / "cam_left_labels_TMP"
    metadata = root / "labeltool_labels_refined"
    for folder in (images, labels, metadata):
        folder.mkdir(parents=True, exist_ok=True)

    for index, (sample_id, fog, precipitation, daytime, twilight, objects) in enumerate(SAMPLES):
        car = _box(0) if objects[0] == "PassengerCar" else None
        (images / f"{sample_id}.png").write_bytes(_png(shade=40 + 20 * index, car=car))
        # newline="\n" keeps the files identical on Windows and elsewhere.
        label_text = "".join(_label_line(obj, i) + "\n" for i, obj in enumerate(objects))
        (labels / f"{sample_id}.txt").write_text(label_text, newline="\n")
        meta_text = json.dumps(_metadata(fog, precipitation, daytime, twilight), indent=4, sort_keys=True)
        (metadata / f"{sample_id}.json").write_text(meta_text, newline="\n")

    return [sample_id for sample_id, *_ in SAMPLES]


def _label_line(obj: str, i: int) -> str:
    if obj == MALFORMED:
        return obj
    # identity truncated occlusion angle | 2D box: left top right bottom | 3D: h w l x y z orient3d
    # | rotx roty rotz score qx qy qz qw | visibleRGB visibleGated visibleLidar visibleRadar
    box = " ".join(f"{v:.2f}" for v in _box(i))
    return f"{obj} 0.00 0 -1.57 {box} 1.50 1.80 4.20 2.00 1.60 15.00 -1.57 0 0 0 1.0 0 0 0 1 1 1 1 0"


def _box(i: int) -> tuple[int, int, int, int]:
    """The i-th object's 2D box in pixels: left, top, right, bottom."""
    left, top = 10 + 45 * i, 20
    return left, top, left + 40, top + 30


def _metadata(fog: str | None, precipitation: str | None, daytime: str, twilight: bool) -> dict:
    """The refined schema: fog and precipitation on separate axes, each with a "no" flag."""
    snowy = precipitation in ("heavySnow", "lightSnow")
    road = "fullSnow" if snowy else "wet" if precipitation == "rain" else "dry"
    return {
        "daytime": {"day": daytime == "day", "night": daytime == "night"},
        "fog": {"no": fog is None, "yes": {"denseFog": fog == "denseFog", "lightFog": fog == "lightFog"}},
        "infrastructure": {"highway": False, "inCity": True, "suburban": False},
        "point_removed": 0,
        "precipitation": {
            "no": precipitation is None,
            "yes": {
                "rain": precipitation == "rain",
                "snow": {"heavySnow": precipitation == "heavySnow", "lightSnow": precipitation == "lightSnow"},
            },
        },
        "roadState": {k: k == road for k in ["dry", "fullSnow", "partialSnow", "wet"]},
        "sidewalkState": {"clean": not snowy, "partialSnow": False, "snowCovered": snowy},
        "tunnel": False,
        "twilight": twilight,
    }


def _png(shade: int, car: tuple[int, int, int, int] | None) -> bytes:
    """An 8-bit grey RGB PNG, with the car's box (right and bottom exclusive) filled bright. Standard library only."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    def row(y: int) -> bytes:
        inside = car is not None and car[1] <= y < car[3]
        pixels = [BRIGHT if inside and car[0] <= x < car[2] else shade for x in range(WIDTH)]
        return b"\x00" + bytes(v for p in pixels for v in (p, p, p))  # filter byte 0, then pixels

    header = struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 2, 0, 0, 0)
    data = zlib.compress(b"".join(row(y) for y in range(HEIGHT)), 9)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", data) + chunk(b"IEND", b"")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    ids = build_fixture_dataset(Path(sys.argv[1]))
    print(f"Wrote {len(ids)} fixture samples to {sys.argv[1]}")
