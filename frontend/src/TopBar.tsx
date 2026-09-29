import { Icon } from "@blueprintjs/core";
import { useNavigate } from "react-router";
import { apiHost } from "./api/client";
import type { Section } from "./sections";
import { useServerHealth } from "./useServerHealth";

export function TopBar({ section }: { section: Section }) {
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
        {/* Job-progress pill goes here; hidden until a job is running (job dock ticket). */}
        {/* Placeholder until the command palette ticket. */}
        <button type="button" className="command-search" disabled>
          <span>Search frames, runs, commands</span>
          <kbd>Ctrl K</kbd>
        </button>
        <ServerStatus />
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
