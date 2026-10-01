import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { BENCHMARK_PORT } from "../playwright.config";

// The frame viewer, on the Benchmark fixture server (see playwright.config.ts). With the stub runner, snow-day's one
// frame has one of each error: the stub's car lands on a LargeVehicle (class confusion), its stray person is a false
// alarm, and the Pedestrian is missed. Clear-day has a hit; fog-night's person is forgiven by an Obstacle region.
test.use({ baseURL: `http://127.0.0.1:${BENCHMARK_PORT}` });

const SNOW_DAY = "2018-02-06_10-00-00_00400";
const CLEAR_DAY = "2018-02-03_10-00-00_00100";

const explorer = (page: Page) => page.getByRole("complementary", { name: "Explorer" });
const tree = (page: Page) => explorer(page).getByRole("list", { name: "Conditions" });
const conditionItem = (page: Page, name: string) => tree(page).getByRole("button", { name: new RegExp(`^${name}`) });
const overlays = (page: Page) => page.getByRole("group", { name: "Overlays" });
const overlay = (page: Page, name: string) => overlays(page).getByRole("button", { name, exact: true });
const inspector = (page: Page) => page.getByRole("complementary", { name: "Inspector" });
// Blueprint's switch indicator covers its checkbox, so click the label, as a user would.
const toggle = (page: Page, name: string) =>
  page.getByRole("toolbar", { name: "Overlay controls" }).getByText(name, { exact: true }).click();

async function openCondition(page: Page, name: string) {
  await page.goto("/benchmark");
  await expect(page.getByText(/^Subset: seed 0, up to 300 frames per condition/)).toBeVisible();
  await page.getByRole("button", { name: "Run benchmark" }).click();
  await expect(tree(page).getByRole("listitem")).toHaveCount(8, { timeout: 15_000 });
  await conditionItem(page, name).click();
}

test("a frame with a miss, a false alarm and a confusion shows each tag", async ({ page }) => {
  await openCondition(page, "Snow · day");

  // Expanded: its frames, worst first, with the score and its parts.
  await expect(conditionItem(page, "Snow · day")).toHaveAttribute("aria-expanded", "true");
  const frames = explorer(page).getByRole("list", { name: "Frames, worst first" });
  await expect(frames.getByRole("button")).toHaveText([
    new RegExp(`^${SNOW_DAY}score 3 · 1 miss · 1 false alarm · 1 confusion$`),
  ]);

  await expect(page.getByRole("img", { name: `Camera image of dataset frame ${SNOW_DAY}` })).toBeVisible();
  await expect(overlays(page).getByRole("button")).toHaveText([
    "CLASS ✕ · LargeVehicle",
    "MISS · Pedestrian",
    "CLASS ✕ · PassengerCar 0.90",
    "FALSE ALARM · Pedestrian 0.30",
  ]);

  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  expect(results.violations).toEqual([]);
});

test("hits, ignored predictions and ignore regions carry their tags too", async ({ page }) => {
  await openCondition(page, "Clear · day");
  await expect(overlay(page, "HIT · PassengerCar 0.90")).toBeVisible();
  await expect(overlay(page, "HIT · PassengerCar")).toBeVisible();

  await conditionItem(page, "Fog · night").click();
  await expect(overlay(page, "IGNORED · Pedestrian 0.30")).toBeVisible();
  await expect(overlay(page, "IGNORE REGION · Obstacle")).toBeVisible();
});

test("toggling layers and moving the threshold never fetch the frame again", async ({ page }) => {
  const frameRequests: string[] = [];
  page.on("request", (request) => {
    if (/\/frames\//.test(new URL(request.url()).pathname)) frameRequests.push(request.url());
  });
  await openCondition(page, "Snow · day");
  await expect(overlay(page, "FALSE ALARM · Pedestrian 0.30")).toBeVisible();
  const loaded = frameRequests.length;

  await page.getByRole("spinbutton", { name: "Display threshold" }).fill("0.5");
  await expect(overlay(page, "FALSE ALARM · Pedestrian 0.30")).toHaveCount(0);
  await expect(overlay(page, "CLASS ✕ · PassengerCar 0.90")).toBeVisible();

  await toggle(page, "Labels");
  await expect(overlay(page, "MISS · Pedestrian")).toHaveCount(0);
  await toggle(page, "Predictions");
  await expect(overlays(page).getByRole("button")).toHaveCount(0);
  await toggle(page, "Labels");
  await expect(overlay(page, "MISS · Pedestrian")).toBeVisible();

  expect(frameRequests).toHaveLength(loaded);
});

test("clicking a box shows it in the inspector", async ({ page }) => {
  await openCondition(page, "Snow · day");

  await overlay(page, "CLASS ✕ · PassengerCar 0.90").click();

  await expect(inspector(page).getByRole("heading", { name: "Selected: CLASS ✕" })).toBeVisible();
  await expect(inspector(page)).toContainText("LargeVehicle → PassengerCar");
  await expect(inspector(page)).toContainText("Confidence0.90");
  await expect(inspector(page)).toContainText("IoU1.00");
  await expect(inspector(page)).toContainText(`Label sourcethe dataset's label file for frame ${SNOW_DAY}: “LargeVehicle”`);
  await expect(inspector(page)).toContainText("Error weight1");
  // The frame's counts, and this condition's AP beside clear weather in the same light.
  await expect(inspector(page)).toContainText("Error score3 (1 miss · 1 false alarm · 1 confusion)");
  await expect(inspector(page).getByRole("heading", { name: "Per-class AP: Snow · day vs. Clear · day" })).toBeVisible();
  await expect(inspector(page)).toContainText("Pedestrian0.00 vs. 0.00 in clear weather");
  await expect(inspector(page).getByRole("link", { name: /Findings/ })).toHaveAttribute("href", "/findings");

  await overlay(page, "MISS · Pedestrian").click();
  await expect(inspector(page).getByRole("heading", { name: "Selected: MISS" })).toBeVisible();
  await expect(inspector(page)).toContainText("Pedestrian → nothing predicted");
});

test("the Frame table lists the condition's frames and opens one", async ({ page }) => {
  await openCondition(page, "Clear · day");
  const dock = page.getByRole("region", { name: "Dock" });
  await expect(dock.getByRole("tab", { name: "Frame table" })).toHaveAttribute("aria-selected", "true");

  const row = dock.getByRole("row").filter({ has: page.getByRole("rowheader", { name: CLEAR_DAY }) });
  await expect(row.getByRole("cell")).toHaveText(["1", "1", "1", "0", "0", "2"]);

  await conditionItem(page, "Snow · day").click();
  await dock.getByRole("button", { name: SNOW_DAY }).click();
  await expect(page.getByRole("img", { name: `Camera image of dataset frame ${SNOW_DAY}` })).toBeVisible();
  await dock.getByRole("button", { name: "Error score" }).click();
  await expect(dock.getByRole("columnheader", { name: /Error score/ })).toHaveAttribute("aria-sort", "ascending");
});

test("below 1280 px, clicking a box opens the inspector drawer", async ({ page }) => {
  await page.setViewportSize({ width: 1100, height: 900 });
  await openCondition(page, "Snow · day");

  await overlay(page, "MISS · Pedestrian").click();

  const drawer = page.getByRole("dialog", { name: "Inspector" });
  await expect(drawer).toBeVisible();
  await expect(drawer.getByRole("heading", { name: "Selected: MISS" })).toBeVisible();
});
