import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { fetchBenchmarkResults, type BenchmarkResults, type ConditionResult } from "./api/client";
import { useCurrentJob } from "./CurrentJob";

const DEFAULT_THRESHOLD = 0.25; // as in the Synthetic frame viewer

interface BenchmarkResultsState {
  results: BenchmarkResults | null;
  error: string | null;
  /** Precision and recall are counted at this confidence; the server re-scores stored detections, never re-runs. */
  threshold: number;
  setThreshold: (threshold: number) => void;
  /** The condition the tree has selected: the first until the user picks one. */
  selected: ConditionResult | null;
  select: (condition: string) => void;
}

const BenchmarkResultsContext = createContext<BenchmarkResultsState | null>(null);

/** The latest Benchmark run's results, shared by the condition tree and the work area. */
export function BenchmarkResultsProvider({ children }: { children: ReactNode }) {
  const { job } = useCurrentJob();
  const benchmark = job?.mode === "benchmark" ? job : null;
  const jobId = benchmark?.id ?? null;
  const completedId = benchmark?.status === "completed" ? benchmark.experiment_id : null;
  const [openId, setOpenId] = useState<string | null>(null);
  const [threshold, setThreshold] = useState(DEFAULT_THRESHOLD);
  const [results, setResults] = useState<BenchmarkResults | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedName, select] = useState<string | null>(null);

  // A new run replaces whatever was open, and its results open once it completes.
  useEffect(() => {
    if (jobId) setOpenId(completedId);
  }, [jobId, completedId]);

  useEffect(() => {
    setResults(null);
    setError(null);
  }, [openId]);

  // Results already on screen stay while a new threshold is scored, so the tree doesn't flicker.
  useEffect(() => {
    if (!openId) return;
    const controller = new AbortController();
    fetchBenchmarkResults(openId, threshold, controller.signal)
      .then((body) => {
        setResults(body);
        setError(null);
      })
      .catch((e) => {
        if (!controller.signal.aborted) setError(`Could not load the benchmark results: ${(e as Error).message}`);
      });
    return () => controller.abort();
  }, [openId, threshold]);

  const conditions = results?.conditions ?? [];
  const selected = conditions.find((c) => c.condition === selectedName) ?? conditions[0] ?? null;

  return (
    <BenchmarkResultsContext.Provider value={{ results, error, threshold, setThreshold, selected, select }}>
      {children}
    </BenchmarkResultsContext.Provider>
  );
}

export function useBenchmarkResults(): BenchmarkResultsState {
  const value = useContext(BenchmarkResultsContext);
  if (!value) throw new Error("useBenchmarkResults needs a BenchmarkResultsProvider");
  return value;
}
