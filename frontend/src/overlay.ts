import type { components } from "./api/schema";

export type Detection = components["schemas"]["Detection"];
export type Box = components["schemas"]["Box"];

/** A box in percent of the frame, so an SVG sized to the image lines up at any display size. */
export interface OverlayRect {
  x: number;
  y: number;
  width: number;
  height: number;
  /** False when the box touches the top edge: the label goes inside it instead. */
  labelAbove: boolean;
}

// Roughly one label's height at typical frame sizes, as a fraction of the frame.
const LABEL_ROOM = 0.06;

export function toOverlayRect(box: Box): OverlayRect {
  return {
    x: box.x1 * 100,
    y: box.y1 * 100,
    width: Math.max(box.x2 - box.x1, 0) * 100,
    height: Math.max(box.y2 - box.y1, 0) * 100,
    labelAbove: box.y1 >= LABEL_ROOM,
  };
}

/** The display threshold filters the raw detections in the browser; no new inference. */
export function visibleDetections(detections: Detection[], threshold: number): Detection[] {
  return detections.filter((d) => d.confidence >= threshold);
}

export function detectionLabel(detection: Detection): string {
  return `${detection.label} ${detection.confidence.toFixed(2)}`;
}
