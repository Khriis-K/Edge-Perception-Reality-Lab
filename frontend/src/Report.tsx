import { Button, Checkbox, Tab, Tabs } from "@blueprintjs/core";
import { useState, type ReactNode } from "react";
import { exportFileUrl, type ExportFileName, type ExportSummary } from "./api/client";
import { RunPicker } from "./Findings";
import { useFindings } from "./FindingsData";
import { Row } from "./FindingsInspector";
import { EXPORT_FILES, useReport } from "./ReportData";
import { alwaysIncluded, byteSize, exportMeta } from "./reportFormat";
import { formatBytes } from "./runHistoryFormat";

/** The work area's tabs: the HTML report as it will look, then the JSON and CSV it is written with. */
export function ReportWorkArea() {
  return (
    <Tabs id="work-tabs" className="tab-strip" animate={false}>
      {EXPORT_FILES.map((name) => (
        <Tab key={name} id={name} title={name} panel={<PreviewPanel name={name} />} />
      ))}
    </Tabs>
  );
}

function PreviewPanel({ name }: { name: ExportFileName }) {
  const { runs, findings, error } = useFindings();
  const { preview, previewError } = useReport();
  let body: ReactNode;
  if (error || previewError) body = <p role="alert" className="run-error">{error ?? previewError}</p>;
  else if (runs?.length === 0)
    body = <p className="empty-state">No finished runs yet. Run a benchmark, or a synthetic run on a video.</p>;
  else if (!findings || !preview) body = <p className="empty-state">Building the preview…</p>;
  else if (name === "report.html")
    // An opaque origin, so nothing in it can reach the app. The report has no scripts (backend/report_html.py), but the
    // sandbox allows them: with none allowed, browser tools (axe, devtools) can't run in the frame either.
    body = <iframe title="Report preview" className="report-frame" sandbox="allow-scripts" srcDoc={preview[name]} />;
  else
    body = (
      <pre aria-label={`${name} preview`} className="report-data" tabIndex={0}>
        {preview[name]}
      </pre>
    );
  return (
    <div className="work-body report">
      <h1>Report</h1>
      {runs && runs.length > 0 && <RunPicker />}
      {body}
    </div>
  );
}

/** Report's explorer: previous exports, newest first. Selecting one shows it in the inspector. */
export function ReportExplorer({ empty }: { empty: string }) {
  const { exports, exportsError, selectedId, select } = useReport();
  let list: ReactNode;
  if (exportsError) list = <p role="alert" className="empty-state">{exportsError}</p>;
  else if (!exports) list = <p className="empty-state">Loading exports…</p>;
  else if (!exports.length) list = <p className="empty-state">{empty}</p>;
  else
    list = (
      <ul aria-label="Exports" className="run-list">
        {exports.map((summary) => (
          <li key={summary.id}>
            <button
              type="button"
              className="run-item"
              aria-current={summary.id === selectedId ? "true" : undefined}
              onClick={() => select(summary.id === selectedId ? null : summary.id)}
            >
              <span>{summary.title}</span>
              <span className="run-meta">
                {new Date(summary.created_at).toLocaleString()} · {exportMeta(summary)}
              </span>
            </button>
          </li>
        ))}
      </ul>
    );
  return (
    <div className="run-explorer">
      <p className="run-group">exports/ · local only</p>
      {list}
    </div>
  );
}

/** Report's inspector: the selected export, if any, then the files to write, what is always in, and Export. */
export function ReportInspector() {
  const { exports, selectedId } = useReport();
  const selected = exports?.find((summary) => summary.id === selectedId) ?? null;
  return (
    <div className="degradation-inspector report-inspector">
      {selected && <SelectedExport summary={selected} />}
      <ExportForm />
    </div>
  );
}

function SelectedExport({ summary }: { summary: ExportSummary }) {
  const { select } = useReport();
  return (
    <section aria-label="Selected export">
      <div className="inspector-heading-row">
        <h3 className="inspector-heading">Selected export</h3>
        <Button aria-label="Close export details" icon="cross" variant="minimal" size="small" onClick={() => select(null)} />
      </div>
      <dl className="metrics">
        <Row name="Run">{summary.title}</Row>
        <Row name="Saved">{new Date(summary.created_at).toLocaleString()}</Row>
        {summary.display_threshold !== null && <Row name="Display threshold">{summary.display_threshold.toFixed(2)}</Row>}
        <Row name="Folder">
          <code>exports/{summary.id}</code>
        </Row>
      </dl>
      <ul aria-label="Saved files" className="report-files">
        {summary.files.map((file) => (
          <li key={file.name}>
            <a href={exportFileUrl(summary.id, file.name)} target="_blank" rel="noreferrer">
              {file.name}
            </a>{" "}
            <span className="run-meta">{formatBytes(file.size_bytes)}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function ExportForm() {
  const { findings } = useFindings();
  const { preview, chosen, choose, runExport } = useReport();
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit() {
    setBusy(true);
    setStatus("Exporting…");
    try {
      const saved = await runExport();
      setStatus(`Saved to exports/${saved.id}.`);
    } catch (e) {
      setStatus(`Not exported: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  if (!findings) return <p className="empty-state">Open a finished run to export its report.</p>;
  return (
    <section aria-label="Export">
      <h3 className="inspector-heading">Files</h3>
      {EXPORT_FILES.map((name) => (
        <Checkbox key={name} checked={chosen.includes(name)} onChange={(e) => choose(name, e.currentTarget.checked)}>
          {name}
          {preview && <span className="run-meta"> · {formatBytes(byteSize(preview[name]))}</span>}
        </Checkbox>
      ))}
      <h3 className="inspector-heading">Always included</h3>
      <ul aria-label="Always included" className="limitations">
        {alwaysIncluded(findings.kind).map((section) => (
          <li key={section}>{section}</li>
        ))}
      </ul>
      <p className="field-note">Headlines appear where you have written them in Findings; none are generated.</p>
      <Button intent="primary" disabled={busy || chosen.length === 0} onClick={submit}>
        Export
      </Button>
      <p role="status" className="field-note">
        {chosen.length === 0 ? "Choose at least one file." : status}
      </p>
    </section>
  );
}
