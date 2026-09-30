import { Button } from "@blueprintjs/core";
import type { ReactNode } from "react";
import type { Match, StabilityReport } from "./api/client";
import { useSyntheticResults } from "./SyntheticResults";

// Said wherever stability numbers appear: they compare against the clean frames, not against labels.
const NOT_ACCURACY = "Consistency, not accuracy: this clip has no labels.";
const WORST_FRAMES_SHOWN = 5;

const OUTCOME_TEXT: Record<Match["outcome"], string> = {
  retained: "Retained",
  dropped: "Dropped",
  introduced: "Introduced",
  class_change: "Class change",
};

/** The dock's table: how each detection in the current frame fared under the degradation. */
export function MatchTable() {
  const { results, frameIndex } = useSyntheticResults();
  if (!results) return <p className="empty-state">Run a video to see how each frame's detections match up.</p>;

  const { stability } = results;
  const frame = stability.frames[frameIndex];
  return (
    <table className="match-table">
      <caption>
        Frame {frameIndex + 1}: clean vs. degraded detections at confidence ≥{" "}
        {stability.confidence_threshold.toFixed(2)}, matched at IoU ≥ {stability.iou_threshold.toFixed(2)}.{" "}
        {NOT_ACCURACY}
      </caption>
      <thead>
        <tr>
          <th scope="col">Outcome</th>
          <th scope="col">Clean</th>
          <th scope="col">Degraded</th>
          <th scope="col" className="numeric">
            IoU
          </th>
          <th scope="col" className="numeric">
            Confidence change
          </th>
        </tr>
      </thead>
      <tbody>
        {frame.matches.length === 0 ? (
          <tr>
            <td colSpan={5} className="empty-state">
              No detections at or above {stability.confidence_threshold.toFixed(2)} in either frame.
            </td>
          </tr>
        ) : (
          frame.matches.map((match, i) => (
            <tr key={i}>
              <td>{OUTCOME_TEXT[match.outcome]}</td>
              <td>{describe(match.clean)}</td>
              <td>{describe(match.degraded)}</td>
              <td className="numeric">{match.iou == null ? "—" : match.iou.toFixed(2)}</td>
              <td className="numeric">{match.confidence_change == null ? "—" : signed(match.confidence_change)}</td>
            </tr>
          ))
        )}
      </tbody>
    </table>
  );
}

/** The inspector's stability section: the clip's metrics with their counts, and the worst-frame score. */
export function StabilityInspector() {
  const { results, frameIndex, setFrameIndex } = useSyntheticResults();
  if (!results) return null;

  const { stability } = results;
  return (
    <section aria-label="Stability" className="stability-inspector">
      <h3 className="inspector-heading">Stability vs. the clean baseline</h3>
      <p className="field-note">{NOT_ACCURACY}</p>
      <ClipMetrics stability={stability} />
      <FrameScore stability={stability} frameIndex={frameIndex} />
      <WorstFrames stability={stability} onSelect={setFrameIndex} />
    </section>
  );
}

function ClipMetrics({ stability }: { stability: StabilityReport }) {
  const { retention, introduced, class_changes, median_confidence_shift: shift } = stability;
  return (
    <>
      <dl className="metrics" aria-label="Clip stability">
        <Metric name="Retention rate" value={percent(retention.rate)} lowN={retention.low_n}>
          {retention.count} / {retention.total} clean detections kept their label
        </Metric>
        <Metric name="Introduced rate" value={percent(introduced.rate)} lowN={introduced.low_n}>
          {introduced.count} / {introduced.total} degraded detections are new
        </Metric>
        <Metric name="Class changes" value={String(class_changes.count)} lowN={class_changes.low_n}>
          of {class_changes.total} clean detections
        </Metric>
        <Metric
          name="Median confidence shift"
          value={shift.value === null ? "—" : signed(shift.value)}
          lowN={shift.low_n}
        >
          over {shift.pairs} retained pairs
        </Metric>
        <Metric name="Frames evaluated" value={String(stability.frames_evaluated)}>
          counting detections at confidence ≥ {stability.confidence_threshold.toFixed(2)} only
        </Metric>
      </dl>
      <p className="field-note">
        <span className="low-n">low n</span>: counted over fewer than {stability.low_n_objects} detections (or retained
        pairs), too few to trust. Counts are detections across frames; consecutive frames of the same object are not independent evidence.
      </p>
    </>
  );
}

type MetricProps = { name: string; value: string; lowN?: boolean; children: ReactNode };

export function Metric({ name, value, lowN = false, children }: MetricProps) {
  return (
    <div>
      <dt>{name}</dt>
      <dd>
        <span className="metric-value">{value}</span> {lowN && <span className="low-n">low n</span>}{" "}
        <span className="metric-counts">{children}</span>
      </dd>
    </div>
  );
}

/** Every value that goes into the score, with its weight, not only the total. */
function FrameScore({ stability, frameIndex }: { stability: StabilityReport; frameIndex: number }) {
  const frame = stability.frames[frameIndex];
  const { weights } = stability;
  const rows: [name: string, amount: number, weight: number][] = [
    ["Dropped", frame.dropped, weights.dropped],
    ["Introduced", frame.introduced, weights.introduced],
    ["Class changes", frame.class_changes, weights.class_changes],
    ["Confidence lost", frame.confidence_loss, weights.confidence_loss],
  ];
  return (
    <table className="score-table">
      <caption>Frame {frameIndex + 1} worst-frame score</caption>
      <thead>
        <tr>
          <th scope="col">Value</th>
          <th scope="col" className="numeric">
            Amount
          </th>
          <th scope="col" className="numeric">
            Weight
          </th>
          <th scope="col" className="numeric">
            Adds
          </th>
        </tr>
      </thead>
      <tbody>
        {rows.map(([name, amount, weight]) => (
          <tr key={name}>
            <th scope="row">{name}</th>
            <td className="numeric">{Number.isInteger(amount) ? amount : amount.toFixed(2)}</td>
            <td className="numeric">× {weight}</td>
            <td className="numeric">{(amount * weight).toFixed(2)}</td>
          </tr>
        ))}
      </tbody>
      <tfoot>
        <tr>
          <th scope="row" colSpan={3}>
            Score
          </th>
          <td className="numeric">{frame.score.toFixed(2)}</td>
        </tr>
      </tfoot>
    </table>
  );
}

function WorstFrames({ stability, onSelect }: { stability: StabilityReport; onSelect: (index: number) => void }) {
  const worst = stability.frames
    .map((frame, i) => ({ i, score: frame.score }))
    .filter((f) => f.score > 0)
    .sort((a, b) => b.score - a.score || a.i - b.i)
    .slice(0, WORST_FRAMES_SHOWN);
  return (
    <div className="worst-frames">
      <h4 className="inspector-subheading">Worst frames</h4>
      {worst.length === 0 ? (
        <p className="field-note">No frame changed: the degraded detections match the clean ones throughout.</p>
      ) : (
        <ol>
          {worst.map(({ i, score }) => (
            <li key={i}>
              <Button variant="minimal" size="small" onClick={() => onSelect(i)}>
                Frame {i + 1} · score {score.toFixed(2)}
              </Button>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

function describe(detection: Match["clean"]): string {
  return detection ? `${detection.label} ${detection.confidence.toFixed(2)}` : "—";
}

function signed(value: number): string {
  // Rounds first, so a tiny negative never shows as "-0.00".
  const text = value.toFixed(2);
  return Number(text) > 0 ? `+${text}` : Number(text) === 0 ? "0.00" : text;
}

function percent(rate: number | null): string {
  return rate === null ? "—" : `${(rate * 100).toFixed(0)}%`;
}
