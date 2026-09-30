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
  /** The frame the viewer, match table and inspector all show. */
  frameIndex: number;
  setFrameIndex: (index: number) => void;
}

const SyntheticResultsContext = createContext<SyntheticResultsState | null>(null);

/**
 * The completed run's results and the current frame. Shared by the frame viewer, the dock's match
 * table and the inspector, which live in different parts of the workbench.
 */
export function SyntheticResultsProvider({ children }: { children: ReactNode }) {
  const { job } = useCurrentJob();
  const completedId = job?.status === "completed" ? job.experiment_id : null;
  const [results, setResults] = useState<Results | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Tagged with its experiment, so a new run starts on its first frame.
  const [frame, setFrame] = useState({ experimentId: "", index: 0 });

  useEffect(() => {
    setResults(null);
    setError(null);
    if (!completedId) return;
    let cancelled = false;
    Promise.all([fetchExperiment(completedId), fetchStability(completedId)])
      .then(([experiment, stability]) => !cancelled && setResults({ experiment, stability }))
      .catch((e) => !cancelled && setError(`Could not load the results: ${(e as Error).message}`));
    return () => {
      cancelled = true;
    };
  }, [completedId]);

  const experimentId = results?.experiment.id ?? "";
  const frameIndex = frame.experimentId === experimentId ? frame.index : 0;
  const setFrameIndex = useCallback((index: number) => setFrame({ experimentId, index }), [experimentId]);

  return (
    <SyntheticResultsContext.Provider value={{ results, error, frameIndex, setFrameIndex }}>
      {children}
    </SyntheticResultsContext.Provider>
  );
}

export function useSyntheticResults(): SyntheticResultsState {
  const value = useContext(SyntheticResultsContext);
  if (!value) throw new Error("useSyntheticResults needs a SyntheticResultsProvider");
  return value;
}
