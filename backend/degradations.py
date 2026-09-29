"""The five synthetic degradations, all written here.

Each takes a normalized severity from 0 to 1. The transform's own parameters are derived from it
by `parameters()`, so what the inspector shows and what the experiment records are the values
`degrade()` actually used. Severity 0 leaves the image untouched, except JPEG, which always
re-encodes.

Fog is the homogeneous form of the atmospheric scattering model, I = J*t + A*(1 - t), with one
transmission t for the whole frame. Severity sets t; the airlight A (the fog's own brightness)
stays fixed, so severity means thickness, not color. It is still recorded. In real fog, transmission falls with distance, so near
objects stay clearer and far ones fade faster than this uniform version shows; that is a
limitation of the simulation, not of the detector. It is written from the textbook model.
No code from the SeeingThroughFog repository is used.
"""

import math
from typing import Literal, get_args

import cv2
import numpy as np

DegradationKind = Literal["darkness", "blur", "fog", "noise", "jpeg"]
KINDS: tuple[DegradationKind, ...] = get_args(DegradationKind)

TITLES: dict[DegradationKind, str] = {
    "darkness": "Darkness",
    "blur": "Gaussian blur",
    "fog": "Synthetic fog",
    "noise": "Gaussian noise",
    "jpeg": "JPEG compression",
}

# Only these draw random numbers, so only these depend on the seed.
RANDOMIZED: frozenset[DegradationKind] = frozenset({"noise"})


def parameters(kind: DegradationKind, severity: float) -> dict[str, float]:
    """The transform parameters for this severity, keyed by name. These are what gets recorded."""
    _check_severity(severity)
    if kind == "darkness":
        return {"gain": 1 - 0.9 * severity}
    if kind == "blur":
        return {"sigma_px": 10 * severity}
    if kind == "fog":
        return {"transmission": 1 - 0.9 * severity, "airlight": 0.8}
    if kind == "noise":
        return {"sigma": 50 * severity}
    if kind == "jpeg":
        return {"quality": round(95 - 90 * severity)}
    raise ValueError(f"Unknown degradation: {kind!r}")


def degrade(image: np.ndarray, kind: DegradationKind, severity: float, rng: np.random.Generator) -> np.ndarray:
    """A degraded copy of an 8-bit BGR image, the same size. `rng` is used only by randomized kinds."""
    p = parameters(kind, severity)
    if kind == "darkness":
        return _to_uint8(image * p["gain"])
    if kind == "blur":
        if p["sigma_px"] == 0:
            return image.copy()
        return cv2.GaussianBlur(image, (0, 0), p["sigma_px"])
    if kind == "fog":
        t = p["transmission"]
        return _to_uint8(image * t + 255 * p["airlight"] * (1 - t))
    if kind == "noise":
        if p["sigma"] == 0:
            return image.copy()
        return _to_uint8(image + rng.normal(0, p["sigma"], image.shape))
    # jpeg
    ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, int(p["quality"])])
    if not ok:
        raise ValueError("The image could not be JPEG-encoded.")
    return cv2.imdecode(encoded, cv2.IMREAD_COLOR)


def _check_severity(severity: float) -> None:
    if math.isnan(severity) or not 0 <= severity <= 1:
        raise ValueError(f"Severity must be between 0 and 1, got {severity}.")


def _to_uint8(values: np.ndarray) -> np.ndarray:
    return np.clip(np.rint(values), 0, 255).astype(np.uint8)
