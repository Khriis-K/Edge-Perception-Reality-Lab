import type { ExportSummary, Findings } from "./api/client";
import { formatBytes } from "./runHistoryFormat";

/** What every report holds whatever the user picks (backend/report_html.py), in the order the report has it. */
export function alwaysIncluded(kind: Findings["kind"]): string[] {
  return [
    kind === "benchmark" ? "Subset manifest" : "Input fingerprint",
    "Model and runtime versions",
    "Class mapping and ignore-region rule",
    "Degradation settings",
    "Metric definitions with sample sizes",
    kind === "benchmark" ? "Worst frames, by frame id" : "Worst frames, by frame number",
    "Limitations",
    "Citation: Bijelic et al., CVPR 2020",
  ];
}

/** A file's size on disk: the server writes UTF-8. */
export function byteSize(text: string): number {
  return new TextEncoder().encode(text).length;
}

/** One line under an export's title in the explorer. */
export function exportMeta(summary: ExportSummary): string {
  const total = summary.files.reduce((sum, file) => sum + file.size_bytes, 0);
  const count = `${summary.files.length} ${summary.files.length === 1 ? "file" : "files"}`;
  const threshold = summary.display_threshold === null ? [] : [`threshold ${summary.display_threshold.toFixed(2)}`];
  return [...threshold, count, formatBytes(total)].join(" · ");
}
