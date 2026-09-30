import type { components } from "./schema";

export type HealthResponse = components["schemas"]["HealthResponse"];
export type SampleVideo = components["schemas"]["SampleVideo"];
export type Job = components["schemas"]["JobResponse"];
export type Experiment = components["schemas"]["Experiment"];
export type ModelInfo = components["schemas"]["ModelInfo"];
export type LatencySummary = components["schemas"]["LatencySummary"];
export type StageLatency = components["schemas"]["StageLatency"];
export type ExperimentSummary = components["schemas"]["ExperimentSummary"];
export type RunPreview = components["schemas"]["RunPreview"];
export type CacheInfo = components["schemas"]["CacheInfo"];
export type StabilityReport = components["schemas"]["StabilityReport"];
export type FrameStability = components["schemas"]["FrameStability"];
export type Match = components["schemas"]["Match"];
export type Degradation = components["schemas"]["Degradation"];
export type DegradationSettings = components["schemas"]["DegradationSettings"];
export type DegradationKind = DegradationSettings["kind"];
// A path parameter, which the generated schema doesn't name as a type. Mirrors backend/jobs.py.
export type FrameVariant = "clean" | "degraded";
export type DatasetStatus = components["schemas"]["DatasetStatusResponse"];
export type DatasetPartStatus = components["schemas"]["DatasetPartStatus"];
export type Subset = components["schemas"]["SubsetResponse"];
export type ConditionSummary = components["schemas"]["ConditionSummary"];
export type Manifest = components["schemas"]["Manifest"];

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

/** The seeded per-condition subset of the dataset: its manifest and the Subset table's counts. Without a
 * seed and cap, the server uses its defaults, and the manifest says which. */
export function fetchSubset(choice: { seed: number; cap: number } | null, signal: AbortSignal): Promise<Subset> {
  const query = choice ? `?seed=${choice.seed}&cap=${choice.cap}` : "";
  return request(`/api/dataset/subset${query}`, { signal });
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

const runRequest = (sampleId: string, degradation: DegradationSettings): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ sample_id: sampleId, degradation }),
});

/** Starts a job, or, if identical settings already ran, returns a completed job with `cached` set. */
export function startRun(sampleId: string, degradation: DegradationSettings): Promise<Job> {
  return request("/api/jobs", runRequest(sampleId, degradation));
}

/** Whether starting this run would reuse cached results or start a new job. Starts nothing. */
export function previewRun(sampleId: string, degradation: DegradationSettings, signal: AbortSignal): Promise<RunPreview> {
  return request("/api/jobs/preview", { ...runRequest(sampleId, degradation), signal });
}

/** Every cached run, newest first. */
export function fetchExperiments(signal: AbortSignal): Promise<ExperimentSummary[]> {
  return request("/api/experiments", { signal });
}

/** The cache folder and its size, so it can be found and deleted. */
export function fetchCacheInfo(signal: AbortSignal): Promise<CacheInfo> {
  return request("/api/cache", { signal });
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

/** How much the degraded detections differ from the clean ones: stability, not accuracy. */
export function fetchStability(experimentId: string): Promise<StabilityReport> {
  return request(`/api/experiments/${encodeURIComponent(experimentId)}/stability`);
}

export function frameImageUrl(experimentId: string, variant: FrameVariant, frameIndex: number): string {
  return `${API_BASE}/api/experiments/${encodeURIComponent(experimentId)}/frames/${variant}/${frameIndex}`;
}
