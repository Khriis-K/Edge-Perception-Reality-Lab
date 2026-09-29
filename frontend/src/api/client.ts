import type { components } from "./schema";

export type HealthResponse = components["schemas"]["HealthResponse"];
export type SampleVideo = components["schemas"]["SampleVideo"];
export type Job = components["schemas"]["JobResponse"];
export type Experiment = components["schemas"]["Experiment"];

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

export function fetchSamples(): Promise<SampleVideo[]> {
  return request("/api/samples");
}

export function startRun(sampleId: string): Promise<Job> {
  return request("/api/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sample_id: sampleId }),
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

export function frameImageUrl(experimentId: string, frameIndex: number): string {
  return `${API_BASE}/api/experiments/${encodeURIComponent(experimentId)}/frames/${frameIndex}`;
}
