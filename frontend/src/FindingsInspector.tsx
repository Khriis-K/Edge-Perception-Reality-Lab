import type { ReactNode } from "react";
import { Link } from "react-router";
import type { BenchmarkFindings, VideoFindings } from "./api/client";
import { conditionName } from "./benchmarkFormat";
import { useFindings } from "./FindingsData";
import { LatencySection } from "./Latency";
import { modelLine } from "./latencyFormat";

/** Findings' inspector: what the run was, how fast it ran, and what to read before trusting it. */
export function FindingsInspector() {
  const { findings } = useFindings();
  if (!findings) return <p className="empty-state">Open a finished run to see its record.</p>;
  return (
    <section aria-label="Run details" className="degradation-inspector findings-inspector">
      <section aria-label="Read this first">
        <h3 className="inspector-heading">Read this first</h3>
        <ul className="limitations">
          {findings.limitations.map((limitation) => (
            <li key={limitation}>{limitation}</li>
          ))}
        </ul>
        <p className="field-note">
          <Link to="/report">Export as report</Link>
        </p>
      </section>
      {findings.kind === "benchmark" ? <BenchmarkRecord findings={findings} /> : <VideoRecord findings={findings} />}
      <LatencySection
        model={findings.record.model}
        latency={findings.latency ?? null}
        readNote={findings.kind === "benchmark" ? "to read a dataset image" : "to decode a frame"}
      />
    </section>
  );
}

function BenchmarkRecord({ findings }: { findings: BenchmarkFindings }) {
  const { record } = findings;
  const { manifest, class_mapping: mapping } = record;
  return (
    <section aria-label="Run record">
      <h3 className="inspector-heading">Run record</h3>
      <dl className="metrics">
        <Row name="Frames · objects">
          {record.frames} frames · {record.objects} objects
        </Row>
        <Row name="Manifest">
          seed {manifest.seed}, up to {manifest.cap} per condition, vocabulary v{manifest.vocabulary_version}
        </Row>
        <Row name="Frames per condition">
          {Object.entries(manifest.frames)
            .map(([condition, ids]) => `${conditionName(condition)} ${ids.length}`)
            .join(" · ")}
        </Row>
        <Row name="Model">{modelLine(record.model)}</Row>
        <Row name="Class map">
          {`v${mapping.version}: `}
          {mapping.mapping.map((row) => `${row.coco} → ${row.dataset_class}`).join(", ")}
        </Row>
        <Row name="Ignore rule">{mapping.ignore_rule}</Row>
        <Row name="Match IoU">≥ {record.match_iou}, class-aware</Row>
        <Row name="Confidence floor">{record.confidence_floor} (raw detections kept down to it)</Row>
        <Row name="Worst-frame weights">
          misses {record.weights.misses} · false alarms {record.weights.false_alarms} · class confusions{" "}
          {record.weights.class_confusions}
        </Row>
      </dl>
    </section>
  );
}

function VideoRecord({ findings }: { findings: VideoFindings }) {
  const { record } = findings;
  const { degradation } = record;
  return (
    <section aria-label="Run record">
      <h3 className="inspector-heading">Run record</h3>
      <dl className="metrics">
        <Row name="Input">{record.sample_title}</Row>
        <Row name="Frames">
          {record.frames} frames, {record.frame_width}×{record.frame_height}
        </Row>
        <Row name="Degradation">
          {degradation.kind}, severity {degradation.severity.toFixed(2)}, seed {degradation.seed}
        </Row>
        <Row name="Model">{modelLine(record.model)}</Row>
        <Row name="Match IoU">≥ {record.match_iou}, class-aware</Row>
        <Row name="Stability threshold">detections ≥ {record.stability_threshold} are matched</Row>
        <Row name="Confidence floor">{record.confidence_floor}</Row>
      </dl>
    </section>
  );
}

/** One line of an inspector's record: a name and its value. */
export function Row({ name, children }: { name: string; children: ReactNode }) {
  return (
    <div>
      <dt>{name}</dt>
      <dd className="record-value">{children}</dd>
    </div>
  );
}
