import type { components } from "./schema";

export type HealthResponse = components["schemas"]["HealthResponse"];
export type DatasetStatus = components["schemas"]["DatasetStatusResponse"];
export type DatasetPartStatus = components["schemas"]["DatasetPartStatus"];

// Empty in production: the backend serves this page, so the API is same-origin.
const API_BASE: string = import.meta.env.VITE_API_BASE ?? "";

/** host:port of the backend this page talks to, for the server-status pill. */
export const apiHost = API_BASE ? new URL(API_BASE).host : window.location.host;

export async function fetchHealth(signal: AbortSignal): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE}/api/health`, { signal });
  if (!response.ok) throw new Error(`Health check failed: HTTP ${response.status}`);
  return response.json();
}

/** Re-checks the dataset folder the backend was started with. The browser never sends a path. */
export async function fetchDatasetStatus(signal: AbortSignal): Promise<DatasetStatus> {
  const response = await fetch(`${API_BASE}/api/dataset/status`, { signal });
  if (!response.ok) throw new Error(`Dataset check failed: HTTP ${response.status}`);
  return response.json();
}
