import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import {
  exportReport,
  fetchExports,
  fetchReportPreview,
  type ExportFileName,
  type ExportSummary,
} from "./api/client";
import { useBenchmarkResults } from "./BenchmarkResults";
import { useFindings } from "./FindingsData";

export const EXPORT_FILES: ExportFileName[] = ["report.html", "metrics.json", "frames.csv"];

type Preview = Record<ExportFileName, string>;

interface ReportState {
  /** The open run's report files as an export would write them now; null while loading or with no run open. */
  preview: Preview | null;
  previewError: string | null;
  /** Previous exports, newest first; null until listed. */
  exports: ExportSummary[] | null;
  exportsError: string | null;
  selectedId: string | null;
  select: (exportId: string | null) => void;
  chosen: ExportFileName[];
  choose: (name: ExportFileName, on: boolean) => void;
  /** Saves the chosen files and selects the new export; rejects with the server's reason. */
  runExport: () => Promise<ExportSummary>;
}

const ReportContext = createContext<ReportState | null>(null);

/**
 * The Report screen's state, shared by the exports list, the preview and the inspector. The run is the one Findings
 * has open, at the Benchmark screen's display threshold: the preview is re-read whenever its findings are (another
 * run, threshold, finished job or saved headline), so it always shows what Export would write.
 */
export function ReportProvider({ children }: { children: ReactNode }) {
  const { findings } = useFindings();
  const { threshold } = useBenchmarkResults();
  const [preview, setPreview] = useState<Preview | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [exports, setExports] = useState<ExportSummary[] | null>(null);
  const [exportsError, setExportsError] = useState<string | null>(null);
  const [selectedId, select] = useState<string | null>(null);
  const [chosen, setChosen] = useState<ExportFileName[]>(EXPORT_FILES);

  useEffect(() => {
    setPreview(null);
    setPreviewError(null);
    if (!findings) return;
    const controller = new AbortController();
    Promise.all(EXPORT_FILES.map((name) => fetchReportPreview(findings.id, name, threshold, controller.signal)))
      .then(([html, json, csv]) => setPreview({ "report.html": html, "metrics.json": json, "frames.csv": csv }))
      .catch((e) => !controller.signal.aborted && setPreviewError(`Could not build the preview: ${(e as Error).message}`));
    return () => controller.abort();
  }, [findings, threshold]);

  useEffect(() => {
    const controller = new AbortController();
    fetchExports(controller.signal)
      .then(setExports)
      .catch((e) => !controller.signal.aborted && setExportsError(`Could not list the exports: ${(e as Error).message}`));
    return () => controller.abort();
  }, []);

  function choose(name: ExportFileName, on: boolean) {
    setChosen((current) => EXPORT_FILES.filter((file) => (file === name ? on : current.includes(file))));
  }

  async function runExport() {
    if (!findings) throw new Error("No run is open.");
    const saved = await exportReport(findings.id, threshold, chosen);
    setExports((current) => [saved, ...(current ?? [])]);
    select(saved.id);
    return saved;
  }

  return (
    <ReportContext.Provider
      value={{ preview, previewError, exports, exportsError, selectedId, select, chosen, choose, runExport }}
    >
      {children}
    </ReportContext.Provider>
  );
}

export function useReport(): ReportState {
  const value = useContext(ReportContext);
  if (!value) throw new Error("useReport needs a ReportProvider");
  return value;
}
