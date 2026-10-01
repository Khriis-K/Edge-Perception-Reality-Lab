import { useEffect, useState } from "react";
import { NavLink, useNavigate } from "react-router";
import { fetchCacheInfo, fetchExperiments, type CacheInfo, type ExperimentSummary } from "./api/client";
import { completedJobId, useCurrentJob } from "./CurrentJob";
import { formatBytes, groupByInput } from "./runHistoryFormat";
import { useSyntheticResults } from "./SyntheticResults";

interface RunHistory {
  runs: ExperimentSummary[] | null;
  cache: CacheInfo | null;
  error: string | null;
}

/** The cached runs and the cache folder, re-read whenever a run completes. */
function useRunHistory(): RunHistory {
  const finishedJobId = completedJobId(useCurrentJob().job);
  const [history, setHistory] = useState<RunHistory>({ runs: null, cache: null, error: null });

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([fetchExperiments(controller.signal), fetchCacheInfo(controller.signal)])
      .then(([runs, cache]) => setHistory({ runs, cache, error: null }))
      .catch((e) => {
        if (!controller.signal.aborted)
          setHistory((current) => ({ ...current, error: `Could not load the runs: ${(e as Error).message}` }));
      });
    return () => controller.abort();
  }, [finishedJobId]);

  return history;
}

/** Setup's explorer: every run, a New run entry, and where the cache lives. */
export function SetupExplorer({ empty }: { empty: string }) {
  const { runs, cache, error } = useRunHistory();

  return (
    <div className="run-explorer">
      <NavLink to="/setup" className="run-item new-run">
        + New run
      </NavLink>
      <RunList label="Runs" runs={runs} empty={empty} error={error} showInput />
      {cache && (
        <footer className="cache-info">
          <span>Cache folder</span>
          <code title={cache.folder}>{cache.folder}</code>
          <span>{formatBytes(cache.size_bytes)}</span>
        </footer>
      )}
    </div>
  );
}

/** Synthetic's explorer: the synthetic runs, grouped by the input they ran on. */
export function SyntheticExplorer({ empty }: { empty: string }) {
  const { runs, error } = useRunHistory();
  if (!runs?.length) return <RunList label="Synthetic runs" runs={runs} empty={empty} error={error} />;

  return (
    <div className="run-explorer">
      {groupByInput(runs).map((group) => (
        <section key={group.sampleId} aria-label={group.title}>
          <h3 className="run-group">{group.title}</h3>
          <RunList label={`Runs on ${group.title}`} runs={group.runs} empty={empty} error={error} />
        </section>
      ))}
    </div>
  );
}

function RunList(props: {
  label: string;
  runs: ExperimentSummary[] | null;
  empty: string;
  error: string | null;
  showInput?: boolean;
}) {
  const { openId, openExperiment } = useSyntheticResults();
  const navigate = useNavigate();
  const { label, runs, empty, error, showInput } = props;

  if (error) return <p role="alert" className="empty-state">{error}</p>;
  if (!runs) return <p className="empty-state">Loading runs…</p>;
  if (!runs.length) return <p className="empty-state">{empty}</p>;
  return (
    <ul aria-label={label} className="run-list">
      {runs.map((run) => (
        <li key={run.id}>
          {/* Opens the cached results: nothing runs again. */}
          <button
            type="button"
            className="run-item"
            aria-current={run.id === openId ? "true" : undefined}
            onClick={() => {
              openExperiment(run.id, run.input);
              navigate("/synthetic");
            }}
          >
            <span>
              {run.degradation.kind}, severity {run.degradation.severity.toFixed(2)}, seed {run.degradation.seed}
            </span>
            <span className="run-meta">
              {showInput && `${run.sample_title} · `}
              {run.frame_count} frames · {new Date(run.saved_at).toLocaleString()}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}
