import type { BenchmarkFindings, FrameReliability, FrameScore, HeatmapCell, VideoFindings } from "./api/client";
import { formatMetric } from "./benchmarkFormat";

type BenchmarkWeights = BenchmarkFindings["record"]["weights"];
type StabilityWeights = VideoFindings["record"]["weights"];

/**
 * Why a Benchmark frame ranks among the worst, in one line: its largest weighted contribution to the error score.
 * Ties go to misses, then false alarms, the order the score lists them.
 */
export function worstReason(frame: FrameScore, weights: BenchmarkWeights): string {
  const [misses, falseAlarms, confusions] = [
    frame.misses * weights.misses,
    frame.false_alarms * weights.false_alarms,
    frame.class_confusions * weights.class_confusions,
  ];
  const largest = Math.max(misses, falseAlarms, confusions);
  if (misses === largest) {
    const objects = frame.hits + frame.misses + frame.class_confusions;
    return `Missed ${frame.misses} of ${objects} labelled ${plural(objects, "object", "objects")}`;
  }
  if (falseAlarms === largest) {
    const one = frame.false_alarms === 1;
    return `${frame.false_alarms} ${one ? "detection" : "detections"} where nothing is labelled (${one ? "a false alarm" : "false alarms"})`;
  }
  return `${frame.class_confusions} ${plural(frame.class_confusions, "object", "objects")} found but given the wrong class`;
}

/** Why a video frame ranks among the least stable: its largest weighted contribution to the stability score. */
export function reliabilityReason(point: FrameReliability, weights: StabilityWeights): string {
  const [dropped, introduced, classChanges, confidenceLoss] = [
    point.dropped * weights.dropped,
    point.introduced * weights.introduced,
    point.class_changes * weights.class_changes,
    point.confidence_loss * weights.confidence_loss,
  ];
  const largest = Math.max(dropped, introduced, classChanges, confidenceLoss);
  const detections = (count: number) => `${count} ${plural(count, "detection", "detections")}`;
  if (dropped === largest) {
    return `${point.dropped} clean ${plural(point.dropped, "detection", "detections")} lost under the degradation`;
  }
  if (introduced === largest) return `${detections(point.introduced)} appeared that the clean frame lacks`;
  if (classChanges === largest) return `${detections(point.class_changes)} changed class`;
  return `Matched detections lost ${point.confidence_loss.toFixed(2)} confidence in total`;
}

/** "0.50", "0.50*" when low n (the legend explains the star), or a dash when the class has no objects. */
export function heatmapCellText(cell: HeatmapCell): string {
  if (cell.ap === null) return formatMetric(null);
  return `${formatMetric(cell.ap)}${cell.low_n ? "*" : ""}`;
}

function plural(count: number, one: string, many: string): string {
  return count === 1 ? one : many;
}

/**
 * Black or white text for a fill given as "rgb(r, g, b)" (what a d3 color scale returns): whichever contrasts more,
 * by WCAG relative luminance. Past luminance 0.179 black wins, and either way the contrast is at least 4.5:1.
 */
export function textColorOn(fill: string): "#000000" | "#ffffff" {
  const [r, g, b] = (fill.match(/\d+(\.\d+)?/g) ?? []).slice(0, 3).map((v) => linear(Number(v) / 255));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b > 0.179 ? "#000000" : "#ffffff";
}

function linear(channel: number): number {
  return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
}
