import { Button } from "@blueprintjs/core";
import { useState, type ChangeEvent, type ReactNode } from "react";
import type { ClassMetrics, ConditionResult, Job, Manifest, SyntheticConditionResult } from "./api/client";
import { useBenchmarkFrame } from "./BenchmarkFrame";
import { useBenchmarkResults } from "./BenchmarkResults";
import { BenchmarkViewer } from "./BenchmarkViewer";
import { conditionName, formatMetric } from "./benchmarkFormat";
import { isActive, useCurrentJob } from "./CurrentJob";
import { useSubsetChoice } from "./SubsetChoice";
import { useSubset } from "./SubsetTable";
import { scoreParts } from "./frameReview";
import { ThresholdField } from "./ThresholdField";
import { useDatasetStatus } from "./useDatasetStatus";

/**
 * Benchmark screen: run the detector over the subset chosen in Setup (or a saved manifest file), then read each
 * condition's per-class AP, and precision and recall at the display threshold, and review its frames.
 * `onOpenInspector` runs when a box in the frame viewer is clicked, to open the inspector drawer.
 */
export function BenchmarkRun({ onOpenInspector }: { onOpenInspector: () => void }) {
  const { status } = useDatasetStatus();
  const ready = status?.ready ?? false;
  const [choice] = useSubsetChoice();
  const { subset, error: subsetError } = useSubset(ready, choice);
  const { job, error, startBenchmark, cancel } = useCurrentJob();
  const { results, error: resultsError } = useBenchmarkResults();
  const [fileError, setFileError] = useState<string | null>(null);
  const running = isActive(job);

  async function runFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = ""; // so choosing the same file again runs it again
    if (!file) return;
    setFileError(null);
    let manifest: Manifest;
    try {
      manifest = JSON.parse(await file.text());
    } catch {
      setFileError(`${file.name} is not a JSON manifest.`);
      return;
    }
    // The server checks it: vocabulary version, conditions, and that every frame is in the local dataset.
    startBenchmark(manifest);
  }

  return (
    <div className="benchmark-run">
      {status && !ready && (
        <p className="dataset-message">Benchmark mode needs a ready dataset. Set it up in Setup.</p>
      )}
      <form
        className="run-form"
        onSubmit={(event) => {
          event.preventDefault();
          if (subset) startBenchmark(subset.manifest);
        }}
      >
        {subset && (
          <span>
            Subset: seed {subset.manifest.seed}, up to {subset.manifest.cap} frames per condition
          </span>
        )}
        <Button type="submit" intent="primary" disabled={!subset || running}>
          Run benchmark
        </Button>
        <label className="manifest-file">
          Run a saved manifest
          <input type="file" accept=".json,application/json" onChange={runFile} disabled={!ready || running} />
        </label>
        {running && (
          <Button type="button" onClick={cancel}>
            Cancel
          </Button>
        )}
      </form>

      <BenchmarkStatus job={job?.mode === "benchmark" ? job : null} />
      {[subsetError && `Couldn't draw the subset: ${subsetError}`, fileError, error, resultsError]
        .filter(Boolean)
        .map((message) => (
          <p key={message} role="alert" className="run-error">
            {message}
          </p>
        ))}
      {results && <BenchmarkBody onOpenInspector={onOpenInspector} />}
    </div>
  );
}

function BenchmarkStatus({ job }: { job: Job | null }) {
  if (!job) return null;
  const text = {
    queued: "Starting…",
    running: `Running the detector: frame ${job.frames_done} of ${job.frames_total}`,
    completed: job.cached
      ? `Cached, results reused: ${job.frames_total} frames, nothing re-run.`
      : `Done: ${job.frames_total} frames.`,
    cancelled: "Cancelled. Nothing was saved from this run.",
    failed: `Failed. Nothing was saved from this run. ${job.error ?? ""}`,
  }[job.status];
  return <p className="run-status">{text}</p>;
}

function BenchmarkBody({ onOpenInspector }: { onOpenInspector: () => void }) {
  const { results, threshold, setThreshold, selected } = useBenchmarkResults();
  if (!results) return null;

  return (
    <>
      {results.warnings.length > 0 && (
        <ul aria-label="Warnings" className="run-warnings">
          {results.warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      )}
      {/* A synthetic row's degraded images aren't kept, so it has no frames to view: just the threshold. */}
      {selected && "experiment_id" in selected ? (
        <ThresholdField threshold={threshold} onChange={setThreshold} />
      ) : (
        <BenchmarkViewer onOpenInspector={onOpenInspector} />
      )}
      {selected && (
        <ClassTable
          title={"experiment_id" in selected ? syntheticName(selected) : conditionName(selected.condition)}
          condition={selected}
          threshold={results.display_threshold}
          lowN={results.low_n_objects}
        />
      )}
    </>
  );
}

/** "Synthetic fog 0.60 on Clear · day frames". */
function syntheticName(row: SyntheticConditionResult): string {
  return `${row.title} on ${conditionName(row.condition)} frames`;
}

type ClassTableProps = {
  title: string;
  condition: { map: number | null; frames: number; classes: ClassMetrics[] };
  threshold: number;
  lowN: number;
};

/** Per-class AP, precision and recall for one condition, with the counts behind each. */
export function ClassTable({ title, condition, threshold, lowN }: ClassTableProps) {
  return (
    <table className="subset-table class-table">
      <caption>
        {title}: mAP {formatMetric(condition.map)} over {condition.frames} frames.
        Precision and recall at confidence ≥ {threshold.toFixed(2)}; <span className="low-n">low n</span>: fewer
        than {lowN} objects.
      </caption>
      <thead>
        <tr>
          <th scope="col">Class</th>
          <th scope="col">Objects</th>
          <th scope="col">Frames</th>
          <th scope="col">AP</th>
          <th scope="col">Precision</th>
          <th scope="col">Recall</th>
          <th scope="col">Sample size</th>
        </tr>
      </thead>
      <tbody>
        {condition.classes.map((row) => (
          <tr key={row.class_name}>
            <th scope="row">{row.class_name}</th>
            <td>{row.objects}</td>
            <td>{row.frames}</td>
            <td>{formatMetric(row.ap)}</td>
            <td>{formatMetric(row.precision)}</td>
            <td>{formatMetric(row.recall)}</td>
            <td>{row.low_n && <span className="low-n">low n</span>}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

const SHOWN_FRAMES = 10; // per expanded condition; the rest are in the dock's Frame table

/**
 * Benchmark's explorer: every condition in the run's manifest with its mAP, then the synthetic degradations run on
 * its clear frames, then the manifest and model. Clicking a real condition selects and expands it to its frames,
 * worst first; clicking it again collapses it.
 */
export function BenchmarkExplorer({ empty }: { empty: string }) {
  const { results, selected, select } = useBenchmarkResults();
  const [expanded, setExpanded] = useState<string | null>(null);

  // A load error is shown in the work area; results already loaded stay listed beside it.
  if (!results) return <p className="empty-state">{empty}</p>;
  const { manifest, model } = results;
  const selectedKey = selected && ("experiment_id" in selected ? selected.experiment_id : selected.condition);
  return (
    <div className="run-explorer">
      <ul aria-label="Conditions" className="run-list">
        {results.conditions.map((row) => (
          <ConditionItem
            key={row.condition}
            row={row}
            name={conditionName(row.condition)}
            current={row.condition === selectedKey}
            expanded={row.condition === expanded}
            onSelect={() => {
              select(row.condition);
              setExpanded(row.condition === expanded ? null : row.condition);
            }}
          >
            {row.condition === expanded && row.condition === selectedKey && <FrameList />}
          </ConditionItem>
        ))}
      </ul>
      {results.synthetic.length > 0 && (
        <>
          <h3 className="run-group">Synthetic, on clear frames</h3>
          {/* Its name leaves out "conditions": lists are found by name, and this must never pass for the real ones. */}
          <ul aria-label="Synthetic degradations" className="run-list">
            {results.synthetic.map((row) => (
              <ConditionItem
                key={row.experiment_id}
                row={row}
                name={row.title}
                detail={`${conditionName(row.condition)} frames, seed ${row.degradation.seed}`}
                current={row.experiment_id === selectedKey}
                onSelect={() => select(row.experiment_id)}
              />
            ))}
          </ul>
        </>
      )}
      <footer className="cache-info">
        <span>Frames ranked by error score at confidence ≥ {results.display_threshold.toFixed(2)}</span>
        <span>
          Manifest: seed {manifest.seed}, up to {manifest.cap} per condition, vocabulary v{manifest.vocabulary_version}
        </span>
        <span>
          {model.name} {model.version} · {model.runtime}
        </span>
      </footer>
    </div>
  );
}

type ConditionItemProps = {
  row: ConditionResult;
  name: string;
  detail?: string;
  current: boolean;
  /** Set on rows that expand to their frames; synthetic rows have none. */
  expanded?: boolean;
  onSelect: () => void;
  children?: ReactNode;
};

function ConditionItem({ row, name, detail, current, expanded, onSelect, children }: ConditionItemProps) {
  return (
    <li>
      <button
        type="button"
        className="run-item"
        aria-current={current ? "true" : undefined}
        aria-expanded={expanded}
        onClick={onSelect}
      >
        <span>{name}</span>
        <span className="run-meta">
          {detail && `${detail} · `}
          mAP {formatMetric(row.map)} · {row.objects} {row.objects === 1 ? "object" : "objects"}
          {row.low_n && (
            <>
              {" · "}
              <span className="low-n">low n</span>
            </>
          )}
        </span>
      </button>
      {children}
    </li>
  );
}

/** The selected condition's worst frames, each with its score and what it is made of. */
function FrameList() {
  const { ranked, frameId, openFrame } = useBenchmarkFrame();
  if (ranked.length === 0) return <p className="frame-list-note">No frames.</p>;
  const more = ranked.length - SHOWN_FRAMES;
  return (
    <>
      <ul aria-label="Frames, worst first" className="frame-list">
        {ranked.slice(0, SHOWN_FRAMES).map((frame) => (
          <li key={frame.id}>
            <button
              type="button"
              className="run-item frame-item"
              aria-current={frame.id === frameId ? "true" : undefined}
              onClick={() => openFrame(frame.id)}
            >
              <span>{frame.id}</span>
              <span className="run-meta">
                score {frame.score} · {scoreParts(frame)}
              </span>
            </button>
          </li>
        ))}
      </ul>
      {more > 0 && <p className="frame-list-note">+ {more} more in the Frame table</p>}
    </>
  );
}
