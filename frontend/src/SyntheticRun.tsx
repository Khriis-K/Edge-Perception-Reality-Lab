import { Button, HTMLSelect } from "@blueprintjs/core";
import { useEffect, useState } from "react";
import { fetchSamples, type Job, type SampleVideo } from "./api/client";
import { isActive, useCurrentJob } from "./CurrentJob";
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
  const { results, error: resultsError, frameIndex, setFrameIndex } = useSyntheticResults();
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
      </form>

      <RunStatus job={job} />
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
    completed: `Done: ${job.frames_total} frames.`,
    cancelled: "Cancelled. Nothing was saved from this run.",
    failed: `Failed. Nothing was saved from this run. ${job.error ?? ""}`,
  }[job.status];
  return <p className="run-status">{text}</p>;
}
