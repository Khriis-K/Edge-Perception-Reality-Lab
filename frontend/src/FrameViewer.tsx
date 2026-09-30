import { Switch } from "@blueprintjs/core";
import { useId, useState, type CSSProperties } from "react";
import { frameImageUrl, type Experiment, type FrameVariant, type StabilityReport } from "./api/client";
import { instabilityLevels } from "./instability";
import { detectionLabel, toOverlayRect, visibleDetections, type Detection } from "./overlay";

const DEFAULT_THRESHOLD = 0.25;

/**
 * One experiment's clean and degraded frames side by side, with their detections drawn over them.
 * One scrubber drives both panes, so they always show the same frame. Threshold and overlay
 * changes filter the detections already loaded; they never ask the server to run inference again.
 * The instability strip under the scrubber shades each frame by its worst-frame score.
 */
export function FrameViewer({
  experiment,
  stability,
  frameIndex,
  onFrameIndexChange,
}: {
  experiment: Experiment;
  stability: StabilityReport;
  frameIndex: number;
  onFrameIndexChange: (index: number) => void;
}) {
  const [threshold, setThreshold] = useState(Math.max(DEFAULT_THRESHOLD, experiment.confidence_floor));
  const [showOverlays, setShowOverlays] = useState(true);
  const thresholdId = useId();
  const frameId = useId();

  const frame = experiment.frames[frameIndex];
  const lastFrame = experiment.frames.length - 1;
  const { kind, severity } = experiment.degradation;
  const pane = (variant: FrameVariant, title: string, detections: Detection[]) => (
    <FramePane
      experiment={experiment}
      variant={variant}
      title={title}
      frameIndex={frameIndex}
      detections={visibleDetections(detections, threshold)}
      threshold={threshold}
      showOverlays={showOverlays}
    />
  );

  return (
    <section aria-label="Frame viewer" className="frame-viewer">
      <div role="toolbar" aria-label="Overlay controls" className="viewer-toolbar">
        <label htmlFor={thresholdId}>Display threshold</label>
        <input
          id={thresholdId}
          type="range"
          min={experiment.confidence_floor}
          max={1}
          step={0.05}
          value={threshold}
          onChange={(e) => setThreshold(Number(e.target.value))}
        />
        <output htmlFor={thresholdId}>{threshold.toFixed(2)}</output>
        <Switch
          className="overlay-switch"
          label="Show overlays"
          checked={showOverlays}
          onChange={(e) => setShowOverlays(e.currentTarget.checked)}
        />
      </div>

      <div className="frame-panes">
        {pane("clean", "Clean", frame.clean)}
        {pane("degraded", `Degraded: ${kind}, severity ${severity.toFixed(2)}`, frame.degraded)}
      </div>
      <p className="viewer-note">Boxes are model outputs, not ground truth.</p>

      <div className="scrubber">
        <label htmlFor={frameId}>Frame</label>
        <input
          id={frameId}
          type="range"
          min={0}
          max={lastFrame}
          step={1}
          value={frameIndex}
          onChange={(e) => onFrameIndexChange(Number(e.target.value))}
        />
        <output htmlFor={frameId}>
          {frameIndex + 1} / {lastFrame + 1}
        </output>
      </div>
      <InstabilityStrip stability={stability} frameIndex={frameIndex} onSelect={onFrameIndexChange} />
    </section>
  );
}

interface FramePaneProps {
  experiment: Experiment;
  variant: FrameVariant;
  title: string;
  frameIndex: number;
  detections: Detection[];
  threshold: number;
  showOverlays: boolean;
}

/** One side of the comparison. Its title is text, so clean vs. degraded never rests on color alone. */
function FramePane({ experiment, variant, title, frameIndex, detections, threshold, showOverlays }: FramePaneProps) {
  const name = variant === "clean" ? "Clean" : "Degraded";
  return (
    <figure className={`frame ${variant}`} aria-label={`${name} frame`}>
      <figcaption className="pane-title">
        {title} <span className="pane-frame">· frame {frameIndex + 1}</span>
      </figcaption>
      <div className="frame-stack" style={{ aspectRatio: `${experiment.frame_width} / ${experiment.frame_height}` }}>
        <img
          src={frameImageUrl(experiment.id, variant, frameIndex)}
          alt={`${name} frame ${frameIndex + 1} of the sample video`}
        />
        {showOverlays && <DetectionOverlay name={`${name} detections (model outputs)`} detections={detections} />}
      </div>
      <p className="pane-count">
        {detections.length} detections at or above {threshold.toFixed(2)}
      </p>
    </figure>
  );
}

/** Boxes in percent units, so the layer stays aligned with the image at any size. */
function DetectionOverlay({ name, detections }: { name: string; detections: Detection[] }) {
  return (
    <svg className="overlay" role="list" aria-label={name}>
      {detections.map((detection, i) => {
        const rect = toOverlayRect(detection.box);
        return (
          <g key={i} role="listitem" className="detection">
            <rect x={`${rect.x}%`} y={`${rect.y}%`} width={`${rect.width}%`} height={`${rect.height}%`} />
            <text x={`${rect.x}%`} y={`${rect.y}%`} dx={3} dy={rect.labelAbove ? -4 : 13}>
              {detectionLabel(detection)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

/**
 * One mark per frame, darker where the degraded detections differ more from the clean ones.
 * Clicking a mark moves the scrubber; the scrubber stays the keyboard route, so marks aren't tab stops.
 */
function InstabilityStrip({
  stability,
  frameIndex,
  onSelect,
}: {
  stability: StabilityReport;
  frameIndex: number;
  onSelect: (index: number) => void;
}) {
  const levels = instabilityLevels(stability.frames.map((f) => f.score));
  return (
    <div className="instability">
      <div role="group" aria-label="Instability strip" className="instability-strip">
        {stability.frames.map((frame, i) => {
          const label = `Frame ${i + 1}: worst-frame score ${frame.score.toFixed(2)}`;
          return (
            <button
              key={frame.index}
              type="button"
              tabIndex={-1}
              aria-label={label}
              aria-current={i === frameIndex || undefined}
              title={label}
              className="instability-mark"
              style={{ "--level": levels[i] } as CSSProperties}
              onClick={() => onSelect(i)}
            />
          );
        })}
      </div>
      <p className="instability-legend">Instability vs. the clean frames: lighter is steadier, darker is worse.</p>
    </div>
  );
}
