import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import {
  fetchFindings,
  fetchFindingsRuns,
  saveHeadline as requestSaveHeadline,
  type FindingKey,
  type Findings,
  type FindingsRun,
} from "./api/client";
import { useBenchmarkResults } from "./BenchmarkResults";
import { completedJobId, useCurrentJob } from "./CurrentJob";

interface FindingsState {
  /** Benchmark runs and Synthetic runs on video, newest first; null until listed. */
  runs: FindingsRun[] | null;
  /** The run on screen: the one picked, else the newest. */
  openId: string | null;
  open: (experimentId: string) => void;
  findings: Findings | null;
  error: string | null;
  /** Stores the user's headline with the run; rejects with the server's reason if it is refused. */
  saveHeadline: (key: FindingKey, text: string) => Promise<void>;
}

const FindingsContext = createContext<FindingsState | null>(null);

/**
 * The open run's findings, shared by the outline, the document and the inspector. Read from the cache, so they are
 * there after a reload. Worst frames are scored at the Benchmark screen's display threshold.
 */
export function FindingsProvider({ children }: { children: ReactNode }) {
  const { job } = useCurrentJob();
  const { threshold } = useBenchmarkResults();
  const finishedJobId = completedJobId(job);
  const [runs, setRuns] = useState<FindingsRun[] | null>(null);
  const [picked, setPicked] = useState<string | null>(null);
  const [findings, setFindings] = useState<Findings | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Re-listed whenever a run finishes, since it may be a new one to open.
  useEffect(() => {
    const controller = new AbortController();
    fetchFindingsRuns(controller.signal)
      .then(setRuns)
      .catch((e) => !controller.signal.aborted && setError(`Could not list the runs: ${(e as Error).message}`));
    return () => controller.abort();
  }, [finishedJobId]);

  const openId = runs?.some((run) => run.id === picked) ? picked : (runs?.[0]?.id ?? null);

  useEffect(() => {
    setFindings(null);
  }, [openId]);

  // A synthetic run on the clear frames adds to sim-to-real, so the findings are re-read when one finishes too.
  useEffect(() => {
    if (!openId) return;
    const controller = new AbortController();
    fetchFindings(openId, threshold, controller.signal)
      .then((body) => {
        setFindings(body);
        setError(null);
      })
      .catch((e) => !controller.signal.aborted && setError(`Could not load the findings: ${(e as Error).message}`));
    return () => controller.abort();
  }, [openId, threshold, finishedJobId]);

  const saveHeadline = useCallback(
    async (key: FindingKey, text: string) => {
      if (!openId) return;
      const headlines = await requestSaveHeadline(openId, key, text);
      setFindings((current) => (current && current.id === openId ? { ...current, headlines } : current));
    },
    [openId],
  );

  return (
    <FindingsContext.Provider value={{ runs, openId, open: setPicked, findings, error, saveHeadline }}>
      {children}
    </FindingsContext.Provider>
  );
}

export function useFindings(): FindingsState {
  const value = useContext(FindingsContext);
  if (!value) throw new Error("useFindings needs a FindingsProvider");
  return value;
}
