import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { fetchBenchmarkFrame, type FrameDetail, type FrameScore } from "./api/client";
import { useBenchmarkResults } from "./BenchmarkResults";
import { rankFrames } from "./frameReview";

interface BenchmarkFrameState {
  /** The selected condition's frames, worst first, scored at the display threshold. */
  ranked: FrameScore[];
  /** The open frame: the one picked in this condition, else its worst. */
  frameId: string | null;
  openFrame: (frameId: string) => void;
  /** The open frame matched at every threshold, so the viewer never asks again when the threshold moves. */
  frame: FrameDetail | null;
  error: string | null;
  /** The selected overlay's key (see frameReview's OverlayItem), or null. */
  selectedKey: string | null;
  selectOverlay: (key: string | null) => void;
}

const BenchmarkFrameContext = createContext<BenchmarkFrameState | null>(null);

/**
 * The open Benchmark frame and the selected overlay, shared by the explorer, viewer, frame table and inspector.
 * Kept above the workbench: the inspector is rebuilt when its drawer opens or the window crosses 1280 px.
 */
export function BenchmarkFrameProvider({ children }: { children: ReactNode }) {
  const { results, selected } = useBenchmarkResults();
  const [picked, setPicked] = useState<string | null>(null);
  const [frame, setFrame] = useState<FrameDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedKey, selectOverlay] = useState<string | null>(null);

  const ranked = rankFrames(selected?.frame_scores ?? []);
  const frameId = ranked.some((f) => f.id === picked) ? picked : (ranked[0]?.id ?? null);
  const experimentId = results?.id ?? null;

  // Pin the worst frame once it opens, so a new threshold that reorders the ranking doesn't swap the frame.
  useEffect(() => {
    if (frameId) setPicked(frameId);
  }, [frameId]);

  useEffect(() => {
    selectOverlay(null);
    setFrame(null);
    setError(null);
    if (!experimentId || !frameId) return;
    const controller = new AbortController();
    fetchBenchmarkFrame(experimentId, frameId, controller.signal)
      .then(setFrame)
      .catch((e) => {
        if (!controller.signal.aborted) setError(`Could not load frame ${frameId}: ${(e as Error).message}`);
      });
    return () => controller.abort();
  }, [experimentId, frameId]);

  return (
    <BenchmarkFrameContext.Provider
      value={{ ranked, frameId, openFrame: setPicked, frame, error, selectedKey, selectOverlay }}
    >
      {children}
    </BenchmarkFrameContext.Provider>
  );
}

export function useBenchmarkFrame(): BenchmarkFrameState {
  const value = useContext(BenchmarkFrameContext);
  if (!value) throw new Error("useBenchmarkFrame needs a BenchmarkFrameProvider");
  return value;
}
