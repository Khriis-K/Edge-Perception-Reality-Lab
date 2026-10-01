import { Button, HTMLSelect, Radio, RadioGroup } from "@blueprintjs/core";
import { useEffect, useState } from "react";
import {
  fetchSamples,
  previewRun,
  type ClearCondition,
  type DegradationSettings,
  type ExperimentSummary,
  type Job,
  type RunPreview,
  type SampleVideo,
} from "./api/client";
import { conditionName } from "./benchmarkFormat";
import { completedJobId, isActive, useCurrentJob } from "./CurrentJob";
import { useDegradationSettings } from "./DegradationSettings";
import { FrameViewer } from "./FrameViewer";
import { useSubsetChoice } from "./SubsetChoice";
import { useSubset } from "./SubsetTable";
import { SyntheticFramesView } from "./SyntheticFrames";
import { useSyntheticResults } from "./SyntheticResults";
import { useDatasetStatus } from "./useDatasetStatus";

type Input = ExperimentSummary["input"];
const CLEAR_CONDITIONS: ClearCondition[] = ["clear-day", "clear-night"];

/**
 * Synthetic screen: pick the sample video, or the clear-weather frames of the subset chosen in Setup, and run it with
 * the degradation set in the inspector. A video run compares clean and degraded frames side by side; a run on the
 * labelled dataset frames also scores both against the ground truth.
 */
export function SyntheticRun() {
  const { job, error, start, startSyntheticFrames, cancel } = useCurrentJob();
  const { settings } = useDegradationSettings();
  const [input, setInput] = useState<Input>("video");
  const [samples, setSamples] = useState<SampleVideo[]>([]);
  const [sampleId, setSampleId] = useState("");
  const [samplesError, setSamplesError] = useState<string | null>(null);
  const [condition, setCondition] = useState<ClearCondition>("clear-day");
  const dataset = useClearFrames();
  const { results, framesResults, error: resultsError, openId, frameIndex, setFrameIndex } = useSyntheticResults();
  const running = isActive(job);
  const preview = useRunPreview(input === "video" ? sampleId : "", settings);
  const manifest = dataset.subset?.manifest;
  const canStart = input === "video" ? Boolean(sampleId) : Boolean(manifest?.frames[condition]?.length);
  // A finished job's "Done" would be wrong next to another run opened from the history. A Benchmark run's status
  // belongs to its own screen, though while it runs, Start run stays disabled: one run at a time.
  const synthetic = job?.mode === "synthetic" || job?.mode === "synthetic-frames" ? job : null;
  const status = synthetic?.status === "completed" && synthetic.experiment_id !== openId ? null : synthetic;

  useEffect(() => {
    fetchSamples()
      .then((list) => {
        setSamples(list);
        setSampleId((current) => current || list[0]?.id || "");
      })
      .catch((e) => setSamplesError(`Could not load the sample videos: ${(e as Error).message}`));
  }, []);

  return (
    <div className="synthetic-run">
      <form
        className="run-form"
        onSubmit={(event) => {
          event.preventDefault();
          if (input === "video") start(sampleId, settings);
          else if (manifest) startSyntheticFrames(manifest, condition, settings);
        }}
      >
        <RadioGroup
          label="Input"
          inline
          selectedValue={input}
          disabled={running}
          onChange={(e) => setInput(e.currentTarget.value as Input)}
        >
          <Radio label="Video" value="video" />
          <Radio label="Clear dataset frames" value="dataset" disabled={running || !dataset.ready} />
        </RadioGroup>
        {input === "video" ? (
          <label>
            Sample video
            <HTMLSelect value={sampleId} onChange={(e) => setSampleId(e.target.value)} disabled={running}>
              {samples.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.title}
                </option>
              ))}
            </HTMLSelect>
          </label>
        ) : (
          <label>
            Frames
            <HTMLSelect
              value={condition}
              onChange={(e) => setCondition(e.target.value as ClearCondition)}
              disabled={running}
            >
              {CLEAR_CONDITIONS.map((c) => (
                <option key={c} value={c}>
                  {conditionName(c)}
                  {manifest && ` (${frameCount(manifest.frames[c]?.length ?? 0)})`}
                </option>
              ))}
            </HTMLSelect>
          </label>
        )}
        <Button type="submit" intent="primary" disabled={!canStart || running}>
          Start run
        </Button>
        {running && (
          <Button type="button" onClick={cancel}>
            Cancel
          </Button>
        )}
        {!running && preview && (
          <span className="run-preview" aria-live="polite">
            {preview.cached ? "Cached: the results will be reused" : "Will start a new job"}
          </span>
        )}
      </form>

      {input === "dataset" && dataset.subset && (
        <p className="field-note">
          From the subset chosen in Setup: seed {dataset.subset.manifest.seed}, up to {dataset.subset.manifest.cap}{" "}
          frames per condition. Results also appear as a condition in Benchmark.
        </p>
      )}
      <RunStatus job={status} />
      {[samplesError, dataset.error, error, resultsError].filter(Boolean).map((message) => (
        <p key={message} role="alert" className="run-error">
          {message}
        </p>
      ))}
      {results && (
        <FrameViewer
          key={results.experiment.id}
          experiment={results.experiment}
          stability={results.stability}
          frameIndex={frameIndex}
          onFrameIndexChange={setFrameIndex}
        />
      )}
      {framesResults && <SyntheticFramesView results={framesResults} />}
    </div>
  );
}

function frameCount(count: number): string {
  return `${count} ${count === 1 ? "frame" : "frames"}`;
}

/** The subset chosen in Setup, whose clear frames a run can degrade. None until the dataset is ready. */
function useClearFrames() {
  const { status } = useDatasetStatus();
  const ready = status?.ready ?? false;
  const [choice] = useSubsetChoice();
  const { subset, error } = useSubset(ready, choice);
  return { ready, subset, error: error && `Couldn't draw the subset: ${error}` };
}

function RunStatus({ job }: { job: Job | null }) {
  if (!job) return null;
  const text = {
    queued: "Starting…",
    running: `Running detection: frame ${job.frames_done} of ${job.frames_total}`,
    completed: job.cached
      ? `Cached, results reused: ${job.frames_total} frames, nothing re-run.`
      : `Done: ${job.frames_total} frames.`,
    cancelled: "Cancelled. Nothing was saved from this run.",
    failed: `Failed. Nothing was saved from this run. ${job.error ?? ""}`,
  }[job.status];
  return <p className="run-status">{text}</p>;
}

/** Whether Start run would reuse cached results or start a new job, re-asked as the settings change. */
function useRunPreview(sampleId: string, settings: DegradationSettings): RunPreview | null {
  const finishedJobId = completedJobId(useCurrentJob().job);
  const [preview, setPreview] = useState<RunPreview | null>(null);
  const { kind, severity, seed } = settings;

  useEffect(() => {
    setPreview(null);
    if (!sampleId) return;
    const controller = new AbortController();
    // Only a hint: when it fails (no weights, say), Start run reports why.
    previewRun(sampleId, { kind, severity, seed }, controller.signal)
      .then(setPreview)
      .catch(() => {});
    return () => controller.abort();
  }, [sampleId, kind, severity, seed, finishedJobId]);

  return preview;
}
