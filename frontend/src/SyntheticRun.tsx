import { Button, HTMLSelect } from "@blueprintjs/core";
import { useEffect, useState } from "react";
import {
  fetchSamples,
  previewRun,
  type DegradationSettings,
  type Job,
  type RunPreview,
  type SampleVideo,
} from "./api/client";
import { completedJobId, isActive, useCurrentJob } from "./CurrentJob";
import { useDegradationSettings } from "./DegradationSettings";
import { FrameViewer } from "./FrameViewer";
import { useSyntheticResults } from "./SyntheticResults";

/**
 * Synthetic screen: pick the sample video and run it with the degradation set in the inspector,
 * then compare clean and degraded frames side by side.
 */
export function SyntheticRun() {
  const { job, error, start, cancel } = useCurrentJob();
  const { settings } = useDegradationSettings();
  const [samples, setSamples] = useState<SampleVideo[]>([]);
  const [sampleId, setSampleId] = useState("");
  const [samplesError, setSamplesError] = useState<string | null>(null);
  const { results, error: resultsError, openId, frameIndex, setFrameIndex } = useSyntheticResults();
  const running = isActive(job);
  const preview = useRunPreview(sampleId, settings);
  // A finished job's "Done" would be wrong next to another run opened from the history.
  const status = job?.status === "completed" && job.experiment_id !== openId ? null : job;

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
          start(sampleId, settings);
        }}
      >
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
        <Button type="submit" intent="primary" disabled={!sampleId || running}>
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

      <RunStatus job={status} />
      {[samplesError, error, resultsError].filter(Boolean).map((message) => (
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
    </div>
  );
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
