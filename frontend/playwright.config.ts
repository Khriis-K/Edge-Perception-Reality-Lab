import { defineConfig } from "@playwright/test";
import { join } from "node:path";

const PORT = 8765;
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
  webServer: {
    command: `${python} -m backend --port ${PORT}`,
    cwd: "..",
    url: `http://127.0.0.1:${PORT}/api/health`,
    reuseExistingServer: false,
  },
});
