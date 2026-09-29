"""YOLOX-Nano, pretrained on COCO, run through ONNX Runtime on the CPU.

Weights: Megvii's official ONNX export (Apache-2.0), fetched by scripts/fetch_model.py.
Pre- and post-processing follow YOLOX's own ONNX demo: letterbox to 416 px padded with gray
(114), raw BGR 0-255 input, then grid decoding, objectness x class score, and per-class NMS.
"""

from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

from backend.detection import Box, Detection, ModelInfo, check_input

MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "yolox_nano.onnx"
MODEL_URL = "https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1.1rc0/yolox_nano.onnx"
MODEL_SHA256 = "c789161ed43c8269fcd4e67c67eeeb4e80c622da2eb296a20bc6007bd18a0b7d"

INPUT_SIZE = 416
STRIDES = (8, 16, 32)
NMS_IOU = 0.45
PAD_VALUE = 114

# fmt: off
COCO_CLASSES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
    "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat", "dog",
    "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella",
    "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball", "kite",
    "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket", "bottle",
    "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
    "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch", "potted plant",
    "bed", "dining table", "toilet", "tv", "laptop", "mouse", "remote", "keyboard", "cell phone",
    "microwave", "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase", "scissors",
    "teddy bear", "hair drier", "toothbrush",
]
# fmt: on


def _grid() -> tuple[np.ndarray, np.ndarray]:
    """Each anchor's (column, row) cell and its stride, in the order the head emits them."""
    cells, strides = [], []
    for stride in STRIDES:
        n = INPUT_SIZE // stride
        rows, cols = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
        cells.append(np.stack((cols, rows), axis=2).reshape(-1, 2))
        strides.append(np.full((n * n, 1), stride))
    return np.concatenate(cells), np.concatenate(strides)


GRID, GRID_STRIDES = _grid()


def letterbox(image: np.ndarray) -> tuple[np.ndarray, float]:
    """Scale to fit INPUT_SIZE, pad bottom-right with gray. Returns the NCHW tensor and the scale ratio."""
    height, width = image.shape[:2]
    ratio = min(INPUT_SIZE / height, INPUT_SIZE / width)
    resized = cv2.resize(image, (int(width * ratio), int(height * ratio)), interpolation=cv2.INTER_LINEAR)
    padded = np.full((INPUT_SIZE, INPUT_SIZE, 3), PAD_VALUE, np.uint8)
    padded[: resized.shape[0], : resized.shape[1]] = resized
    return padded.transpose(2, 0, 1)[None].astype(np.float32), ratio


def decode(raw: np.ndarray, ratio: float, width: int, height: int, confidence_threshold: float) -> list[Detection]:
    """Turn the raw head output (anchors x 85) into normalized detections for a width x height image."""
    scores = raw[:, 4:5] * raw[:, 5:]  # objectness x per-class score, both already sigmoid
    class_ids = scores.argmax(axis=1)
    confidences = scores[np.arange(len(scores)), class_ids]
    keep = confidences >= confidence_threshold
    if not keep.any():
        return []

    raw, class_ids, confidences = raw[keep], class_ids[keep], confidences[keep]
    centers = (raw[:, 0:2] + GRID[keep]) * GRID_STRIDES[keep] / ratio
    sizes = np.exp(raw[:, 2:4]) * GRID_STRIDES[keep] / ratio
    corners = np.concatenate((centers - sizes / 2, centers + sizes / 2), axis=1)

    xywh = np.concatenate((corners[:, :2], sizes), axis=1)
    kept = cv2.dnn.NMSBoxesBatched(xywh.tolist(), confidences.tolist(), class_ids.tolist(), confidence_threshold, NMS_IOU)

    scale = np.array([width, height, width, height], np.float64)
    detections = []
    for i in sorted(np.asarray(kept).reshape(-1), key=lambda i: -confidences[i]):
        x1, y1, x2, y2 = np.clip(corners[i] / scale, 0.0, 1.0)
        detections.append(
            Detection(
                label=COCO_CLASSES[class_ids[i]],
                confidence=float(confidences[i]),
                box=Box(x1=float(x1), y1=float(y1), x2=float(x2), y2=float(y2)),
            )
        )
    return detections


class YoloxRunner:
    def __init__(self, model_path: Path):
        self.session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name
        self.info = ModelInfo(
            name="YOLOX-Nano (COCO)",
            version=f"0.1.1rc0 sha256:{MODEL_SHA256[:12]}",
            runtime=f"onnxruntime {ort.__version__} ({self.session.get_providers()[0]})",
        )

    def detect(self, image: np.ndarray, confidence_threshold: float) -> list[Detection]:
        check_input(image, confidence_threshold)
        tensor, ratio = letterbox(image)
        raw = self.session.run(None, {self.input_name: tensor})[0][0]
        height, width = image.shape[:2]
        return decode(raw, ratio, width, height, confidence_threshold)
