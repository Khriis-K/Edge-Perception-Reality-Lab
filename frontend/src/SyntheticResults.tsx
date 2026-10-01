import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import {
  fetchExperiment,
  fetchStability,
  fetchSyntheticFramesResults,
  type Experiment,
  type ExperimentSummary,
  type StabilityReport,
  type SyntheticFramesResults,
} from "./api/client";
import { useCurrentJob } from "./CurrentJob";

// Precision and recall on dataset frames start at this confidence, as in the frame viewer and Benchmark.
const DEFAULT_FRAMES_THRESHOLD = 0.25;

interface Results {
  experiment: Experiment;
  stability: StabilityReport;
}

type Input = ExperimentSummary["input"];

interface SyntheticResultsState {
  /** A video run's results; null while a run on dataset frames is open. */
  results: Results | null;
  /** A run on dataset frames: stability and both variants' accuracy. It has no frame images. */
  framesResults: SyntheticFramesResults | null;
  /** Precision and recall on dataset frames are counted at this confidence; the server re-scores, never re-runs. */
  framesThreshold: number;
  setFramesThreshold: (threshold: number) => void;
  error: string | null;
  /** The experiment on screen: the latest run's once it completes, or one picked from the run history. */
  openId: string | null;
  /** Open a cached run without running anything. */
  openExperiment: (experimentId: string, input: Input) => void;
  /** The frame the viewer, match table and inspector all show. */
  frameIndex: number;
  setFrameIndex: (index: number) => void;
}

const SyntheticResultsContext = createContext<SyntheticResultsState | null>(null);

/**
 * The open experiment's results and the current frame. Shared by the frame viewer, the dock's match
 * table and the inspector, which live in different parts of the workbench.
 */
export function SyntheticResultsProvider({ children }: { children: ReactNode }) {
  const { job } = useCurrentJob();
  const input: Input | null = job?.mode === "synthetic" ? "video" : job?.mode === "synthetic-frames" ? "dataset" : null;
  const jobId = input ? job!.id : null;
  const completedId = input && job!.status === "completed" ? job!.experiment_id : null;
  const [open, setOpen] = useState<{ id: string; input: Input } | null>(null);
  const [results, setResults] = useState<Results | null>(null);
  const [framesResults, setFramesResults] = useState<SyntheticFramesResults | null>(null);
  const [framesThreshold, setFramesThreshold] = useState(DEFAULT_FRAMES_THRESHOLD);
  const [error, setError] = useState<string | null>(null);
  // Tagged with its experiment, so a new run starts on its first frame.
  const [frame, setFrame] = useState({ experimentId: "", index: 0 });

  // A new run replaces whatever was open, and its results open once it completes.
  useEffect(() => {
    if (jobId) setOpen(completedId ? { id: completedId, input: input! } : null);
  }, [jobId, completedId, input]);

  useEffect(() => {
    setResults(null);
    setFramesResults(null);
    setError(null);
  }, [open]);

  useEffect(() => {
    if (open?.input !== "video") return;
    const controller = new AbortController();
    Promise.all([fetchExperiment(open.id), fetchStability(open.id)])
      .then(([experiment, stability]) => !controller.signal.aborted && setResults({ experiment, stability }))
      .catch((e) => !controller.signal.aborted && setError(`Could not load the results: ${(e as Error).message}`));
    return () => controller.abort();
  }, [open]);

  // Results already on screen stay while a new threshold is scored, as in Benchmark.
  useEffect(() => {
    if (open?.input !== "dataset") return;
    const controller = new AbortController();
    fetchSyntheticFramesResults(open.id, framesThreshold, controller.signal)
      .then((body) => {
        setFramesResults(body);
        setError(null);
      })
      .catch((e) => !controller.signal.aborted && setError(`Could not load the results: ${(e as Error).message}`));
    return () => controller.abort();
  }, [open, framesThreshold]);

  const openExperiment = useCallback((id: string, input: Input) => setOpen({ id, input }), []);
  const experimentId = results?.experiment.id ?? "";
  const frameIndex = frame.experimentId === experimentId ? frame.index : 0;
  const setFrameIndex = useCallback((index: number) => setFrame({ experimentId, index }), [experimentId]);

  return (
    <SyntheticResultsContext.Provider
      value={{
        results,
        framesResults,
        framesThreshold,
        setFramesThreshold,
        error,
        openId: open?.id ?? null,
        openExperiment,
        frameIndex,
        setFrameIndex,
      }}
    >
      {children}
    </SyntheticResultsContext.Provider>
  );
}

export function useSyntheticResults(): SyntheticResultsState {
  const value = useContext(SyntheticResultsContext);
  if (!value) throw new Error("useSyntheticResults needs a SyntheticResultsProvider");
  return value;
}
