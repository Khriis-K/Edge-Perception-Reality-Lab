import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { BENCHMARK_PORT } from "../playwright.config";

// Synthetic degradation on the fixture dataset's clear frames, with the stub runner, on the Benchmark spec's server
// (it has a dataset of its own). The fixture's one clear-day frame holds a car the stub finds, even through fog, and a
// pedestrian it misses: mAP 0.50 clean and degraded, over 2 objects.
test.use({ baseURL: `http://127.0.0.1:${BENCHMARK_PORT}` });

const explorer = (page: Page) => page.getByRole("complementary", { name: "Explorer" });
const settings = (page: Page) =>
  page.getByRole("complementary", { name: "Inspector" }).getByRole("region", { name: "Degradation" });
const resultsView = (page: Page) => page.getByRole("region", { name: "Results on dataset frames" });
// The label wraps the select, so its name runs on into the chosen option.
const framesSelect = (page: Page) => page.getByRole("combobox", { name: /^Frames/ });

/** From the Synthetic screen, without reloading: a reload would forget the Benchmark run opened in this page. */
async function runFogOnClearFrames(page: Page) {
  await settings(page).getByLabel("Type").selectOption("fog");
  await settings(page).getByLabel("Severity").fill("0.6");
  // Blueprint draws its indicator over the input, so the label is what a user clicks.
  await page.getByText("Clear dataset frames").click();
  await expect(page.getByRole("radio", { name: "Clear dataset frames" })).toBeChecked();
  await expect(framesSelect(page)).toHaveValue("clear-day");
  await expect(framesSelect(page).locator("option")).toHaveText(["Clear · day (1 frame)", "Clear · night (1 frame)"]);
  await page.getByRole("button", { name: "Start run" }).click();
  await expect(resultsView(page)).toBeVisible({ timeout: 15_000 });
}

test("fog on the clear frames reports both stability and accuracy for clean and degraded", async ({ page }) => {
  await page.goto("/synthetic");
  await runFogOnClearFrames(page);

  const view = resultsView(page);
  await expect(view).toContainText("Synthetic fog 0.60 on Clear · day frames (1 frame), seed 0.");
  // Stability: the stub keeps both its car and the person beside it through fog.
  const stability = view.getByRole("definition").filter({ hasText: "clean detections kept their label" });
  await expect(stability).toContainText("100%");
  await expect(stability).toContainText("2 / 2");
  // Accuracy, clean and degraded, as Benchmark scores them.
  await expect(view.getByRole("table")).toHaveCount(2);
  await expect(view.getByRole("table").nth(0).locator("caption")).toContainText(
    "Clean Clear · day frames: mAP 0.50 over 1 frames.",
  );
  await expect(view.getByRole("table").nth(1).locator("caption")).toContainText(
    "Synthetic fog 0.60 on Clear · day frames: mAP 0.50 over 1 frames.",
  );

  // The run is listed in the Synthetic explorer under its frames.
  const group = explorer(page).getByRole("region", { name: "Clear · day frames" });
  await expect(group.getByRole("button", { name: /^fog, severity 0\.60, seed 0/ })).toBeVisible();

  const a11y = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  expect(a11y.violations).toEqual([]);
});

test("the degraded condition appears in the Benchmark condition tree beside the real ones", async ({ page }) => {
  await page.goto("/benchmark");
  await expect(page.getByText(/^Subset: seed 0, up to 300 frames per condition/)).toBeVisible();
  await page.getByRole("button", { name: "Run benchmark" }).click();
  const conditions = explorer(page).getByRole("list", { name: "Conditions", exact: true });
  await expect(conditions.getByRole("listitem")).toHaveCount(8, { timeout: 15_000 });

  await page.getByRole("link", { name: "Synthetic", exact: true }).click();
  await runFogOnClearFrames(page);
  await page.getByRole("link", { name: "Benchmark", exact: true }).click();

  const row = explorer(page)
    .getByRole("list", { name: "Synthetic degradations" })
    .getByRole("button", { name: /^Synthetic fog 0\.60/ });
  await expect(row).toContainText("Clear · day frames, seed 0 · mAP 0.50 · 2 objects · low n");
  await expect(conditions.getByRole("listitem")).toHaveCount(8);

  await row.click();
  await expect(row).toHaveAttribute("aria-current", "true");
  await expect(page.getByRole("table").locator("caption")).toContainText(
    "Synthetic fog 0.60 on Clear · day frames: mAP 0.50 over 1 frames.",
  );
});

test("changing the display threshold rescores precision and recall without re-running", async ({ page }) => {
  const starts: string[] = [];
  page.on("request", (request) => {
    if (request.method() === "POST" && new URL(request.url()).pathname.endsWith("/jobs")) starts.push(request.url());
  });
  await page.goto("/synthetic");
  await runFogOnClearFrames(page);
  const pedestrian = (table: number) =>
    resultsView(page)
      .getByRole("table")
      .nth(table)
      .getByRole("row")
      .filter({ has: page.getByRole("rowheader", { name: "Pedestrian", exact: true }) });

  const threshold = resultsView(page).getByRole("spinbutton", { name: "Display threshold" });
  await expect(threshold).toHaveValue("0.25");
  // The stub's person at 0.3 is shown, and it is a false alarm: precision 0.
  await expect(pedestrian(0).getByRole("cell")).toHaveText(["1", "1", "0.00", "0.00", "0.00", "low n"]);

  await threshold.fill("0.5");
  // Nothing is predicted at 0.5 in either variant, so precision is undefined, not zero. AP doesn't move.
  await expect(pedestrian(0).getByRole("cell")).toHaveText(["1", "1", "0.00", "—", "0.00", "low n"]);
  await expect(pedestrian(1).getByRole("cell")).toHaveText(["1", "1", "0.00", "—", "0.00", "low n"]);
  await expect(resultsView(page).getByRole("table").nth(0).locator("caption")).toContainText("confidence ≥ 0.50");
  expect(starts).toHaveLength(1);
});

test("running the same degradation again reuses the cached results", async ({ page }) => {
  await page.goto("/synthetic");
  await runFogOnClearFrames(page);
  await page.reload();

  await runFogOnClearFrames(page);

  await expect(page.getByText("Cached, results reused: 1 frames, nothing re-run.")).toBeVisible();
});
