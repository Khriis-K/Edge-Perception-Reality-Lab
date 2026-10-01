import { Switch } from "@blueprintjs/core";
import { useId, useState, type KeyboardEvent, type ReactNode } from "react";
import { Link } from "react-router";
import { datasetFrameUrl, type FrameDetail, type FrameScore } from "./api/client";
import { useBenchmarkFrame } from "./BenchmarkFrame";
import { useBenchmarkResults } from "./BenchmarkResults";
import { conditionName, formatMetric, parseThreshold } from "./benchmarkFormat";
import {
  clearCounterpart,
  describeSelection,
  levelAt,
  overlayItems,
  scoreParts,
  sortFrames,
  unmappedAt,
  type FrameColumn,
  type Layer,
  type OverlayItem,
  type Selection,
  type SortDirection,
} from "./frameReview";
import { toOverlayRect, type Box } from "./overlay";

const LAYERS: [layer: Layer, name: string][] = [
  ["labels", "Labels"],
  ["predictions", "Predictions"],
  ["regions", "Ignore regions"],
];

/**
 * A Benchmark frame with its labels and predictions drawn over it, each tagged with its outcome. The frame arrives
 * matched at every threshold, so toggling layers or moving the threshold never asks the server again.
 * `onSelect` runs when a box is clicked, so the narrow layout can open its inspector drawer.
 */
export function BenchmarkViewer({ onSelect }: { onSelect: () => void }) {
  const { threshold } = useBenchmarkResults();
  const { frame, frameId, error, selectedKey, selectOverlay } = useBenchmarkFrame();
  const [shown, setShown] = useState<Record<Layer, boolean>>({ labels: true, predictions: true, regions: true });

  const select = (key: string) => {
    selectOverlay(key);
    onSelect();
  };

  return (
    <section aria-label="Frame viewer" className="frame-viewer benchmark-viewer">
      <div role="toolbar" aria-label="Overlay controls" className="viewer-toolbar">
        <ThresholdInput />
        {LAYERS.map(([layer, name]) => (
          <Switch
            key={layer}
            className="overlay-switch"
            label={name}
            checked={shown[layer]}
            onChange={(e) => setShown({ ...shown, [layer]: e.currentTarget.checked })}
          />
        ))}
      </div>
      {error && (
        <p role="alert" className="run-error">
          {error}
        </p>
      )}
      {!frameId && <p className="empty-state">This condition has no frames.</p>}
      {frame && (
        <BenchmarkFrameView
          frame={frame}
          threshold={threshold}
          items={overlayItems(frame, levelAt(frame.levels, threshold)).filter((item) => shown[item.layer])}
          selectedKey={selectedKey}
          onSelect={select}
        />
      )}
    </section>
  );
}

function ThresholdInput() {
  const { threshold, setThreshold } = useBenchmarkResults();
  const [text, setText] = useState(String(threshold));
  const id = useId();
  return (
    <span className="threshold-field">
      <label htmlFor={id}>Display threshold</label>
      <input
        id={id}
        className="bp6-input"
        type="number"
        min={0}
        max={1}
        step={0.05}
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          const value = parseThreshold(e.target.value);
          if (value !== null) setThreshold(value);
        }}
      />
    </span>
  );
}

interface FrameViewProps {
  frame: FrameDetail;
  threshold: number;
  items: OverlayItem[];
  selectedKey: string | null;
  onSelect: (key: string) => void;
}

function BenchmarkFrameView({ frame, threshold, items, selectedKey, onSelect }: FrameViewProps) {
  const unmapped = unmappedAt(frame, threshold);
  return (
    <figure className="frame" aria-label="Benchmark frame">
      <figcaption className="pane-title">
        {frame.id} <span className="pane-frame">· {conditionName(frame.condition)}</span>
      </figcaption>
      <div className="frame-stack">
        <img src={datasetFrameUrl(frame.id)} alt={`Camera image of dataset frame ${frame.id}`} />
        <svg className="overlay" role="group" aria-label="Overlays">
          {items.map((item) => (
            <OverlayBox key={item.key} item={item} selected={item.key === selectedKey} onSelect={onSelect} />
          ))}
        </svg>
      </div>
      <p className="viewer-note">
        Labels are dashed, predictions solid. Blue is a hit, orange an error; every box says which. Showing predictions
        at confidence ≥ {threshold.toFixed(2)}.{" "}
        {unmapped > 0 &&
          `${unmapped} ${unmapped === 1 ? "detection" : "detections"} of classes outside the class mapping ${unmapped === 1 ? "is" : "are"} not drawn and not scored.`}
      </p>
    </figure>
  );
}

function OverlayBox({ item, selected, onSelect }: { item: OverlayItem; selected: boolean; onSelect: (key: string) => void }) {
  const rect = toOverlayRect(item.box);
  // A label's tag sits under its box, a prediction's above, so a hit's two tags never overlap.
  const tagY = item.layer === "labels" ? rect.y + rect.height : rect.y;
  const dy = item.layer === "labels" ? 13 : rect.labelAbove ? -4 : 13;
  const onKeyDown = (event: KeyboardEvent) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelect(item.key);
    }
  };
  return (
    <g
      role="button"
      tabIndex={0}
      aria-label={item.text}
      aria-pressed={selected}
      className={`overlay-item ${item.layer} ${item.tone}${selected ? " selected" : ""}`}
      onClick={() => onSelect(item.key)}
      onKeyDown={onKeyDown}
    >
      <rect x={`${rect.x}%`} y={`${rect.y}%`} width={`${rect.width}%`} height={`${rect.height}%`} />
      <text x={`${rect.x}%`} y={`${tagY}%`} dx={3} dy={dy}>
        {item.text}
      </text>
    </g>
  );
}

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
          {truth ? `dataset label “${truth.label}” in frame ${frame.id}` : "none: no label here"}
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
  const clearName = clearCounterpart(condition.condition);
  const clear = results.conditions.find((c) => c.condition === clearName);
  const isClear = clearName === condition.condition;
  const clearAp = (className: string) => clear?.classes.find((c) => c.class_name === className)?.ap ?? null;
  return (
    <div>
      <h3 className="inspector-heading">
        Per-class AP: {conditionName(condition.condition)}
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

const COLUMNS: [column: FrameColumn, name: string][] = [
  ["id", "Frame"],
  ["hits", "Hits"],
  ["misses", "Misses"],
  ["false_alarms", "False alarms"],
  ["class_confusions", "Class confusions"],
  ["ignored", "Ignored"],
  ["score", "Error score"],
];

/** The bottom dock's Frame table: the condition's frames and their error counts, sortable by any column. */
export function FrameTable() {
  const { selected: condition, results } = useBenchmarkResults();
  const { ranked, frameId, openFrame } = useBenchmarkFrame();
  const [sort, setSort] = useState<{ column: FrameColumn; direction: SortDirection }>({
    column: "score",
    direction: "descending",
  });
  if (!results || !condition) return <p className="empty-state">Run a benchmark to list its frames.</p>;

  const rows = sortFrames(ranked, sort.column, sort.direction);
  const toggle = (column: FrameColumn) =>
    setSort({
      column,
      direction: sort.column === column && sort.direction === "descending" ? "ascending" : "descending",
    });
  return (
    <table className="subset-table frame-table">
      <caption>
        {conditionName(condition.condition)}: {rows.length} frames at confidence ≥{" "}
        {results.display_threshold.toFixed(2)}. Error score = misses + false alarms + class confusions.
      </caption>
      <thead>
        <tr>
          {COLUMNS.map(([column, name]) => (
            <th key={column} scope="col" aria-sort={sort.column === column ? sort.direction : undefined}>
              <button type="button" className="sort-button" onClick={() => toggle(column)}>
                {name}
                {sort.column === column && (sort.direction === "descending" ? " ▼" : " ▲")}
              </button>
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.id} aria-current={row.id === frameId ? "true" : undefined}>
            <th scope="row">
              <button type="button" className="link-button" onClick={() => openFrame(row.id)}>
                {row.id}
              </button>
            </th>
            <td>{row.hits}</td>
            <td>{row.misses}</td>
            <td>{row.false_alarms}</td>
            <td>{row.class_confusions}</td>
            <td>{row.ignored}</td>
            <td>{row.score}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
