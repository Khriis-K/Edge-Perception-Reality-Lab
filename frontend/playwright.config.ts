import { defineConfig } from "@playwright/test";
import { join, resolve } from "node:path";

const PORT = 8765;
export const FIXTURE_PORT = 8766;
// Generated fresh on every run by scripts/make_fixture_dataset.py; the real dataset is never used.
export const FIXTURE_DATASET = resolve(".e2e-dataset");
// The Benchmark spec gets its own server, dataset copy and cache: dataset.spec.ts briefly breaks the shared fixture
// dataset to test Re-check, and a benchmark started at that moment would find it not ready.
export const BENCHMARK_PORT = 8767;
const BENCHMARK_DATASET = resolve(".e2e-dataset-benchmark");
// join() gives backslashes on Windows, where the command runs under cmd.exe.
const python = process.platform === "win32" ? join(".venv", "Scripts", "python.exe") : join(".venv", "bin", "python");
// Each server gets a cache and an exports folder emptied on every run: finished runs are reused, so a leftover one
// would turn a test's run into an instant cache hit, and the developer's own cache/ and exports/ must never leak in.
const E2E_CACHE = resolve(".e2e-cache");
const E2E_EXPORTS = resolve(".e2e-exports");
const freshCache = (name: string) => {
  const [cache, exports] = [join(E2E_CACHE, name), join(E2E_EXPORTS, name)];
  return {
    clear: `${python} -c "import shutil; [shutil.rmtree(d, ignore_errors=True) for d in (r'${cache}', r'${exports}')]"`,
    flag: `--cache-dir "${cache}" --exports-dir "${exports}"`,
  };
};
const mainCache = freshCache("main");
const fixtureCache = freshCache("fixture");
const benchmarkCache = freshCache("benchmark");

// Drives a real browser against the built frontend served by the backend, as a reviewer would run it.
// `npm run test:e2e` builds first; the backend serves frontend/dist.
// The stub runner gives fixed detections on the sample video, so no weights are needed.
export default defineConfig({
  testDir: "e2e",
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    viewport: { width: 1440, height: 900 },
  },
  webServer: [
    {
      // No dataset configured: the out-of-the-box state.
      command: `${mainCache.clear} && ${python} -m backend --port ${PORT} --runner stub ${mainCache.flag}`,
      cwd: "..",
      url: `http://127.0.0.1:${PORT}/api/health`,
      reuseExistingServer: false,
      env: { EDGE_LAB_DATASET: "" }, // ignore a dataset configured on the developer's machine
    },
    {
      command: `${fixtureCache.clear} && ${python} scripts/make_fixture_dataset.py "${FIXTURE_DATASET}" && ${python} -m backend --port ${FIXTURE_PORT} --runner stub --dataset "${FIXTURE_DATASET}" ${fixtureCache.flag}`,
      cwd: "..",
      url: `http://127.0.0.1:${FIXTURE_PORT}/api/health`,
      reuseExistingServer: false,
    },
    {
      command: `${benchmarkCache.clear} && ${python} scripts/make_fixture_dataset.py "${BENCHMARK_DATASET}" && ${python} -m backend --port ${BENCHMARK_PORT} --runner stub --dataset "${BENCHMARK_DATASET}" ${benchmarkCache.flag}`,
      cwd: "..",
      url: `http://127.0.0.1:${BENCHMARK_PORT}/api/health`,
      reuseExistingServer: false,
    },
  ],
});
