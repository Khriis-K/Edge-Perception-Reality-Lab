import { Tab, Tabs } from "@blueprintjs/core";
import { Navigate, useParams } from "react-router";
import { DatasetSetup } from "./DatasetSetup";
import { Rail } from "./Rail";
import { SyntheticRun } from "./SyntheticRun";
import { findSection, type Section } from "./sections";
import { TopBar } from "./TopBar";

/** The one layout every screen lives in: top bar, rail, explorer, tabbed work area, inspector. */
export function Workbench() {
  const section = findSection(useParams().section);
  if (!section) return <Navigate to="/setup" replace />;

  return (
    <div className="workbench">
      <TopBar section={section} />
      <Rail />
      <Explorer section={section} />
      <WorkArea section={section} />
      <Inspector />
    </div>
  );
}

function Explorer({ section }: { section: Section }) {
  return (
    <aside aria-label="Explorer" className="panel explorer">
      <h2 className="panel-header">{section.explorerTitle}</h2>
      <p className="empty-state">{section.explorerEmpty}</p>
    </aside>
  );
}

function WorkArea({ section }: { section: Section }) {
  return (
    <main className="work-area">
      {/* Keyed by section so each section starts on its own tab set. */}
      {/* animate={false}: Blueprint's sliding indicator forces a transparent tab background. */}
      <Tabs id="work-tabs" key={section.id} className="tab-strip" animate={false}>
        <Tab id="overview" title={section.id} panel={<Overview section={section} />} />
      </Tabs>
    </main>
  );
}

function Overview({ section }: { section: Section }) {
  return (
    <div className="work-body">
      <h1>{section.label}</h1>
      {section.id === "synthetic" ? (
        <SyntheticRun />
      ) : section.id === "setup" ? (
        <DatasetSetup />
      ) : (
        <p className="empty-state">Nothing here yet.</p>
      )}
    </div>
  );
}

function Inspector() {
  return (
    <aside aria-label="Inspector" className="panel inspector">
      <h2 className="panel-header">Inspector</h2>
      <p className="empty-state">Select something to see its details.</p>
    </aside>
  );
}
