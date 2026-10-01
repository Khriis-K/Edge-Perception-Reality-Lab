import type { components, operations } from "./schema";

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
export type BenchmarkResults = components["schemas"]["BenchmarkResults"];
export type ConditionResult = components["schemas"]["ConditionResult"];
export type ClassMetrics = components["schemas"]["ClassMetrics"];
export type FrameScore = components["schemas"]["FrameScore"];
export type FrameDetail = components["schemas"]["FrameDetail"];
export type FrameLevel = components["schemas"]["FrameLevel"];
export type FrameTruth = components["schemas"]["FrameTruth"];
export type IndexedMatch = components["schemas"]["IndexedMatch"];
export type SyntheticConditionResult = components["schemas"]["SyntheticConditionResult"];
export type SyntheticFramesResults = components["schemas"]["SyntheticFramesResults"];
export type ClearCondition = SyntheticFramesResults["condition"];
export type ClassMapping = components["schemas"]["ClassMapping"];
export type FindingsRun = components["schemas"]["FindingsRun"];
export type BenchmarkFindings = components["schemas"]["BenchmarkFindings"];
export type VideoFindings = components["schemas"]["VideoFindings"];
export type Findings = BenchmarkFindings | VideoFindings;
// The numbered findings a headline can lead: the path parameter is the one place the schema names them.
export type FindingKey = operations["put_headline_api_findings__experiment_id__headlines__key__put"]["parameters"]["path"]["key"];
export type Headlines = Partial<Record<FindingKey, string>>;
export type SimToReal = components["schemas"]["SimToReal"];
export type Side = components["schemas"]["Side"];
export type Comparison = components["schemas"]["Comparison"];
export type ClassDrop = components["schemas"]["ClassDrop"];
export type HeatmapRow = components["schemas"]["HeatmapRow"];
export type HeatmapCell = components["schemas"]["HeatmapCell"];
export type WorstFrame = components["schemas"]["WorstFrame"];
export type FrameReliability = components["schemas"]["FrameReliability"];

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

/** Runs the detector over every frame of the manifest, or returns a completed job with `cached` set. The manifest
 * is sent as JSON, never as a path; the server refuses one it can't run, and says why. */
export function startBenchmark(manifest: Manifest): Promise<Job> {
  return request("/api/benchmark/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ manifest }),
  });
}

/** Per-condition and per-class AP, and precision and recall at the display threshold, scored from stored detections. */
export function fetchBenchmarkResults(
  experimentId: string,
  displayThreshold: number,
  signal: AbortSignal,
): Promise<BenchmarkResults> {
  const id = encodeURIComponent(experimentId);
  return request(`/api/benchmark/experiments/${id}?display_threshold=${displayThreshold}`, { signal });
}

/** One frame's predictions and labels, matched at every display threshold: the viewer never asks again. */
export function fetchBenchmarkFrame(experimentId: string, frameId: string, signal: AbortSignal): Promise<FrameDetail> {
  const id = encodeURIComponent(experimentId);
  return request(`/api/benchmark/experiments/${id}/frames/${encodeURIComponent(frameId)}`, { signal });
}

/** A dataset frame's camera image. Shown locally only; it never goes into a report by default. */
export function datasetFrameUrl(frameId: string): string {
  return `${API_BASE}/api/dataset/frames/${encodeURIComponent(frameId)}`;
}

/** Degrades the manifest's frames of one clear condition and runs the detector on both variants, or returns a
 * completed job with `cached` set. The server checks the manifest as for a Benchmark run. */
export function startSyntheticFrames(
  manifest: Manifest,
  condition: ClearCondition,
  degradation: DegradationSettings,
): Promise<Job> {
  return request("/api/synthetic-frames/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ manifest, condition, degradation }),
  });
}

/** Stability against the clean detections, and AP, precision and recall for both variants against the labels. */
export function fetchSyntheticFramesResults(
  experimentId: string,
  displayThreshold: number,
  signal: AbortSignal,
): Promise<SyntheticFramesResults> {
  const id = encodeURIComponent(experimentId);
  return request(`/api/synthetic-frames/experiments/${id}?display_threshold=${displayThreshold}`, { signal });
}

export function frameImageUrl(experimentId: string, variant: FrameVariant, frameIndex: number): string {
  return `${API_BASE}/api/experiments/${encodeURIComponent(experimentId)}/frames/${variant}/${frameIndex}`;
}

/** The runs Findings can open, newest first: Benchmark runs and Synthetic runs on video. */
export function fetchFindingsRuns(signal: AbortSignal): Promise<FindingsRun[]> {
  return request("/api/findings", { signal });
}

/** A run's findings, as chart data. A Benchmark run's worst frames are scored at the display threshold. */
export function fetchFindings(experimentId: string, displayThreshold: number, signal: AbortSignal): Promise<Findings> {
  const id = encodeURIComponent(experimentId);
  return request(`/api/findings/${id}?display_threshold=${displayThreshold}`, { signal });
}

/** Stores the headline the user wrote for one finding, with the run; blank text clears it. Returns them all. */
export function saveHeadline(experimentId: string, key: FindingKey, text: string): Promise<Headlines> {
  return request(`/api/findings/${encodeURIComponent(experimentId)}/headlines/${key}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
}
