import { Button, HTMLSelect } from "@blueprintjs/core";
import { useEffect, useState } from "react";
import { fetchExperiment, fetchSamples, type Experiment, type Job, type SampleVideo } from "./api/client";
import { isActive, useCurrentJob } from "./CurrentJob";
import { FrameViewer } from "./FrameViewer";

/** Synthetic screen: pick the sample video, run the detector on it, and inspect every frame. */
export function SyntheticRun() {
  const { job, error, start, cancel } = useCurrentJob();
  const [samples, setSamples] = useState<SampleVideo[]>([]);
  const [sampleId, setSampleId] = useState("");
  const [samplesError, setSamplesError] = useState<string | null>(null);
  const { experiment, error: resultsError } = useCompletedExperiment(job);
  const running = isActive(job);

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
          start(sampleId);
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
      </form>

      <RunStatus job={job} />
      {[samplesError, error, resultsError].filter(Boolean).map((message) => (
        <p key={message} role="alert" className="run-error">
          {message}
        </p>
      ))}
      {experiment && <FrameViewer key={experiment.id} experiment={experiment} />}
    </div>
  );
}

function RunStatus({ job }: { job: Job | null }) {
  if (!job) return null;
  const text = {
    queued: "Starting…",
    running: `Running detection: frame ${job.frames_done} of ${job.frames_total}`,
    completed: `Done: ${job.frames_total} frames.`,
    cancelled: "Cancelled. Nothing was saved from this run.",
    failed: `Failed. Nothing was saved from this run. ${job.error ?? ""}`,
  }[job.status];
  return <p className="run-status">{text}</p>;
}

/** The results of the current job once, and only once, it has completed. */
function useCompletedExperiment(job: Job | null): { experiment: Experiment | null; error: string | null } {
  const [experiment, setExperiment] = useState<Experiment | null>(null);
  const [error, setError] = useState<string | null>(null);
  const completedId = job?.status === "completed" ? job.experiment_id : null;

  useEffect(() => {
    setExperiment(null);
    setError(null);
    if (!completedId) return;
    let cancelled = false;
    fetchExperiment(completedId)
      .then((result) => !cancelled && setExperiment(result))
      .catch((e) => !cancelled && setError(`Could not load the results: ${(e as Error).message}`));
    return () => {
      cancelled = true;
    };
  }, [completedId]);

  return { experiment, error };
}
