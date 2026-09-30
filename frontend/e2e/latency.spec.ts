import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

// The stub runner (see playwright.config.ts) has no weights file or execution provider, and sleeps a fixed time per
// call, so this checks what the section shows, not the numbers themselves.

const inspector = (page: Page) => page.getByRole("complementary", { name: "Inspector" });
const latency = (page: Page) => inspector(page).getByRole("region", { name: "Latency" });

async function runOnSyntheticSample(page: Page) {
  await page.goto("/synthetic");
  await page.getByLabel("Sample video").selectOption("synthetic-traffic");
  await page.getByRole("button", { name: "Start run" }).click();
  await expect(page.getByRole("region", { name: "Frame viewer" })).toBeVisible({ timeout: 15_000 });
}

test("a finished run shows its latency and the model and runtime that produced it", async ({ page }) => {
  await runOnSyntheticSample(page);

  await expect(latency(page)).toContainText("Stub detector · none (deterministic stub)");
  await expect(latency(page)).toContainText("not a real-time claim");
  const metrics = latency(page).getByRole("term");
  await expect(metrics).toHaveText(["Inference", "Effective fps", "Pre/post-processing", "Read", "Degrade", "Render"]);
  // The stub sleeps 50 ms a call, so inference can't read as zero.
  await expect(latency(page).getByRole("definition").first()).toContainText(/[1-9]\d*\.\d ms p50/);
  await expect(latency(page)).toContainText("the first 2 were warm-up and are left out");
});

test("the latency section has no accessibility violations", async ({ page }) => {
  await runOnSyntheticSample(page);
  await expect(latency(page)).toBeVisible();

  const results = await new AxeBuilder({ page })
    .include('[aria-label="Latency"]')
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  expect(results.violations).toEqual([]);
});
