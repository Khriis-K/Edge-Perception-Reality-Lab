import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { BENCHMARK_PORT } from "../playwright.config";

// The primary acceptance workflows, one per mode, each ending in an exported report. Both use the stub runner (see
// playwright.config.ts). Each run's settings are its own, so no other spec's run on the same server is reused, and
// the run is picked by name on the Report screen, never assumed newest.

const SNOW_DAY = "2018-02-06_10-00-00_00400";

const explorer = (page: Page) => page.getByRole("complementary", { name: "Explorer" });
const inspector = (page: Page) => page.getByRole("complementary", { name: "Inspector" });
const runPicker = (page: Page) => page.getByRole("combobox", { name: /^Run/ });
const preview = (page: Page) => page.frameLocator('iframe[title="Report preview"]');
const tab = (page: Page, name: string) => page.getByRole("tab", { name, exact: true });
const dataPreview = (page: Page, name: string) => page.getByLabel(`${name} preview`);

async function openRun(page: Page, title: string) {
  const option = runPicker(page).locator("option").filter({ hasText: title }).first();
  await expect(option).toBeAttached();
  await runPicker(page).selectOption((await option.getAttribute("value"))!);
}

/** From the top bar to a saved export of the open run: the preview, its JSON and CSV, then Export. */
async function exportReport(page: Page, title: string, finding: string) {
  await page.getByRole("button", { name: "Export report" }).click();
  await expect(page).toHaveURL(/\/report$/);
  await openRun(page, title);

  // The preview is the open run's report as Export will write it.
  await expect(preview(page).getByRole("heading", { level: 1 })).toHaveText(title);
  await expect(preview(page).getByRole("heading", { name: finding })).toBeVisible();
  await expect(preview(page).getByRole("heading", { name: "Citation" })).toBeVisible();
  await tab(page, "metrics.json").click();
  const metrics = JSON.parse((await dataPreview(page, "metrics.json").textContent())!);
  expect(metrics.export.title).toBe(title);
  await tab(page, "frames.csv").click();
  const csv = (await dataPreview(page, "frames.csv").textContent())!;

  const exportForm = inspector(page).getByRole("region", { name: "Export" });
  await expect(exportForm.getByRole("list", { name: "Always included" })).toContainText("Limitations");
  await exportForm.getByRole("button", { name: "Export", exact: true }).click();
  await expect(exportForm.getByRole("status")).toHaveText(/^Saved to exports\//);

  // The new export is listed and selected, with its files.
  const item = explorer(page).getByRole("list", { name: "Exports" }).getByRole("button", { name: title });
  await expect(item.first()).toHaveAttribute("aria-current", "true");
  const files = inspector(page).getByRole("region", { name: "Selected export" }).getByRole("list", { name: "Saved files" });
  await expect(files.getByRole("link")).toHaveText(["report.html", "metrics.json", "frames.csv"]);

  // The saved data is the data the preview showed: the same run, scored the same way.
  const saved = await page.request.get((await files.getByRole("link", { name: "frames.csv" }).getAttribute("href"))!);
  expect(await saved.text()).toBe(csv);
  const savedMetrics = await (await page.request.get((await files.getByRole("link", { name: "metrics.json" }).getAttribute("href"))!)).json();
  expect(savedMetrics.findings).toEqual(metrics.findings);
  expect(savedMetrics.results).toEqual(metrics.results);
  return { metrics, csv };
}

test.describe("Benchmark", () => {
  test.use({ baseURL: `http://127.0.0.1:${BENCHMARK_PORT}` });
  const TITLE = "Benchmark: seed 3, up to 5 frames per condition";

  test("fixture dataset → select conditions → run → inspect frame → export report", async ({ page }) => {
    // The subset: up to 5 frames of each condition, drawn with seed 3.
    await page.goto("/setup");
    await page.getByLabel("Seed", { exact: true }).fill("3");
    await page.getByLabel("Frames per condition").fill("5");
    await page.getByRole("link", { name: "Benchmark", exact: true }).click();
    await expect(page.getByText(/^Subset: seed 3, up to 5 frames per condition/)).toBeVisible();

    await page.getByRole("button", { name: "Run benchmark" }).click();
    const conditions = explorer(page).getByRole("list", { name: "Conditions" });
    await expect(conditions.getByRole("listitem")).toHaveCount(8, { timeout: 15_000 });

    // Inspect a frame: snow-day's one frame, and its missed pedestrian.
    await conditions.getByRole("button", { name: /^Snow · day/ }).click();
    await expect(page.getByRole("img", { name: `Camera image of dataset frame ${SNOW_DAY}` })).toBeVisible();
    await page.getByRole("group", { name: "Overlays" }).getByRole("button", { name: "MISS · Pedestrian" }).click();
    await expect(inspector(page).getByRole("heading", { name: "Selected: MISS" })).toBeVisible();

    const { metrics, csv } = await exportReport(page, TITLE, "Finding 01 · Sim-to-real");
    expect(metrics.export.display_threshold).toBe(0.25);
    expect(metrics.findings.record.manifest).toMatchObject({ seed: 3, cap: 5 });
    expect(csv.split(/\r?\n/)[0]).toBe("condition,synthetic_run,frame_id,score,hits,misses,false_alarms,class_confusions,ignored");
    // One of each error: score 3 = 1 miss + 1 false alarm + 1 class confusion.
    expect(csv).toContain(`snow-day,,${SNOW_DAY},3.0,0,1,1,1,0`);
  });

  test("an export writes only the files chosen, and the Report screen has no accessibility violations", async ({ page }) => {
    await page.goto("/benchmark");
    await expect(page.getByText(/^Subset: seed 0, up to 300 frames per condition/)).toBeVisible();
    await page.getByRole("button", { name: "Run benchmark" }).click();
    await expect(explorer(page).getByRole("list", { name: "Conditions" }).getByRole("listitem")).toHaveCount(8, {
      timeout: 15_000,
    });
    await page.getByRole("button", { name: "Export report" }).click();
    await openRun(page, "Benchmark: seed 0, up to 300 frames per condition");
    await expect(preview(page).getByRole("heading", { name: "Finding 01 · Sim-to-real" })).toBeVisible();

    const exportForm = inspector(page).getByRole("region", { name: "Export" });
    // Blueprint's checkbox indicator covers its input, so click the label, as a user would.
    const choice = (name: string) => exportForm.locator("label").filter({ hasText: name });
    await choice("metrics.json").click();
    await choice("frames.csv").click();
    await expect(exportForm.getByRole("checkbox", { checked: true })).toHaveCount(1);
    await exportForm.getByRole("button", { name: "Export", exact: true }).click();
    await expect(exportForm.getByRole("status")).toHaveText(/^Saved to exports\//);

    const files = inspector(page).getByRole("region", { name: "Selected export" }).getByRole("list", { name: "Saved files" });
    await expect(files.getByRole("link")).toHaveText(["report.html"]);
    // Still listed after a reload, though it has no metrics.json.
    await page.reload();
    const item = explorer(page).getByRole("list", { name: "Exports" }).getByRole("button", { name: /1 file/ });
    await expect(inspector(page).getByRole("region", { name: "Selected export" })).toHaveCount(0);
    // Selecting it shows its details in the inspector.
    await item.click();
    await expect(item).toHaveAttribute("aria-current", "true");
    await expect(files.getByRole("link")).toHaveText(["report.html"]);

    // The report in the preview is checked too.
    const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
    expect(results.violations).toEqual([]);
  });
});

test.describe("Synthetic", () => {
  const TITLE = "Synthetic fog 0.70 on Synthetic traffic (generated)";

  test("fixture video → configure one degradation → run → inspect comparison + metrics → export report", async ({
    page,
  }) => {
    await page.goto("/synthetic");
    const settings = inspector(page).getByRole("region", { name: "Degradation" });
    await settings.getByLabel("Type").selectOption("fog");
    await settings.getByLabel("Severity").fill("0.7");
    await settings.getByLabel("Seed").fill("7");
    await page.getByLabel("Sample video").selectOption("synthetic-traffic");
    await page.getByRole("button", { name: "Start run" }).click();

    // The comparison: clean and degraded side by side, each with its labelled boxes.
    const viewer = page.getByRole("region", { name: "Frame viewer" });
    await expect(viewer).toBeVisible({ timeout: 15_000 });
    await expect(viewer.getByRole("figure", { name: "Degraded frame" })).toContainText("Degraded: fog, severity 0.70");
    for (const name of ["Clean", "Degraded"]) {
      await expect(
        viewer.getByRole("figure", { name: `${name} frame` }).getByRole("list", { name: `${name} detections (model outputs)` }),
      ).toContainText("car 0.90");
    }
    // The metrics: the clip's stability against the clean run.
    await expect(inspector(page).getByRole("region", { name: "Stability" }).getByLabel("Clip stability")).toContainText(
      "Retention rate",
    );

    const { metrics, csv } = await exportReport(page, TITLE, "Finding 01 · Reliability timeline");
    expect(metrics.findings.record.degradation).toMatchObject({ kind: "fog", severity: 0.7, seed: 7 });
    const rows = csv.trim().split(/\r?\n/);
    expect(rows[0]).toBe("index,score,retained,dropped,introduced,class_changes,confidence_loss");
    expect(rows).toHaveLength(1 + 48);
  });
});
