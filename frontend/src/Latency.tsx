import type { LatencySummary } from "./api/client";
import { formatMs, modelLine } from "./latencyFormat";
import { Metric } from "./Stability";
import { useSyntheticResults } from "./SyntheticResults";

/** The inspector's latency section: what ran the model, and how long each stage took on this machine. */
export function LatencyInspector() {
  const { results } = useSyntheticResults();
  if (!results) return null;

  const { model, latency } = results.experiment;
  return (
    <section aria-label="Latency" className="latency-inspector">
      <h3 className="inspector-heading">Latency</h3>
      <p className="field-note">{modelLine(model)}</p>
      {latency ? (
        <LatencyMetrics latency={latency} provider={model.provider ?? model.runtime} />
      ) : (
        <p className="field-note">Not recorded: this run is too short to measure after the warm-up, or was cached before latency was measured.</p>
      )}
    </section>
  );
}

function LatencyMetrics({ latency, provider }: { latency: LatencySummary; provider: string }) {
  const { inference, processing, read, degrade, render } = latency;
  const fps = latency.effective_fps;
  return (
    <>
      <p className="field-note">
        Measured on this machine with {provider}. Timing for comparison between runs, not a real-time claim for other
        hardware.
      </p>
      <dl className="metrics" aria-label="Latency">
        <Metric name="Inference" value={`${formatMs(inference.p50_ms)} p50`}>
          p90 {formatMs(inference.p90_ms)} over {latency.inference_runs} model calls
        </Metric>
        <Metric name="Effective fps" value={fps === null ? "—" : fps.toFixed(1)}>
          reading and detecting one stream, at the medians
        </Metric>
        <Metric name="Pre/post-processing" value={`${formatMs(processing.p50_ms)} p50`}>
          p90 {formatMs(processing.p90_ms)}
        </Metric>
        <Metric name="Read" value={`${formatMs(read.p50_ms)} p50`}>
          p90 {formatMs(read.p90_ms)} to decode a frame
        </Metric>
        <Metric name="Degrade" value={`${formatMs(degrade.p50_ms)} p50`}>
          p90 {formatMs(degrade.p90_ms)}
        </Metric>
        <Metric name="Render" value={`${formatMs(render.p50_ms)} p50`}>
          p90 {formatMs(render.p90_ms)} to write both frames
        </Metric>
      </dl>
      <p className="field-note">
        Over {latency.frames} frames; the first {latency.warmup_frames} were warm-up and are left out.
      </p>
    </>
  );
}
