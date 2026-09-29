import { Icon } from "@blueprintjs/core";
import { useNavigate } from "react-router";
import { apiHost } from "./api/client";
import { isActive, useCurrentJob } from "./CurrentJob";
import type { Section } from "./sections";
import { useServerHealth } from "./useServerHealth";

/** `onOpenInspector` is given only while the inspector is a drawer; it shows the toggle that opens it. */
export function TopBar({ section, onOpenInspector }: { section: Section; onOpenInspector?: () => void }) {
  const navigate = useNavigate();

  return (
    <header className="top-bar">
      <div className="brand">
        <Icon icon="selection" size={16} aria-hidden />
        <span className="brand-name">Perception Reliability Lab</span>
      </div>
      <nav aria-label="Breadcrumb" className="breadcrumbs">
        <ol>
          <li>workbench</li>
          <li aria-current="page">{section.id}</li>
        </ol>
      </nav>

      <div className="top-bar-actions">
        <JobPill />
        {/* Placeholder until the command palette ticket. */}
        <button type="button" className="command-search" disabled>
          <span>Search frames, runs, commands</span>
          <kbd>Ctrl K</kbd>
        </button>
        <ServerStatus />
        {onOpenInspector && (
          <button type="button" className="inspector-toggle" aria-haspopup="dialog" onClick={onOpenInspector}>
            <Icon icon="panel-stats" size={14} aria-hidden />
            Inspector
          </button>
        )}
        {/* Stub: the Report section holds the real export action. */}
        <button type="button" className="primary-action" onClick={() => navigate("/report")}>
          Export report
        </button>
      </div>
    </header>
  );
}

function ServerStatus() {
  const health = useServerHealth();
  const label = { checking: "Connecting…", connected: apiHost, disconnected: "Disconnected" }[health];

  return (
    <span role="status" className="server-status" data-health={health} title="Local backend server">
      <span aria-hidden>● </span>
      {label}
    </span>
  );
}

/** The running job's mode and percent complete; hidden when nothing is running. */
function JobPill() {
  const { job } = useCurrentJob();
  if (!isActive(job)) return null;
  const percent = Math.round(job.progress * 100);

  return (
    <span
      role="progressbar"
      aria-label="Job progress"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={percent}
      className="job-pill"
    >
      <span className="job-pill-mode">{job.mode}</span> {percent}%
    </span>
  );
}
