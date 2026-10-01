import { Button } from "@blueprintjs/core";
import { useState, type ChangeEvent } from "react";
import type { ConditionResult, Job, Manifest } from "./api/client";
import { useBenchmarkFrame } from "./BenchmarkFrame";
import { useBenchmarkResults } from "./BenchmarkResults";
import { BenchmarkViewer } from "./BenchmarkViewer";
import { conditionName, formatMetric } from "./benchmarkFormat";
import { scoreParts } from "./frameReview";
import { isActive, useCurrentJob } from "./CurrentJob";
import { useSubsetChoice } from "./SubsetChoice";
import { useSubset } from "./SubsetTable";
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
  const { results, selected } = useBenchmarkResults();
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
      <BenchmarkViewer onOpenInspector={onOpenInspector} />
      {selected && <ClassTable condition={selected} threshold={results.display_threshold} lowN={results.low_n_objects} />}
    </>
  );
}

function ClassTable({ condition, threshold, lowN }: { condition: ConditionResult; threshold: number; lowN: number }) {
  return (
    <table className="subset-table class-table">
      <caption>
        {conditionName(condition.condition)}: mAP {formatMetric(condition.map)} over {condition.frames} frames.
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
 * Benchmark's explorer: every condition in the run's manifest with its mAP, then the manifest and model. Clicking a
 * condition selects and expands it to its frames, worst first; clicking it again collapses it.
 */
export function BenchmarkExplorer({ empty }: { empty: string }) {
  const { results, selected, select } = useBenchmarkResults();
  const [expanded, setExpanded] = useState<string | null>(null);

  // A load error is shown in the work area; results already loaded stay listed beside it.
  if (!results) return <p className="empty-state">{empty}</p>;
  const { manifest, model } = results;
  return (
    <div className="run-explorer">
      <ul aria-label="Conditions" className="run-list">
        {results.conditions.map((row) => (
          <li key={row.condition}>
            <button
              type="button"
              className="run-item"
              aria-current={row.condition === selected?.condition ? "true" : undefined}
              aria-expanded={row.condition === expanded}
              onClick={() => {
                select(row.condition);
                setExpanded(row.condition === expanded ? null : row.condition);
              }}
            >
              <span>{conditionName(row.condition)}</span>
              <span className="run-meta">
                mAP {formatMetric(row.map)} · {row.objects} {row.objects === 1 ? "object" : "objects"}
                {row.low_n && (
                  <>
                    {" · "}
                    <span className="low-n">low n</span>
                  </>
                )}
              </span>
            </button>
            {row.condition === expanded && row.condition === selected?.condition && <FrameList />}
          </li>
        ))}
      </ul>
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
