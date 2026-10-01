import type { SyntheticFramesResults } from "./api/client";
import { ClassTable } from "./Benchmark";
import { conditionName } from "./benchmarkFormat";
import { StabilityMetrics } from "./Stability";
import { useSyntheticResults } from "./SyntheticResults";
import { ThresholdField } from "./ThresholdField";

/**
 * A Synthetic run on the subset's clear frames. The frames are labelled, so it has both metric sets: stability against
 * the clean detections, and accuracy against the ground truth for the clean and the degraded frames, scored as in
 * Benchmark mode.
 */
export function SyntheticFramesView({ results }: { results: SyntheticFramesResults }) {
  const { stability, clean, degraded, degradation } = results;
  const { framesThreshold, setFramesThreshold } = useSyntheticResults();
  const frames = `${conditionName(results.condition)} frames`;
  return (
    <section aria-label="Results on dataset frames" className="synthetic-frames">
      <p>
        {results.title} on {frames} ({clean.frames} {clean.frames === 1 ? "frame" : "frames"}), seed {degradation.seed}.{" "}
        {results.model.name} {results.model.version}.
      </p>

      <h2>Stability vs. the clean baseline</h2>
      <p className="field-note">How much the degraded detections differ from the clean ones on the same frames.</p>
      <StabilityMetrics stability={stability} label="Stability" />
      <p className="field-note">
        <span className="low-n">low n</span>: counted over fewer than {stability.low_n_objects} detections (or retained
        pairs), too few to trust.
      </p>

      <h2>Accuracy vs. the ground truth</h2>
      <p className="field-note">
        Scored as in Benchmark mode, at IoU ≥ {results.iou_threshold.toFixed(2)}. The clean side is the Benchmark's own{" "}
        {conditionName(results.condition)} condition on these frames.
      </p>
      <ThresholdField threshold={framesThreshold} onChange={setFramesThreshold} />
      <ClassTable
        title={`Clean ${frames}`}
        condition={clean}
        threshold={results.display_threshold}
        lowN={results.low_n_objects}
      />
      <ClassTable
        title={`${results.title} on ${frames}`}
        condition={degraded}
        threshold={results.display_threshold}
        lowN={results.low_n_objects}
      />
    </section>
  );
}
