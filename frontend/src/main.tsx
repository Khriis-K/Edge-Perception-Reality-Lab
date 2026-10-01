import "@blueprintjs/core/lib/css/blueprint.css";
import "@blueprintjs/icons/lib/css/blueprint-icons.css";
import "./styles.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router";
import { BenchmarkFrameProvider } from "./BenchmarkFrame";
import { BenchmarkResultsProvider } from "./BenchmarkResults";
import { CurrentJobProvider } from "./CurrentJob";
import { DegradationSettingsProvider } from "./DegradationSettings";
import { FindingsProvider } from "./FindingsData";
import { ReportProvider } from "./ReportData";
import { SubsetChoiceProvider } from "./SubsetChoice";
import { SyntheticResultsProvider } from "./SyntheticResults";
import { Workbench } from "./Workbench";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <CurrentJobProvider>
      <SyntheticResultsProvider>
        <BenchmarkResultsProvider>
          <BenchmarkFrameProvider>
            <FindingsProvider>
              <ReportProvider>
                <SubsetChoiceProvider>
                  <DegradationSettingsProvider>
                    <BrowserRouter>
                      <Routes>
                        <Route path="/:section" element={<Workbench />} />
                        <Route path="*" element={<Navigate to="/setup" replace />} />
                      </Routes>
                    </BrowserRouter>
                  </DegradationSettingsProvider>
                </SubsetChoiceProvider>
              </ReportProvider>
            </FindingsProvider>
          </BenchmarkFrameProvider>
        </BenchmarkResultsProvider>
      </SyntheticResultsProvider>
    </CurrentJobProvider>
  </StrictMode>,
);
