import { Switch } from "@blueprintjs/core";
import { useId, useState } from "react";
import { frameImageUrl, type Experiment } from "./api/client";
import { detectionLabel, toOverlayRect, visibleDetections, type Detection } from "./overlay";

const DEFAULT_THRESHOLD = 0.25;

/**
 * One experiment's frames with their detections drawn over them. Threshold and overlay changes
 * filter the detections already loaded; they never ask the server to run inference again.
 */
export function FrameViewer({ experiment }: { experiment: Experiment }) {
  const [frameIndex, setFrameIndex] = useState(0);
  const [threshold, setThreshold] = useState(Math.max(DEFAULT_THRESHOLD, experiment.confidence_floor));
  const [showOverlays, setShowOverlays] = useState(true);
  const thresholdId = useId();
  const frameId = useId();

  const frame = experiment.frames[frameIndex];
  const detections = visibleDetections(frame.detections, threshold);
  const lastFrame = experiment.frames.length - 1;

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

      <figure className="frame">
        <div className="frame-stack" style={{ aspectRatio: `${experiment.frame_width} / ${experiment.frame_height}` }}>
          <img src={frameImageUrl(experiment.id, frameIndex)} alt={`Frame ${frameIndex + 1} of the sample video`} />
          {showOverlays && <DetectionOverlay detections={detections} />}
        </div>
        <figcaption>
          {detections.length} detections at or above {threshold.toFixed(2)}. Boxes are model outputs, not ground
          truth.
        </figcaption>
      </figure>

      <div className="scrubber">
        <label htmlFor={frameId}>Frame</label>
        <input
          id={frameId}
          type="range"
          min={0}
          max={lastFrame}
          step={1}
          value={frameIndex}
          onChange={(e) => setFrameIndex(Number(e.target.value))}
        />
        <output htmlFor={frameId}>
          {frameIndex + 1} / {lastFrame + 1}
        </output>
      </div>
    </section>
  );
}

/** Boxes in percent units, so the layer stays aligned with the image at any size. */
function DetectionOverlay({ detections }: { detections: Detection[] }) {
  return (
    <svg className="overlay" role="list" aria-label="Detections (model outputs)">
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
