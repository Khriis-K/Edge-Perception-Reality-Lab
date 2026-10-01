import type { FrameReliability, FrameScore, HeatmapCell } from "./api/client";
import { formatMetric } from "./benchmarkFormat";

/**
 * Why a Benchmark frame ranks among the worst, in one line: its largest contribution to the error score. Every
 * weight is 1, so that is its largest count; ties go to misses, then false alarms, the order the score lists them.
 */
export function worstReason(frame: FrameScore): string {
  const largest = Math.max(frame.misses, frame.false_alarms, frame.class_confusions);
  if (frame.misses === largest) {
    const objects = frame.hits + frame.misses + frame.class_confusions;
    return `Missed ${frame.misses} of ${objects} labelled ${plural(objects, "object", "objects")}`;
  }
  if (frame.false_alarms === largest) {
    const one = frame.false_alarms === 1;
    return `${frame.false_alarms} ${one ? "detection" : "detections"} where nothing is labelled (${one ? "a false alarm" : "false alarms"})`;
  }
  return `${frame.class_confusions} ${plural(frame.class_confusions, "object", "objects")} found but given the wrong class`;
}

/** Why a video frame ranks among the least stable: its largest contribution to the stability score. */
export function reliabilityReason(point: FrameReliability): string {
  const largest = Math.max(point.dropped, point.introduced, point.class_changes, point.confidence_loss);
  const detections = (count: number) => `${count} ${plural(count, "detection", "detections")}`;
  if (point.dropped === largest) {
    return `${point.dropped} clean ${plural(point.dropped, "detection", "detections")} lost under the degradation`;
  }
  if (point.introduced === largest) return `${detections(point.introduced)} appeared that the clean frame lacks`;
  if (point.class_changes === largest) return `${detections(point.class_changes)} changed class`;
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
