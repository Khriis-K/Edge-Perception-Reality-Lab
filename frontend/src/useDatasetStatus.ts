import { useCallback, useEffect, useRef, useState } from "react";
import { fetchDatasetStatus, type DatasetStatus } from "./api/client";

export interface DatasetCheck {
  status: DatasetStatus | null;
  error: string | null;
  checking: boolean;
  recheck: () => void;
}

/** Checks the dataset once on mount; recheck() runs the backend's readiness check again. */
export function useDatasetStatus(): DatasetCheck {
  const [status, setStatus] = useState<DatasetStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [checking, setChecking] = useState(true);
  const inFlight = useRef<AbortController | null>(null);

  const recheck = useCallback(async () => {
    inFlight.current?.abort();
    const controller = new AbortController();
    inFlight.current = controller;
    setChecking(true);
    try {
      setStatus(await fetchDatasetStatus(controller.signal));
      setError(null);
    } catch (reason) {
      if (controller.signal.aborted) return;
      setError(reason instanceof Error ? reason.message : String(reason));
    }
    setChecking(false);
  }, []);

  useEffect(() => {
    recheck();
    return () => inFlight.current?.abort();
  }, [recheck]);

  return { status, error, checking, recheck };
}
