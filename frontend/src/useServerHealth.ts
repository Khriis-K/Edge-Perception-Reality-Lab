import { useEffect, useState } from "react";
import { fetchHealth } from "./api/client";

export type ServerHealth = "checking" | "connected" | "disconnected";

const POLL_MS = 5000;
const TIMEOUT_MS = 3000;

/** Polls the backend health endpoint; any failure or timeout reads as disconnected. */
export function useServerHealth(): ServerHealth {
  const [health, setHealth] = useState<ServerHealth>("checking");

  useEffect(() => {
    let cancelled = false;

    async function check() {
      try {
        await fetchHealth(AbortSignal.timeout(TIMEOUT_MS));
        if (!cancelled) setHealth("connected");
      } catch {
        if (!cancelled) setHealth("disconnected");
      }
    }

    check();
    const timer = setInterval(check, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  return health;
}
