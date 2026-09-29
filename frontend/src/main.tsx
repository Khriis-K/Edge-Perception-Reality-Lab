import "@blueprintjs/core/lib/css/blueprint.css";
import "@blueprintjs/icons/lib/css/blueprint-icons.css";
import "./styles.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router";
import { CurrentJobProvider } from "./CurrentJob";
import { DegradationSettingsProvider } from "./DegradationSettings";
import { Workbench } from "./Workbench";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <CurrentJobProvider>
      <DegradationSettingsProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/:section" element={<Workbench />} />
            <Route path="*" element={<Navigate to="/setup" replace />} />
          </Routes>
        </BrowserRouter>
      </DegradationSettingsProvider>
    </CurrentJobProvider>
  </StrictMode>,
);
