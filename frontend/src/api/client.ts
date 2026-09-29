import type { components } from "./schema";

export type HealthResponse = components["schemas"]["HealthResponse"];
export type SampleVideo = components["schemas"]["SampleVideo"];
export type Job = components["schemas"]["JobResponse"];
export type Experiment = components["schemas"]["Experiment"];
export type Degradation = components["schemas"]["Degradation"];
export type DegradationSettings = components["schemas"]["DegradationSettings"];
export type DegradationKind = DegradationSettings["kind"];
// A path parameter, which the generated schema doesn't name as a type. Mirrors backend/jobs.py.
export type FrameVariant = "clean" | "degraded";
export type DatasetStatus = components["schemas"]["DatasetStatusResponse"];
export type DatasetPartStatus = components["schemas"]["DatasetPartStatus"];

// Empty in production: the backend serves this page, so the API is same-origin.
const API_BASE: string = import.meta.env.VITE_API_BASE ?? "";

/** host:port of the backend this page talks to, for the server-status pill. */
export const apiHost = API_BASE ? new URL(API_BASE).host : window.location.host;

/** The API answered 404: the id it was asked about doesn't exist (any more). */
export class JobNotFound extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (response.status === 404 && path.startsWith("/api/jobs/")) throw new JobNotFound("No such job.");
  if (!response.ok) {
    // FastAPI puts a plain-language message in `detail` for the errors we raise.
    const body = await response.json().catch(() => null);
    const detail = typeof body?.detail === "string" ? body.detail : `HTTP ${response.status}`;
    throw new Error(detail);
  }
  return response.json();
}

export function fetchHealth(signal: AbortSignal): Promise<HealthResponse> {
  return request("/api/health", { signal });
}

/** Re-checks the dataset folder the backend was started with. The browser never sends a path. */
export function fetchDatasetStatus(signal: AbortSignal): Promise<DatasetStatus> {
  return request("/api/dataset/status", { signal });
}

export function fetchSamples(): Promise<SampleVideo[]> {
  return request("/api/samples");
}

export function fetchDegradations(): Promise<Degradation[]> {
  return request("/api/degradations");
}

/** The transform parameters a severity gives, as the server derives and records them. */
export function fetchDegradationParameters(
  kind: DegradationKind,
  severity: number,
  signal: AbortSignal,
): Promise<Record<string, number>> {
  return request(`/api/degradations/${kind}/parameters?severity=${severity}`, { signal });
}

export function startRun(sampleId: string, degradation: DegradationSettings): Promise<Job> {
  return request("/api/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sample_id: sampleId, degradation }),
  });
}

export function fetchJob(jobId: string): Promise<Job> {
  return request(`/api/jobs/${encodeURIComponent(jobId)}`);
}

export function cancelJob(jobId: string): Promise<Job> {
  return request(`/api/jobs/${encodeURIComponent(jobId)}/cancel`, { method: "POST" });
}

export function fetchExperiment(experimentId: string): Promise<Experiment> {
  return request(`/api/experiments/${encodeURIComponent(experimentId)}`);
}

export function frameImageUrl(experimentId: string, variant: FrameVariant, frameIndex: number): string {
  return `${API_BASE}/api/experiments/${encodeURIComponent(experimentId)}/frames/${variant}/${frameIndex}`;
}
