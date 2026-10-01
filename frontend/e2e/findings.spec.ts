import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { BENCHMARK_PORT } from "../playwright.config";

// Findings on the fixture dataset with the stub runner, on the Benchmark spec's server (it has a dataset of its own).
// Clear-day: the stub's car is a hit and its pedestrian a miss, mAP 0.50 over 2 objects. Fog-day: its one
// RidableVehicle is missed, mAP 0.00. The stub still finds the car through synthetic fog 0.6, so that drop is 0.
test.use({ baseURL: `http://127.0.0.1:${BENCHMARK_PORT}` });

const BENCHMARK_RUN = "Benchmark: seed 0, up to 300 frames per condition";
const explorer = (page: Page) => page.getByRole("complementary", { name: "Explorer" });
const inspector = (page: Page) => page.getByRole("complementary", { name: "Inspector" });
const finding = (page: Page, name: string) => page.getByRole("region", { name });
const simToReal = (page: Page) => finding(page, "Finding 01 · Sim-to-real");
const runPicker = (page: Page) => page.getByRole("combobox", { name: /^Run/ });

async function runBenchmark(page: Page) {
  await page.goto("/benchmark");
  await expect(page.getByText(/^Subset: seed 0, up to 300 frames per condition/)).toBeVisible();
  await page.getByRole("button", { name: "Run benchmark" }).click();
  await expect(explorer(page).getByRole("list", { name: "Conditions" }).getByRole("listitem")).toHaveCount(8, {
    timeout: 15_000,
  });
}

/** Other specs on this server may have finished runs since, so the run is picked by name, never assumed newest. */
async function openRun(page: Page, title: string | RegExp) {
  const option = runPicker(page).locator("option").filter({ hasText: title }).first();
  await expect(option).toBeAttached();
  await runPicker(page).selectOption((await option.getAttribute("value"))!);
}

async function openBenchmarkFindings(page: Page) {
  await runBenchmark(page);
  await page.getByRole("link", { name: "Findings", exact: true }).click();
  await openRun(page, BENCHMARK_RUN);
  await expect(simToReal(page)).toBeVisible();
}

test("a headline the user writes is saved with the run and is there after a reload", async ({ page }) => {
  await openBenchmarkFindings(page);
  const headline = simToReal(page).getByRole("textbox", { name: "Headline for Finding 01 · Sim-to-real" });
  // Nothing writes it for the user: on a fresh run the field is empty and asks for one.
  await expect(headline).toHaveValue("");
  await expect(headline).toHaveAttribute("placeholder", /headline from the results/);

  await headline.fill("Real fog costs the detector far more than synthetic fog does.");
  await simToReal(page).getByRole("button", { name: "Save headline" }).click();
  await expect(simToReal(page).getByRole("status")).toHaveText("Saved with the run.");

  await page.reload();
  await openRun(page, BENCHMARK_RUN);
  await expect(simToReal(page).getByRole("textbox", { name: "Headline for Finding 01 · Sim-to-real" })).toHaveValue(
    "Real fog costs the detector far more than synthetic fog does.",
  );
  await expect(explorer(page).getByRole("list", { name: "Outline" })).toContainText(
    "Real fog costs the detector far more than synthetic fog does.",
  );
});

test("finding 01 sets clear-day beside real fog by day, with counts and the caveat in view", async ({ page }) => {
  await openBenchmarkFindings(page);

  await expect(simToReal(page).getByRole("note")).toContainText("Distributional, not paired");
  await expect(simToReal(page).getByRole("note")).toContainText("Both sides are daytime");
  const numbers = simToReal(page).getByLabel("Headline numbers");
  await expect(numbers).toContainText("Clear · daymAP 0.50 2 objects, 1 frame");
  await expect(numbers).toContainText("Real fog · daymAP 0.00 · drop 0.50 1 object, 1 frame");
  await expect(simToReal(page).getByRole("img", { name: /Per-class AP drop/ })).toBeVisible();
  const car = simToReal(page)
    .getByRole("row")
    .filter({ has: page.getByRole("rowheader", { name: "PassengerCar", exact: true }) });
  // Fog-day has no cars: the real drop is undefined, not 0, and the counts say why.
  await expect(car.getByRole("cell").nth(0)).toHaveText("1.00 (1)");
  await expect(car.getByRole("cell").nth(2)).toHaveText("— (0)");
});

test("finding 02's heatmap keeps day and night apart and marks low-n cells", async ({ page }) => {
  await openBenchmarkFindings(page);
  const heatmap = finding(page, "Finding 02 · Where it fails").getByRole("table");

  await expect(heatmap.getByRole("rowheader")).toHaveText([
    /^Clear · day/,
    /^Clear · night/,
    /^Fog · day/,
    /^Fog · night/,
    /^Snow · day/,
    /^Snow · night/,
    /^Rain · day/,
    /^Rain · night/,
  ]);
  const clearDay = heatmap.getByRole("row").filter({ has: page.getByRole("rowheader", { name: /^Clear · day/ }) });
  await expect(clearDay.getByRole("cell").first()).toHaveText("1.00*1 obj");
  await expect(heatmap.locator("caption")).toContainText("* fewer than 30 objects (low n)");
  // The worst frames are ranked, each with its reason and its counts.
  const worst = finding(page, "Worst frames").getByRole("listitem");
  await expect(worst.first()).toContainText("2018-02-06_10-00-00_00400");
  await expect(worst.first()).toContainText("Snow · day · score 3");
  await expect(worst.first()).toContainText("1 miss · 1 false alarm · 1 confusion");
  // A dataset subset is not a continuous sequence: no reliability timeline.
  await expect(page.getByRole("img", { name: /Stability score for each/ })).toHaveCount(0);
});

test("the inspector shows the run record, latency and what to read first", async ({ page }) => {
  await openBenchmarkFindings(page);

  const readFirst = inspector(page).getByRole("region", { name: "Read this first" });
  await expect(readFirst).toContainText("distributional, not paired");
  await expect(readFirst.getByRole("link", { name: "Export as report" })).toBeVisible();
  const record = inspector(page).getByRole("region", { name: "Run record" });
  await expect(record).toContainText("8 frames · 10 objects");
  await expect(record).toContainText("seed 0, up to 300 per condition, vocabulary v1");
  await expect(record).toContainText("car → PassengerCar");
  await expect(record).toContainText("≥ 0.5, class-aware");
  const latency = inspector(page).getByRole("region", { name: "Latency" });
  await expect(latency.getByRole("term")).toHaveText(["Inference", "Effective fps", "Pre/post-processing", "Read"]);
  await expect(latency).toContainText("the first 2 were warm-up and are left out");

  const a11y = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  expect(a11y.violations).toEqual([]);
});

test("synthetic fog on the clear-day frames joins finding 01", async ({ page }) => {
  await runBenchmark(page);
  // Without reloading, so the Synthetic screen still knows the run's subset.
  await page.getByRole("link", { name: "Synthetic", exact: true }).click();
  const settings = inspector(page).getByRole("region", { name: "Degradation" });
  await settings.getByLabel("Type").selectOption("fog");
  await settings.getByLabel("Severity").fill("0.6");
  await page.getByText("Clear dataset frames").click();
  await page.getByRole("button", { name: "Start run" }).click();
  await expect(page.getByRole("region", { name: "Results on dataset frames" })).toBeVisible({ timeout: 15_000 });

  await page.getByRole("link", { name: "Findings", exact: true }).click();
  await openRun(page, BENCHMARK_RUN);

  await expect(simToReal(page).getByLabel("Headline numbers")).toContainText(
    "Synthetic fog 0.60mAP 0.50 · drop 0.00 2 objects, 1 frame",
  );
});

test("a video run shows its reliability timeline", async ({ page }) => {
  await page.goto("/synthetic");
  await page.getByLabel("Sample video").selectOption("synthetic-traffic");
  await page.getByRole("button", { name: "Start run" }).click();
  await expect(page.getByRole("region", { name: "Frame viewer" })).toBeVisible({ timeout: 30_000 });

  await page.getByRole("link", { name: "Findings", exact: true }).click();
  await openRun(page, /on Synthetic traffic/);

  const timeline = finding(page, "Finding 01 · Reliability timeline");
  await expect(timeline.getByRole("img", { name: /Stability score for each of 48 frames/ })).toBeVisible();
  await expect(timeline).toContainText("stability relative to the clean baseline, not accuracy");
  await expect(timeline.getByRole("textbox", { name: "Headline for Finding 01 · Reliability timeline" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Finding 01 · Sim-to-real" })).toHaveCount(0);
  await expect(inspector(page).getByRole("region", { name: "Read this first" })).toContainText("not accuracy");

  const a11y = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  expect(a11y.violations).toEqual([]);
});
