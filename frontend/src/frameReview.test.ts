import { describe, expect, test } from "vitest";
import type { FrameDetail, FrameLevel, FrameScore } from "./api/client";
import {
  clearCounterpart,
  describeSelection,
  levelAt,
  overlayItems,
  rankFrames,
  scoreParts,
  sortFrames,
  unmappedAt,
} from "./frameReview";

const box = (x1: number) => ({ x1, y1: 0.2, x2: x1 + 0.2, y2: 0.6 });
const score = (id: string, value: number, parts: Partial<FrameScore> = {}): FrameScore => ({
  id,
  hits: 0,
  misses: 0,
  false_alarms: 0,
  class_confusions: 0,
  ignored: 0,
  score: value,
  ...parts,
});

// The fixture's snow-day frame, as the server sends it: a car on a LargeVehicle, a stray person, a missed Pedestrian,
// plus a DontCare region forgiving a low bicycle and an excluded label.
const frame: FrameDetail = {
  id: "f",
  condition: "snow-day",
  weights: { misses: 1, false_alarms: 1, class_confusions: 1 },
  predictions: [
    { label: "PassengerCar", confidence: 0.9, box: box(0) },
    { label: "Pedestrian", confidence: 0.3, box: box(0.3) },
    { label: "RidableVehicle", confidence: 0.1, box: box(0.6) },
  ],
  unmapped: [
    { label: "cat", confidence: 0.7, box: box(0.1) },
    { label: "dog", confidence: 0.2, box: box(0.1) },
  ],
  truths: [
    { label: "LargeVehicle", role: "object", box: box(0) },
    { label: "Pedestrian", role: "object", box: box(0.5) },
    { label: "DontCare", role: "ignore", box: box(0.6) },
    { label: "train", role: "excluded", box: box(0.2) },
  ],
  levels: [
    level(null, [
      { outcome: "miss", prediction: null, truth: 0, iou: null },
      { outcome: "miss", prediction: null, truth: 1, iou: null },
    ]),
    level(0.9, [
      { outcome: "class_confusion", prediction: 0, truth: 0, iou: 1 },
      { outcome: "miss", prediction: null, truth: 1, iou: null },
    ]),
    level(0.3, [
      { outcome: "class_confusion", prediction: 0, truth: 0, iou: 1 },
      { outcome: "false_alarm", prediction: 1, truth: null, iou: null },
      { outcome: "miss", prediction: null, truth: 1, iou: null },
    ]),
    level(0.1, [
      { outcome: "class_confusion", prediction: 0, truth: 0, iou: 1 },
      { outcome: "false_alarm", prediction: 1, truth: null, iou: null },
      { outcome: "ignored", prediction: 2, truth: 2, iou: 1 },
      { outcome: "miss", prediction: null, truth: 1, iou: null },
    ]),
  ],
};

function level(min_confidence: number | null, matches: FrameLevel["matches"]): FrameLevel {
  // The score's counts don't matter to these tests; the server computes them.
  return { min_confidence, matches, score: score("f", matches.length) };
}

describe("rankFrames", () => {
  test("puts the worst frame first and keeps manifest order on ties", () => {
    const ranked = rankFrames([score("a", 1), score("b", 3), score("c", 1), score("d", 2)]);
    expect(ranked.map((f) => f.id)).toEqual(["b", "d", "a", "c"]);
  });
});

describe("scoreParts", () => {
  test("names each part of the score", () => {
    expect(scoreParts(score("a", 4, { misses: 2, false_alarms: 1, class_confusions: 1 }))).toBe(
      "2 misses · 1 false alarm · 1 confusion",
    );
  });

  test("says so when a frame has no errors", () => {
    expect(scoreParts(score("a", 0, { hits: 3 }))).toBe("no errors");
  });
});

describe("levelAt", () => {
  test("shows the predictions at or above the threshold", () => {
    expect(levelAt(frame.levels, 0.25).min_confidence).toBe(0.3);
    expect(levelAt(frame.levels, 0.3).min_confidence).toBe(0.3);
    expect(levelAt(frame.levels, 0.05).min_confidence).toBe(0.1);
  });

  test("shows nothing above the most confident prediction", () => {
    expect(levelAt(frame.levels, 0.95).min_confidence).toBeNull();
  });
});

describe("overlayItems", () => {
  const items = overlayItems(frame, levelAt(frame.levels, 0.05));
  const tags = (layer: string) => items.filter((i) => i.layer === layer).map((i) => i.text);

  test("tags every label with what became of it", () => {
    expect(tags("labels")).toEqual(["CLASS ✕ · LargeVehicle", "MISS · Pedestrian"]);
  });

  test("tags every prediction shown with its outcome, class and confidence", () => {
    expect(tags("predictions")).toEqual([
      "CLASS ✕ · PassengerCar 0.90",
      "FALSE ALARM · Pedestrian 0.30",
      "IGNORED · RidableVehicle 0.10",
    ]);
  });

  test("draws ignore regions on their own layer, and never an excluded label", () => {
    expect(tags("regions")).toEqual(["IGNORE REGION · DontCare"]);
    expect(items.some((i) => i.text.includes("train"))).toBe(false);
  });

  test("marks hits blue, errors orange and ignored ones neutral", () => {
    const hit = overlayItems(
      { ...frame, levels: [] },
      level(0.9, [{ outcome: "hit", prediction: 0, truth: 0, iou: 1 }]),
    );
    expect(hit.filter((i) => i.layer !== "regions").map((i) => [i.text, i.tone])).toEqual([
      ["HIT · LargeVehicle", "ok"],
      ["HIT · PassengerCar 0.90", "ok"],
    ]);
    // Drawing order: regions under labels under predictions.
    expect(items.map((i) => i.tone)).toEqual(["neutral", "error", "error", "error", "error", "neutral"]);
  });

  test("leaves out predictions below the threshold", () => {
    expect(overlayItems(frame, levelAt(frame.levels, 0.5)).filter((i) => i.layer === "predictions")).toHaveLength(1);
  });
});

describe("describeSelection", () => {
  const at = levelAt(frame.levels, 0.05);

  test("a prediction: its match, IoU and error weight", () => {
    expect(describeSelection(frame, at, "prediction-0")).toEqual({
      tag: "CLASS ✕",
      truth: frame.truths[0],
      prediction: frame.predictions[0],
      iou: 1,
      weight: 1,
    });
  });

  test("a label selects the same match as its prediction", () => {
    expect(describeSelection(frame, at, "label-0")).toEqual(describeSelection(frame, at, "prediction-0"));
  });

  test("a miss has no prediction and weighs a miss", () => {
    expect(describeSelection(frame, at, "label-1")).toMatchObject({ tag: "MISS", prediction: null, iou: null, weight: 1 });
  });

  test("hits, ignored predictions and regions weigh nothing", () => {
    expect(describeSelection(frame, at, "prediction-2")).toMatchObject({ tag: "IGNORED", weight: 0 });
    expect(describeSelection(frame, at, "region-2")).toMatchObject({ tag: "IGNORE REGION", prediction: null, weight: 0 });
  });

  test("a prediction below the threshold is no longer selected", () => {
    expect(describeSelection(frame, levelAt(frame.levels, 0.5), "prediction-1")).toBeNull();
  });
});

describe("unmappedAt", () => {
  test("counts the unscored detections at or above the threshold", () => {
    expect(unmappedAt(frame, 0.25)).toBe(1);
    expect(unmappedAt(frame, 0.1)).toBe(2);
  });
});

describe("clearCounterpart", () => {
  test("compares with clear weather in the same light", () => {
    expect(clearCounterpart("fog-night")).toBe("clear-night");
    expect(clearCounterpart("snow-day")).toBe("clear-day");
  });
});

describe("sortFrames", () => {
  const rows = [score("a", 1, { misses: 1 }), score("b", 3, { hits: 2 }), score("c", 2, { hits: 1 })];

  test("sorts by any column, either way", () => {
    expect(sortFrames(rows, "score", "descending").map((r) => r.id)).toEqual(["b", "c", "a"]);
    expect(sortFrames(rows, "hits", "ascending").map((r) => r.id)).toEqual(["a", "c", "b"]);
    expect(sortFrames(rows, "id", "descending").map((r) => r.id)).toEqual(["c", "b", "a"]);
  });

  test("leaves the input untouched", () => {
    sortFrames(rows, "score", "descending");
    expect(rows.map((r) => r.id)).toEqual(["a", "b", "c"]);
  });
});
