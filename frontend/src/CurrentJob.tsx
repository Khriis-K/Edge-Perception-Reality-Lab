import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import {
  cancelJob,
  fetchJob,
  JobNotFound,
  startBenchmark as requestBenchmark,
  startRun,
  type DegradationSettings,
  type Job,
  type Manifest,
} from "./api/client";

const POLL_MS = 250;

export const isActive = (job: Job | null): job is Job => job?.status === "queued" || job?.status === "running";

/** The job's id once it has completed, else null: a dependency that changes exactly when a run finishes. */
export const completedJobId = (job: Job | null): string | null => (job?.status === "completed" ? job.id : null);

interface CurrentJob {
  job: Job | null;
  /** Why starting or polling failed, in plain language. */
  error: string | null;
  start: (sampleId: string, degradation: DegradationSettings) => Promise<void>;
  startBenchmark: (manifest: Manifest) => Promise<void>;
  cancel: () => Promise<void>;
}

const CurrentJobContext = createContext<CurrentJob | null>(null);

/** The job this browser started most recently, polled while it runs. Shared by the top-bar pill and the run screen. */
export function CurrentJobProvider({ children }: { children: ReactNode }) {
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const activeId = isActive(job) ? job.id : null;

  useEffect(() => {
    if (!activeId) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;

    // Each poll waits for the previous answer, so a slow response can never overwrite a newer one.
    async function poll() {
      try {
        const latest = await fetchJob(activeId!);
        if (cancelled) return;
        setJob(latest);
        setError(null);
      } catch (e) {
        if (cancelled) return;
        if (e instanceof JobNotFound) {
          // The server no longer knows the job (it restarted): stop polling and say so.
          setJob(null);
          setError("The server lost track of the run, probably because it restarted. Start it again.");
          return;
        }
        setError(`Can't reach the server to check the run: ${(e as Error).message}`);
      }
      timer = setTimeout(poll, POLL_MS);
    }

    timer = setTimeout(poll, POLL_MS);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [activeId]);

  // Synthetic and Benchmark runs are tracked, polled and cancelled the same way.
  const track = useCallback(async (begin: () => Promise<Job>) => {
    setError(null);
    try {
      setJob(await begin());
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);
  const start = useCallback(
    (sampleId: string, degradation: DegradationSettings) => track(() => startRun(sampleId, degradation)),
    [track],
  );
  const startBenchmark = useCallback((manifest: Manifest) => track(() => requestBenchmark(manifest)), [track]);

  const cancel = useCallback(async () => {
    if (!activeId) return;
    try {
      setJob(await cancelJob(activeId));
    } catch (e) {
      setError((e as Error).message);
    }
  }, [activeId]);

  return (
    <CurrentJobContext.Provider value={{ job, error, start, startBenchmark, cancel }}>
      {children}
    </CurrentJobContext.Provider>
  );
}

export function useCurrentJob(): CurrentJob {
  const value = useContext(CurrentJobContext);
  if (!value) throw new Error("useCurrentJob needs a CurrentJobProvider");
  return value;
}
