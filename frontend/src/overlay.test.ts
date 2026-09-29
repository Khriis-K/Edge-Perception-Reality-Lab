import { describe, expect, test } from "vitest";
import { detectionLabel, toOverlayRect, visibleDetections, type Detection } from "./overlay";

const detection = (label: string, confidence: number, box = { x1: 0.1, y1: 0.2, x2: 0.4, y2: 0.6 }): Detection => ({
  label,
  confidence,
  box,
});

describe("toOverlayRect", () => {
  test("maps a normalized box to percentages of the frame", () => {
    expect(toOverlayRect({ x1: 0.25, y1: 0.1, x2: 0.75, y2: 0.6 })).toEqual({
      x: 25,
      y: 10,
      width: 50,
      height: 50,
      labelAbove: true,
    });
  });

  test("is independent of the display size: the full frame is always 0-100", () => {
    expect(toOverlayRect({ x1: 0, y1: 0, x2: 1, y2: 1 })).toMatchObject({ x: 0, y: 0, width: 100, height: 100 });
  });

  test("puts the label inside a box that touches the top edge, so it is never cut off", () => {
    expect(toOverlayRect({ x1: 0.2, y1: 0.02, x2: 0.5, y2: 0.4 }).labelAbove).toBe(false);
  });

  test("keeps a zero-size box at zero size rather than going negative", () => {
    expect(toOverlayRect({ x1: 0.5, y1: 0.5, x2: 0.5, y2: 0.5 })).toMatchObject({ width: 0, height: 0 });
  });
});

describe("visibleDetections", () => {
  const detections = [detection("car", 0.9), detection("person", 0.3), detection("dog", 0.25)];

  test("keeps detections at or above the threshold, in their original order", () => {
    expect(visibleDetections(detections, 0.3).map((d) => d.label)).toEqual(["car", "person"]);
  });

  test("a threshold at the floor shows everything", () => {
    expect(visibleDetections(detections, 0.05)).toEqual(detections);
  });

  test("a threshold above every confidence shows nothing", () => {
    expect(visibleDetections(detections, 0.95)).toEqual([]);
  });
});

describe("detectionLabel", () => {
  test("names the class and the confidence to two decimals", () => {
    expect(detectionLabel(detection("car", 0.8567))).toBe("car 0.86");
  });
});
