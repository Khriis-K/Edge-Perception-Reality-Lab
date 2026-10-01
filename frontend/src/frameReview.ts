import type { FrameDetail, FrameLevel, FrameScore, FrameTruth, IndexedMatch } from "./api/client";
import type { Box, Detection } from "./overlay";

type Outcome = IndexedMatch["outcome"];

/** Every overlay carries one of these, so its meaning never rests on color alone. */
const TAGS: Record<Outcome, string> = {
  hit: "HIT",
  miss: "MISS",
  false_alarm: "FALSE ALARM",
  class_confusion: "CLASS ✕",
  ignored: "IGNORED",
};
const REGION_TAG = "IGNORE REGION";

export type Layer = "labels" | "predictions" | "regions";
/** ok is blue (a hit), error orange (a miss, false alarm or confusion), neutral grey (ignored). */
export type Tone = "ok" | "error" | "neutral";

export interface OverlayItem {
  /** Stable across thresholds: indexes the frame's own predictions and truths, not a level's matches. */
  key: string;
  layer: Layer;
  tone: Tone;
  text: string;
  box: Box;
}

export interface Selection {
  tag: string;
  truth: FrameTruth | null;
  prediction: Detection | null;
  iou: number | null;
  /** What this adds to the frame's error score. */
  weight: number;
}

export type FrameColumn = keyof FrameScore;
export type SortDirection = "ascending" | "descending";

/** Worst first. Array sort is stable, so ties keep manifest order. */
export function rankFrames(frames: FrameScore[]): FrameScore[] {
  return [...frames].sort((a, b) => b.score - a.score);
}

/** "2 misses · 1 false alarm · 1 confusion": what the score is made of. */
export function scoreParts(frame: FrameScore): string {
  const parts = [
    counted(frame.misses, "miss", "misses"),
    counted(frame.false_alarms, "false alarm", "false alarms"),
    counted(frame.class_confusions, "confusion", "confusions"),
  ].filter(Boolean);
  return parts.length ? parts.join(" · ") : "no errors";
}

function counted(count: number, one: string, many: string): string {
  return count === 0 ? "" : `${count} ${count === 1 ? one : many}`;
}

/** The level a display threshold shows: the server matched each one afresh, so this is a lookup, not a filter. */
export function levelAt(levels: FrameLevel[], threshold: number): FrameLevel {
  let chosen = levels[0];
  for (const level of levels.slice(1)) {
    if (level.min_confidence !== null && level.min_confidence >= threshold) chosen = level;
  }
  return chosen;
}

/** Everything to draw at this level, regions first so labels and predictions sit on top. Excluded labels aren't drawn. */
export function overlayItems(frame: FrameDetail, level: FrameLevel): OverlayItem[] {
  const regions = frame.truths.flatMap((truth, k): OverlayItem[] =>
    truth.role === "ignore"
      ? [{ key: `region-${k}`, layer: "regions", tone: "neutral", text: `${REGION_TAG} · ${truth.label}`, box: truth.box }]
      : [],
  );
  const labels = frame.truths.flatMap((truth, k): OverlayItem[] => {
    const match = truth.role === "object" ? labelMatch(level, k) : undefined;
    if (!match) return [];
    return [{ key: `label-${k}`, layer: "labels", tone: tone(match.outcome), text: `${TAGS[match.outcome]} · ${truth.label}`, box: truth.box }];
  });
  const predictions = frame.predictions.flatMap((prediction, i): OverlayItem[] => {
    const match = level.matches.find((m) => m.prediction === i);
    if (!match) return [];
    const text = `${TAGS[match.outcome]} · ${prediction.label} ${prediction.confidence.toFixed(2)}`;
    return [{ key: `prediction-${i}`, layer: "predictions", tone: tone(match.outcome), text, box: prediction.box }];
  });
  return [...regions, ...labels, ...predictions];
}

/** What the inspector shows for a selected overlay, or null when it isn't shown at this threshold. */
export function describeSelection(frame: FrameDetail, level: FrameLevel, key: string): Selection | null {
  const [kind, index] = [key.slice(0, key.lastIndexOf("-")), Number(key.slice(key.lastIndexOf("-") + 1))];
  if (kind === "region") {
    return { tag: REGION_TAG, truth: frame.truths[index] ?? null, prediction: null, iou: null, weight: 0 };
  }
  const match = kind === "label" ? labelMatch(level, index) : level.matches.find((m) => m.prediction === index);
  if (!match) return null;
  return {
    tag: TAGS[match.outcome],
    truth: match.truth === null ? null : frame.truths[match.truth],
    prediction: match.prediction === null ? null : frame.predictions[match.prediction],
    iou: match.iou ?? null,
    weight: errorWeight(match.outcome, frame.weights),
  };
}

/** Detections of classes outside the mapping at or above the threshold: shown nowhere, scored never. */
export function unmappedAt(frame: FrameDetail, threshold: number): number {
  return frame.unmapped.filter((d) => d.confidence >= threshold).length;
}

/** "fog-night" → "clear-night": weather compared in the same light, so illumination isn't mistaken for weather. */
export function clearCounterpart(condition: string): string {
  return `clear-${condition.split("-")[1]}`;
}

export function sortFrames(frames: FrameScore[], column: FrameColumn, direction: SortDirection): FrameScore[] {
  const sign = direction === "ascending" ? 1 : -1;
  return [...frames].sort((a, b) => {
    const [x, y] = [a[column], b[column]];
    return sign * (typeof x === "string" ? x.localeCompare(y as string) : x - (y as number));
  });
}

// A label's own match: the hit, confusion or miss on it. (An ignore region can forgive many predictions.)
function labelMatch(level: FrameLevel, truth: number): IndexedMatch | undefined {
  return level.matches.find((m) => m.truth === truth && m.outcome !== "ignored");
}

function tone(outcome: Outcome): Tone {
  return outcome === "hit" ? "ok" : outcome === "ignored" ? "neutral" : "error";
}

// Hits and ignored predictions add nothing to the score.
function errorWeight(outcome: Outcome, weights: FrameDetail["weights"]): number {
  if (outcome === "miss") return weights.misses;
  if (outcome === "false_alarm") return weights.false_alarms;
  if (outcome === "class_confusion") return weights.class_confusions;
  return 0;
}
