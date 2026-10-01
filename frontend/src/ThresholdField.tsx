import { useId, useState } from "react";
import { parseThreshold } from "./benchmarkFormat";

/** The confidence precision and recall are counted at. Changing it re-scores stored detections; nothing re-runs. */
export function ThresholdField({ threshold, onChange }: { threshold: number; onChange: (value: number) => void }) {
  // The typed text, kept apart from the value so a half-typed number like "0." stays in the box.
  const [text, setText] = useState(String(threshold));
  const id = useId();
  return (
    <div className="field threshold-field">
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
          if (value !== null) onChange(value);
        }}
      />
    </div>
  );
}
