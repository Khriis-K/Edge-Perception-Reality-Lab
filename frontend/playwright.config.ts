import { defineConfig } from "@playwright/test";
import { join, resolve } from "node:path";

const PORT = 8765;
export const FIXTURE_PORT = 8766;
// Generated fresh on every run by scripts/make_fixture_dataset.py; the real dataset is never used.
export const FIXTURE_DATASET = resolve(".e2e-dataset");
// join() gives backslashes on Windows, where the command runs under cmd.exe.
const python = process.platform === "win32" ? join(".venv", "Scripts", "python.exe") : join(".venv", "bin", "python");

// Drives a real browser against the built frontend served by the backend, as a reviewer would run it.
// `npm run test:e2e` builds first; the backend serves frontend/dist.
export default defineConfig({
  testDir: "e2e",
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    viewport: { width: 1440, height: 900 },
  },
  webServer: [
    {
      // No dataset configured: the out-of-the-box state.
      command: `${python} -m backend --port ${PORT}`,
      cwd: "..",
      url: `http://127.0.0.1:${PORT}/api/health`,
      reuseExistingServer: false,
      env: { EDGE_LAB_DATASET: "" }, // ignore a dataset configured on the developer's machine
    },
    {
      command: `${python} scripts/make_fixture_dataset.py "${FIXTURE_DATASET}" && ${python} -m backend --port ${FIXTURE_PORT} --dataset "${FIXTURE_DATASET}"`,
      cwd: "..",
      url: `http://127.0.0.1:${FIXTURE_PORT}/api/health`,
      reuseExistingServer: false,
    },
  ],
});
