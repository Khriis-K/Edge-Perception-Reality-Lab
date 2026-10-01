import { Switch } from "@blueprintjs/core";
import { useId, useState, type KeyboardEvent } from "react";
import { datasetFrameUrl, type FrameDetail } from "./api/client";
import { useBenchmarkFrame } from "./BenchmarkFrame";
import { useBenchmarkResults } from "./BenchmarkResults";
import { conditionName, parseThreshold } from "./benchmarkFormat";
import { levelAt, overlayItems, unmappedAt, type Layer, type OverlayItem } from "./frameReview";
import { toOverlayRect } from "./overlay";


const LAYERS: [layer: Layer, name: string][] = [
  ["labels", "Labels"],
  ["predictions", "Predictions"],
  ["regions", "Ignore regions"],
];

/**
 * A Benchmark frame with its labels and predictions drawn over it, each tagged with its outcome. The frame arrives
 * matched at every threshold, so toggling layers or moving the threshold never asks the server again.
 * `onOpenInspector` runs when a box is clicked, so the narrow layout can open its inspector drawer.
 */
export function BenchmarkViewer({ onOpenInspector }: { onOpenInspector: () => void }) {
  const { threshold } = useBenchmarkResults();
  const { frame, frameId, error, selectedKey, selectOverlay } = useBenchmarkFrame();
  const [shown, setShown] = useState<Record<Layer, boolean>>({ labels: true, predictions: true, regions: true });

  const select = (key: string) => {
    selectOverlay(key);
    onOpenInspector();
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

