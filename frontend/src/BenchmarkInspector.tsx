import type { ReactNode } from "react";
import { Link } from "react-router";
import type { FrameDetail, FrameScore } from "./api/client";
import { useBenchmarkFrame } from "./BenchmarkFrame";
import { useBenchmarkResults } from "./BenchmarkResults";
import { conditionName, formatMetric } from "./benchmarkFormat";
import { clearCounterpart, describeSelection, levelAt, scoreParts, type Selection } from "./frameReview";
import type { Box } from "./overlay";

/** The selected box, the open frame's counts, and this condition's per-class AP beside clear weather. */
export function BenchmarkInspector() {
  const { results, threshold, selected: condition } = useBenchmarkResults();
  const { frame, selectedKey } = useBenchmarkFrame();
  if (!results || !condition) return <p className="empty-state">Run a benchmark to inspect its frames.</p>;

  const level = frame ? levelAt(frame.levels, threshold) : null;
  return (
    <section aria-label="Benchmark details" className="degradation-inspector benchmark-inspector">
      {frame && level && (
        <>
          <SelectionDetails
            frame={frame}
            selected={selectedKey !== null}
            selection={selectedKey === null ? null : describeSelection(frame, level, selectedKey)}
          />
          <FrameCounts score={level.score} threshold={threshold} />
        </>
      )}
      <ClassComparison />
    </section>
  );
}

function SelectionDetails({
  frame,
  selected,
  selection,
}: {
  frame: FrameDetail;
  selected: boolean;
  selection: Selection | null;
}) {
  if (!selected) return <p className="field-note">Click a box in the frame viewer to inspect it.</p>;
  if (!selection) return <p className="field-note">The selected prediction is below the display threshold.</p>;
  const { tag, truth, prediction, iou, weight } = selection;
  return (
    <div>
      <h3 className="inspector-heading">Selected: {tag}</h3>
      <dl className="metrics" aria-label="Selected detection">
        <Row name="Class → predicted">
          {truth ? truth.label : "no label"} → {prediction ? prediction.label : "nothing predicted"}
        </Row>
        <Row name="Confidence">{prediction ? prediction.confidence.toFixed(2) : "—"}</Row>
        <Row name="IoU">{iou === null ? "—" : iou.toFixed(2)}</Row>
        {prediction && <Row name="Predicted box">{boxText(prediction.box)}</Row>}
        {truth && <Row name="Label box">{boxText(truth.box)}</Row>}
        <Row name="Label source">
          {truth ? `the dataset's label file for frame ${frame.id}: “${truth.label}”` : "none: no label here"}
        </Row>
        <Row name="Error weight">{weight}</Row>
      </dl>
    </div>
  );
}

function FrameCounts({ score, threshold }: { score: FrameScore; threshold: number }) {
  return (
    <div>
      <h3 className="inspector-heading">This frame at ≥ {threshold.toFixed(2)}</h3>
      <dl className="metrics" aria-label="Frame counts">
        <Row name="Hits">{score.hits}</Row>
        <Row name="Misses">{score.misses}</Row>
        <Row name="False alarms">{score.false_alarms}</Row>
        <Row name="Class confusions">{score.class_confusions}</Row>
        <Row name="Error score">
          {score.score} ({scoreParts(score)})
        </Row>
      </dl>
    </div>
  );
}

function ClassComparison() {
  const { results, selected: condition } = useBenchmarkResults();
  if (!results || !condition) return null;
  // A synthetic row degrades a clear condition's frames, so it compares against that condition.
  const synthetic = "experiment_id" in condition;
  const clearName = synthetic ? condition.condition : clearCounterpart(condition.condition);
  const clear = results.conditions.find((c) => c.condition === clearName);
  const isClear = !synthetic && clearName === condition.condition;
  const clearAp = (className: string) => clear?.classes.find((c) => c.class_name === className)?.ap ?? null;
  return (
    <div>
      <h3 className="inspector-heading">
        Per-class AP: {synthetic ? condition.title : conditionName(condition.condition)}
        {!isClear && ` vs. ${conditionName(clearName)}`}
      </h3>
      <dl className="metrics" aria-label="Per-class AP">
        {condition.classes.map((row) => (
          <Row key={row.class_name} name={row.class_name}>
            {formatMetric(row.ap)}
            {!isClear && ` vs. ${formatMetric(clearAp(row.class_name))} in clear weather`}
          </Row>
        ))}
      </dl>
      {!isClear && !clear && <p className="field-note">{conditionName(clearName)} is not in this run's manifest.</p>}
      <p className="field-note">
        <Link to="/findings">Compare every condition in Findings</Link>
      </p>
    </div>
  );
}

function Row({ name, children }: { name: string; children: ReactNode }) {
  return (
    <div>
      <dt>{name}</dt>
      <dd className="metric-value">{children}</dd>
    </div>
  );
}

function boxText(box: Box): string {
  return [box.x1, box.y1, box.x2, box.y2].map((v) => v.toFixed(3)).join(", ");
}
