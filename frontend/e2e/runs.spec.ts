import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

// Finished runs are cached (the e2e servers start on an empty cache, see playwright.config.ts).
// Blur at 0.30 is run by no other spec, so these runs and cache hits are this file's own.

const explorer = (page: Page) => page.getByRole("complementary", { name: "Explorer" });
const settings = (page: Page) => page.getByRole("complementary", { name: "Inspector" }).getByRole("region", { name: "Degradation" });
const viewer = (page: Page) => page.getByRole("region", { name: "Frame viewer" });
const degradedPane = (page: Page) => viewer(page).getByRole("figure", { name: "Degraded frame" });
const pill = (page: Page) => page.getByRole("progressbar", { name: "Job progress" });
const runItem = (page: Page, seed: number) =>
  explorer(page).getByRole("button", { name: new RegExp(`^blur, severity 0\\.30, seed ${seed}\\b`) });

async function configure(page: Page, seed: number) {
  await settings(page).getByLabel("Type").selectOption("blur");
  await settings(page).getByLabel("Severity").fill("0.3");
  await settings(page).getByLabel("Seed").fill(String(seed));
  await page.getByLabel("Sample video").selectOption("synthetic-traffic");
}

async function run(page: Page, seed: number) {
  await page.goto("/synthetic");
  await configure(page, seed);
  await page.getByRole("button", { name: "Start run" }).click();
  await expect(viewer(page)).toBeVisible({ timeout: 15_000 });
}

/** Every POST that would start inference, from here on. */
function watchRunRequests(page: Page) {
  const posts: number[] = [];
  page.on("response", (response) => {
    const url = new URL(response.url());
    if (response.request().method() === "POST" && url.pathname === "/api/jobs") posts.push(response.status());
  });
  return posts;
}

test("an identical run reuses the cached results at once, and says so before and after", async ({ page }) => {
  await page.goto("/synthetic");
  await configure(page, 7);
  await expect(page.getByText("Will start a new job")).toBeVisible();
  await page.getByRole("button", { name: "Start run" }).click();
  await expect(viewer(page)).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText(/^Done: 48 frames/)).toBeVisible();

  // Same settings again: the form says the results will be reused, and they are, with no job to watch.
  await expect(page.getByText("Cached: the results will be reused")).toBeVisible();
  const posts = watchRunRequests(page);
  await page.getByRole("button", { name: "Start run" }).click();

  await expect(page.getByText("Cached, results reused: 48 frames, nothing re-run.")).toBeVisible();
  await expect(pill(page)).toBeHidden();
  await expect(degradedPane(page)).toContainText("Degraded: blur, severity 0.30");
  expect(posts).toEqual([200]); // 200, not 202: no job was started

  // A different seed is a different experiment.
  await settings(page).getByLabel("Seed").fill("70");
  await expect(page.getByText("Will start a new job")).toBeVisible();
});

test("the Synthetic explorer groups runs by input, and opening one does not re-run it", async ({ page }) => {
  await run(page, 8);
  await run(page, 9);
  const group = explorer(page).getByRole("region", { name: "Synthetic traffic (generated)" });
  await expect(group.getByRole("button", { name: /^blur, severity 0\.30, seed 8\b/ })).toBeVisible();
  await expect(group.getByRole("button", { name: /^blur, severity 0\.30, seed 9\b/ })).toBeVisible();
  await expect(runItem(page, 9)).toHaveAttribute("aria-current", "true");

  const posts = watchRunRequests(page);
  await runItem(page, 8).click();

  await expect(runItem(page, 8)).toHaveAttribute("aria-current", "true");
  await expect(runItem(page, 9)).not.toHaveAttribute("aria-current");
  await expect(degradedPane(page)).toContainText("Degraded: blur, severity 0.30");
  await expect(viewer(page).getByText("1 / 48")).toBeVisible();
  // The finished run's "Done" belongs to seed 9, not the run now open.
  await expect(page.getByText(/^Done:/)).toHaveCount(0);
  expect(posts).toEqual([]);
});

test("Setup lists the runs, a New run entry and the cache folder, and opens a run in Synthetic", async ({ page }) => {
  await run(page, 10);
  await page.getByRole("navigation", { name: "Sections" }).getByRole("link", { name: "Setup" }).click();

  await expect(explorer(page).getByRole("link", { name: "+ New run" })).toHaveAttribute("aria-current", "page");
  await expect(runItem(page, 10)).toContainText("Synthetic traffic (generated) · 48 frames");
  const footer = explorer(page).locator(".cache-info");
  await expect(footer).toContainText("Cache folder");
  await expect(footer.locator("code")).toContainText(".e2e-cache");
  await expect(footer).toContainText(/\d+(\.\d)? (kB|MB)/);

  const posts = watchRunRequests(page);
  await runItem(page, 10).click();

  await expect(page).toHaveURL(/\/synthetic$/);
  await expect(viewer(page)).toBeVisible();
  await expect(degradedPane(page)).toContainText("Degraded: blur, severity 0.30");
  expect(posts).toEqual([]);
});

test("the run history has no accessibility violations", async ({ page }) => {
  await run(page, 11);

  for (const section of ["setup", "synthetic"]) {
    await page.goto(`/${section}`);
    await expect(runItem(page, 11)).toBeVisible();
    const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
    expect(results.violations, section).toEqual([]);
  }
});
