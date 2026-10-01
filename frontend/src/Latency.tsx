import type { ReactNode } from "react";
import type { LatencySummary, ModelInfo, StageLatency } from "./api/client";
import { formatMs, modelLine } from "./latencyFormat";
import { Metric } from "./Stability";
import { useSyntheticResults } from "./SyntheticResults";

/** The inspector's latency section: what ran the model, and how long each stage took on this machine. */
export function LatencyInspector() {
  const { results } = useSyntheticResults();
  if (!results) return null;

  const { model, latency } = results.experiment;
  return <LatencySection model={model} latency={latency ?? null} readNote="to decode a frame" />;
}

/** What ran the model and each stage's time; shared by Synthetic and Findings. `readNote` says what "Read" timed. */
export function LatencySection({
  model,
  latency,
  readNote,
}: {
  model: ModelInfo;
  latency: LatencySummary | null;
  readNote: string;
}) {
  return (
    <section aria-label="Latency" className="latency-inspector">
      <h3 className="inspector-heading">Latency</h3>
      <p className="field-note">{modelLine(model)}</p>
      {latency ? (
        <LatencyMetrics latency={latency} provider={model.provider ?? model.runtime} readNote={readNote} />
      ) : (
        <p className="field-note">Not recorded: this run is too short to measure after the warm-up, or was cached before latency was measured.</p>
      )}
    </section>
  );
}

function LatencyMetrics({ latency, provider, readNote }: { latency: LatencySummary; provider: string; readNote: string }) {
  const { inference, processing, read, degrade, render } = latency;
  const fps = latency.effective_fps;
  return (
    <>
      <p className="field-note">
        Measured on this machine with {provider}. Timing for comparison between runs, not a real-time claim for other
        hardware.
      </p>
      <dl className="metrics" aria-label="Latency by stage">
        <StageMetric name="Inference" stage={inference}>
          over {latency.inference_runs} model calls
        </StageMetric>
        <Metric name="Effective fps" value={fps === null ? "—" : fps.toFixed(1)}>
          reading and detecting one stream, at the medians
        </Metric>
        <StageMetric name="Pre/post-processing" stage={processing} />
        <StageMetric name="Read" stage={read}>
          {readNote}
        </StageMetric>
        {/* A Benchmark run degrades and renders nothing: those stages are left out, never shown as 0 ms. */}
        {degrade && <StageMetric name="Degrade" stage={degrade} />}
        {render && (
          <StageMetric name="Render" stage={render}>
            to write both frames
          </StageMetric>
        )}
      </dl>
      <p className="field-note">
        Over {latency.frames} frames; the first {latency.warmup_frames} were warm-up and are left out.
      </p>
    </>
  );
}

function StageMetric({ name, stage, children }: { name: string; stage: StageLatency; children?: ReactNode }) {
  return (
    <Metric name={name} value={`${formatMs(stage.p50_ms)} p50`}>
      p90 {formatMs(stage.p90_ms)} {children}
    </Metric>
  );
}
