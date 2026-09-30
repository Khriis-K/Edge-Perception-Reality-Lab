import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { fetchExperiment, fetchStability, type Experiment, type StabilityReport } from "./api/client";
import { useCurrentJob } from "./CurrentJob";

interface Results {
  experiment: Experiment;
  stability: StabilityReport;
}

interface SyntheticResultsState {
  results: Results | null;
  error: string | null;
  /** The experiment on screen: the latest run's once it completes, or one picked from the run history. */
  openId: string | null;
  /** Open a cached run without running anything. */
  openExperiment: (experimentId: string) => void;
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
  const jobId = job?.id ?? null;
  const completedId = job?.status === "completed" ? job.experiment_id : null;
  const [openId, setOpenId] = useState<string | null>(null);
  const [results, setResults] = useState<Results | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Tagged with its experiment, so a new run starts on its first frame.
  const [frame, setFrame] = useState({ experimentId: "", index: 0 });

  // A new run replaces whatever was open, and its results open once it completes.
  useEffect(() => {
    if (jobId) setOpenId(completedId);
  }, [jobId, completedId]);

  useEffect(() => {
    setResults(null);
    setError(null);
    if (!openId) return;
    let cancelled = false;
    Promise.all([fetchExperiment(openId), fetchStability(openId)])
      .then(([experiment, stability]) => !cancelled && setResults({ experiment, stability }))
      .catch((e) => !cancelled && setError(`Could not load the results: ${(e as Error).message}`));
    return () => {
      cancelled = true;
    };
  }, [openId]);

  const experimentId = results?.experiment.id ?? "";
  const frameIndex = frame.experimentId === experimentId ? frame.index : 0;
  const setFrameIndex = useCallback((index: number) => setFrame({ experimentId, index }), [experimentId]);

  return (
    <SyntheticResultsContext.Provider
      value={{ results, error, openId, openExperiment: setOpenId, frameIndex, setFrameIndex }}
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
