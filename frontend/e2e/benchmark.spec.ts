import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { BENCHMARK_PORT } from "../playwright.config";

// On the fixture dataset with the stub runner, on a server of this file's own (see playwright.config.ts). The stub
// finds the bright car the fixture draws in clear-day, fog-night and rain-night. In clear-night and snow-day the bright
// block is over a LargeVehicle, so the stub's car is a class confusion; everything else is missed.
test.use({ baseURL: `http://127.0.0.1:${BENCHMARK_PORT}` });

const explorer = (page: Page) => page.getByRole("complementary", { name: "Explorer" });
const tree = (page: Page) => explorer(page).getByRole("list", { name: "Conditions" });
const conditionItem = (page: Page, name: string) => tree(page).getByRole("button", { name: new RegExp(`^${name}`) });
const classRow = (page: Page, name: string) =>
  page.getByRole("table").getByRole("row").filter({ has: page.getByRole("rowheader", { name, exact: true }) });

async function runBenchmark(page: Page) {
  await page.goto("/benchmark");
  await expect(page.getByText(/^Subset: seed 0, up to 300 frames per condition/)).toBeVisible();
  await page.getByRole("button", { name: "Run benchmark" }).click();
  await expect(tree(page).getByRole("listitem")).toHaveCount(8, { timeout: 15_000 });
}

test("running a benchmark populates the condition tree with mAP, objects and low n", async ({ page }) => {
  await runBenchmark(page);

  await expect(tree(page).getByRole("button")).toHaveText([
    /^Clear · day/,
    /^Clear · night/,
    /^Fog · day/,
    /^Fog · night/,
    /^Snow · day/,
    /^Snow · night/,
    /^Rain · day/,
    /^Rain · night/,
  ]);
  await expect(conditionItem(page, "Clear · day")).toContainText("mAP 0.50 · 2 objects · low n");
  await expect(conditionItem(page, "Fog · night")).toContainText("mAP 1.00 · 1 object · low n");
  await expect(conditionItem(page, "Snow · day")).toContainText("mAP 0.00");
  await expect(explorer(page)).not.toContainText(/chamber/i);
  // The manifest and the model sit under the tree.
  await expect(explorer(page)).toContainText("Manifest: seed 0, up to 300 per condition, vocabulary v1");
  await expect(explorer(page)).toContainText("Stub detector fixture-1");

  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  expect(results.violations).toEqual([]);
});

test("changing the display threshold updates precision and recall without re-running", async ({ page }) => {
  const starts: string[] = [];
  page.on("request", (request) => {
    if (request.method() === "POST" && new URL(request.url()).pathname === "/api/benchmark/jobs") starts.push(request.url());
  });
  await runBenchmark(page);
  await conditionItem(page, "Clear · day").click();
  await expect(conditionItem(page, "Clear · day")).toHaveAttribute("aria-current", "true");

  const threshold = page.getByRole("spinbutton", { name: "Display threshold" });
  await threshold.fill("0.25");
  // The stub's person at 0.3 is shown, and it is a false alarm: precision 0.
  await expect(classRow(page, "Pedestrian").getByRole("cell")).toHaveText(["1", "1", "0.00", "0.00", "0.00", "low n"]);
  await expect(classRow(page, "PassengerCar").getByRole("cell")).toHaveText(["1", "1", "1.00", "1.00", "1.00", "low n"]);

  await threshold.fill("0.5");
  // Nothing is predicted at 0.5, so precision is undefined, not zero. AP doesn't move.
  await expect(classRow(page, "Pedestrian").getByRole("cell")).toHaveText(["1", "1", "0.00", "—", "0.00", "low n"]);
  expect(starts).toHaveLength(1);
});

test("running the same subset again reuses the cached results", async ({ page }) => {
  await runBenchmark(page);
  await page.reload();

  await page.getByRole("button", { name: "Run benchmark" }).click();

  await expect(page.getByText("Cached, results reused: 8 frames, nothing re-run.")).toBeVisible();
  await expect(tree(page).getByRole("listitem")).toHaveCount(8);
});

test("the benchmark runs the subset chosen in Setup", async ({ page }) => {
  await page.goto("/setup");
  await page.getByRole("spinbutton", { name: "Seed" }).fill("42");
  await page.getByRole("link", { name: "Benchmark" }).click();

  await expect(page.getByText(/^Subset: seed 42, up to 300 frames per condition/)).toBeVisible();
});

test("a saved manifest from another vocabulary version is refused in plain language", async ({ page }) => {
  await page.goto("/benchmark");
  const manifest = { seed: 0, cap: 300, vocabulary_version: 99, frames: { "clear-day": ["2018-02-03_10-00-00_00100"] } };

  await page.getByLabel("Run a saved manifest").setInputFiles({
    name: "old-manifest.json",
    mimeType: "application/json",
    buffer: Buffer.from(JSON.stringify(manifest)),
  });

  await expect(page.getByRole("alert")).toContainText("condition vocabulary version 99");
  await expect(page.getByRole("alert")).toContainText("Draw a new subset");
});
