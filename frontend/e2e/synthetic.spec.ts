import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

// The e2e server runs the deterministic stub runner (see playwright.config.ts): on the synthetic
// sample it reports a car (0.90) and a person (0.30) in all 48 frames, with the car moving right.
// These tests look at the clean pane; degradation.spec.ts covers the degraded one.

const pill = (page: Page) => page.getByRole("progressbar", { name: "Job progress" });
const viewer = (page: Page) => page.getByRole("region", { name: "Frame viewer" });
const cleanPane = (page: Page) => viewer(page).getByRole("figure", { name: "Clean frame" });
const detections = (page: Page) =>
  cleanPane(page).getByRole("list", { name: "Clean detections (model outputs)" }).getByRole("listitem");

/** With a seed, the run is one no other test makes: identical settings would reuse a cached run. */
async function startRun(page: Page, seed?: number) {
  await page.goto("/synthetic");
  // The real clip is preselected; these tests rely on the stub's fixed boxes on the synthetic one.
  await expect(page.getByLabel("Sample video")).toHaveValue("krakow-city-driving");
  if (seed !== undefined) await page.getByRole("region", { name: "Degradation" }).getByLabel("Seed").fill(String(seed));
  await page.getByLabel("Sample video").selectOption("synthetic-traffic");
  await page.getByRole("button", { name: "Start run" }).click();
}

async function runToCompletion(page: Page) {
  await startRun(page);
  await expect(viewer(page)).toBeVisible({ timeout: 15_000 });
}

test("runs detection on the sample video, showing progress, then scrubs frames with labelled boxes", async ({ page }) => {
  // A seed of its own: other specs run the default settings on this server, and a cached run shows no progress.
  await startRun(page, 902);

  // Progress: the pill names the mode and shows a percent part-way through.
  await expect(pill(page)).toContainText(/synthetic/i);
  await expect(pill(page)).toHaveAttribute("aria-valuenow", /^[1-9]\d?$/);
  await expect(pill(page)).toContainText(/\d+%/);

  // Complete: the pill goes away and the first frame appears with its boxes.
  await expect(viewer(page)).toBeVisible({ timeout: 15_000 });
  await expect(pill(page)).toBeHidden();
  await expect(detections(page)).toHaveCount(2);
  await expect(detections(page).filter({ hasText: "car 0.90" })).toHaveCount(1);
  await expect(detections(page).filter({ hasText: "person 0.30" })).toHaveCount(1);
  await expect(viewer(page).getByText("model outputs, not ground truth")).toBeVisible();

  const image = cleanPane(page).getByRole("img");
  await expect.poll(() => image.evaluate((img: HTMLImageElement) => img.naturalWidth)).toBe(320);
  const car = detections(page).filter({ hasText: "car" }).locator("rect");
  const firstX = await car.getAttribute("x");

  // Scrub to frame 31: a new image loads and the car's box has moved right.
  await viewer(page).getByLabel("Frame", { exact: true }).fill("30");

  await expect(viewer(page).getByText("31 / 48")).toBeVisible();
  await expect(image).toHaveAttribute("src", /\/frames\/clean\/30$/);
  await expect.poll(() => image.evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth)).toBe(320);
  await expect(car).not.toHaveAttribute("x", firstX!);
  const x = (value: string | null) => parseFloat(value ?? "");
  expect(x(await car.getAttribute("x"))).toBeGreaterThan(x(firstX));
});

test("threshold and overlay toggle change the view with no new inference request", async ({ page }) => {
  await runToCompletion(page);
  await expect(detections(page)).toHaveCount(2);

  const apiCalls: string[] = [];
  page.on("request", (request) => {
    const path = new URL(request.url()).pathname;
    if (path.startsWith("/api/") && path !== "/api/health") apiCalls.push(`${request.method()} ${path}`);
  });

  const threshold = viewer(page).getByLabel("Display threshold");
  await threshold.fill("0.5");
  await expect(detections(page)).toHaveCount(1);
  await expect(detections(page)).toHaveText("car 0.90");

  await threshold.fill("0.05");
  await expect(detections(page)).toHaveCount(2);

  await viewer(page).getByText("Show overlays").click();
  await expect(viewer(page).getByRole("list", { name: /detections/i })).toHaveCount(0);
  await expect(viewer(page).getByRole("img")).toHaveCount(2);
  await expect(cleanPane(page).getByRole("img")).toBeVisible();
  await expect(viewer(page).getByRole("figure", { name: "Degraded frame" }).getByRole("img")).toBeVisible();

  await viewer(page).getByText("Show overlays").click();
  await expect(detections(page)).toHaveCount(2);

  expect(apiCalls).toEqual([]);
});

test("cancel stops the run and shows no results", async ({ page }) => {
  // A run no other test makes: a cached one would complete at once, leaving nothing to cancel.
  await startRun(page, 901);
  await expect(pill(page)).toBeVisible();

  await page.getByRole("button", { name: "Cancel" }).click();

  await expect(page.getByText("Cancelled. Nothing was saved from this run.")).toBeVisible();
  await expect(pill(page)).toBeHidden();
  await expect(viewer(page)).toHaveCount(0);
});

test("the frame viewer has no accessibility violations", async ({ page }) => {
  await runToCompletion(page);
  await expect(detections(page)).toHaveCount(2);

  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();

  expect(results.violations).toEqual([]);
});
