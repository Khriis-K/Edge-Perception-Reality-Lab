import { Button, Drawer, Tab, Tabs } from "@blueprintjs/core";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { Navigate, useParams } from "react-router";
import { BenchmarkExplorer, BenchmarkRun } from "./Benchmark";
import { BenchmarkInspector } from "./BenchmarkInspector";
import { FrameTable } from "./FrameTable";
import { DatasetSetup } from "./DatasetSetup";
import { DegradationInspector } from "./DegradationSettings";
import { Rail } from "./Rail";
import { SetupExplorer, SyntheticExplorer } from "./RunHistory";
import { LatencyInspector } from "./Latency";
import { MatchTable, StabilityInspector } from "./Stability";
import { SyntheticRun } from "./SyntheticRun";
import { findSection, type Section } from "./sections";
import { TopBar } from "./TopBar";
import { useMediaQuery } from "./useMediaQuery";

// Desktop widths; below this the inspector becomes a drawer. Keep in step with styles.css.
const WIDE_LAYOUT = "(width >= 1280px)";

/** The one layout every screen lives in: top bar, rail, explorer, tabbed work area, inspector. */
export function Workbench() {
  const section = findSection(useParams().section);
  const wide = useMediaQuery(WIDE_LAYOUT);
  // Lives here, not in the drawer, so selecting something (#12, #19) can open the inspector too.
  const [inspectorOpen, setInspectorOpen] = useState(false);
  // The panel replaces the drawer when the window widens; without this it would reopen on narrowing.
  useEffect(() => {
    if (wide) setInspectorOpen(false);
  }, [wide]);
  if (!section) return <Navigate to="/setup" replace />;

  const inspector = <InspectorContent section={section} />;
  return (
    <div className="workbench">
      <TopBar section={section} onOpenInspector={wide ? undefined : () => setInspectorOpen(true)} />
      <Rail />
      <Explorer section={section} />
      {/* Selecting a box opens the drawer below 1280 px; at desktop width the panel is always there. */}
      <WorkArea section={section} onOpenInspector={() => setInspectorOpen(true)} />
      {section.id === "synthetic" && <Dock />}
      {section.id === "benchmark" && <BenchmarkDock />}
      {wide ? (
        <InspectorPanel>{inspector}</InspectorPanel>
      ) : (
        <InspectorDrawer isOpen={inspectorOpen} onClose={() => setInspectorOpen(false)}>
          {inspector}
        </InspectorDrawer>
      )}
    </div>
  );
}

function Explorer({ section }: { section: Section }) {
  return (
    <aside aria-label="Explorer" className="panel explorer">
      <h2 className="panel-header">{section.explorerTitle}</h2>
      {section.id === "setup" ? (
        <SetupExplorer empty={section.explorerEmpty} />
      ) : section.id === "synthetic" ? (
        <SyntheticExplorer empty={section.explorerEmpty} />
      ) : section.id === "benchmark" ? (
        <BenchmarkExplorer empty={section.explorerEmpty} />
      ) : (
        <p className="empty-state">{section.explorerEmpty}</p>
      )}
    </aside>
  );
}

function WorkArea({ section, onOpenInspector }: { section: Section; onOpenInspector: () => void }) {
  return (
    <main className="work-area">
      {/* Keyed by section so each section starts on its own tab set. */}
      {/* animate={false}: Blueprint's sliding indicator forces a transparent tab background. */}
      <Tabs id="work-tabs" key={section.id} className="tab-strip" animate={false}>
        <Tab id="overview" title={section.id} panel={<Overview section={section} onOpenInspector={onOpenInspector} />} />
      </Tabs>
    </main>
  );
}

/** Below the work area on screens that tabulate data. */
function Dock() {
  return (
    <section aria-label="Dock" className="dock">
      <h2 className="panel-header">Match table</h2>
      <div className="dock-body">
        <MatchTable />
      </div>
    </section>
  );
}

/** Benchmark's dock. The Job tab (#13) will sit beside the Frame table. */
function BenchmarkDock() {
  return (
    <section aria-label="Dock" className="dock">
      <Tabs id="benchmark-dock" className="tab-strip dock-tabs" animate={false}>
        <Tab
          id="frames"
          title="Frame table"
          panel={
            <div className="dock-body">
              <FrameTable />
            </div>
          }
        />
      </Tabs>
    </section>
  );
}

function Overview({ section, onOpenInspector }: { section: Section; onOpenInspector: () => void }) {
  return (
    <div className="work-body">
      <h1>{section.label}</h1>
      {section.id === "synthetic" ? (
        <SyntheticRun />
      ) : section.id === "setup" ? (
        <DatasetSetup />
      ) : section.id === "benchmark" ? (
        <BenchmarkRun onOpenInspector={onOpenInspector} />
      ) : (
        <p className="empty-state">Nothing here yet.</p>
      )}
    </div>
  );
}

/** What the inspector shows; rendered once, inside either the panel or the drawer. */
function InspectorContent({ section }: { section: Section }) {
  if (section.id === "synthetic")
    return (
      <>
        <DegradationInspector />
        <StabilityInspector />
        <LatencyInspector />
      </>
    );
  if (section.id === "benchmark") return <BenchmarkInspector />;
  return <p className="empty-state">Select something to see its details.</p>;
}

function InspectorPanel({ children }: { children: ReactNode }) {
  return (
    <aside aria-label="Inspector" className="panel inspector">
      <h2 className="panel-header">Inspector</h2>
      {children}
    </aside>
  );
}

/**
 * Blueprint's Drawer gives the focus trap, Escape, backdrop and focus return, but no dialog role or
 * name, and on open it focuses an empty trap element. So the content sits in our own labelled
 * dialog, which takes focus once the drawer has opened.
 */
function InspectorDrawer({ isOpen, onClose, children }: { isOpen: boolean; onClose: () => void; children: ReactNode }) {
  const dialog = useRef<HTMLDivElement>(null);

  return (
    <Drawer
      isOpen={isOpen}
      onClose={onClose}
      onOpened={() => dialog.current?.focus()}
      size={300}
      className="inspector-drawer"
    >
      <div ref={dialog} role="dialog" aria-modal="true" aria-labelledby="inspector-drawer-title" tabIndex={-1}>
        <div className="panel-header inspector-drawer-header">
          <h2 id="inspector-drawer-title">Inspector</h2>
          <Button aria-label="Close" icon="cross" variant="minimal" size="small" onClick={onClose} />
        </div>
        <div className="inspector-drawer-body">{children}</div>
      </div>
    </Drawer>
  );
}
