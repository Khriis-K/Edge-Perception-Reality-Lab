import type { ModelInfo } from "./api/client";
import { formatBytes } from "./runHistoryFormat";

/** Name, size, runtime and execution provider, leaving out whatever the runner doesn't have. */
export function modelLine(model: ModelInfo): string {
  const size = model.size_bytes == null ? null : formatBytes(model.size_bytes);
  return [model.name, size, model.runtime, model.provider].filter(Boolean).join(" · ");
}

export function formatMs(ms: number): string {
  return ms >= 100 ? `${Math.round(ms)} ms` : `${ms.toFixed(1)} ms`;
}
