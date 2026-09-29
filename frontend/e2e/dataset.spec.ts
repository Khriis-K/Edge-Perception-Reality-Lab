import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { readFileSync, renameSync } from "node:fs";
import { join } from "node:path";
import { FIXTURE_DATASET, FIXTURE_PORT } from "../playwright.config";

const datasetPanel = (page: Page) => page.getByRole("region", { name: "Dataset" });
const subsetPanel = (page: Page) => page.getByRole("region", { name: "Subset" });
const conditionRow = (page: Page, name: string) =>
  subsetPanel(page).getByRole("row").filter({ has: page.getByRole("rowheader", { name, exact: true }) });
const part = (page: Page, name: RegExp) =>
  datasetPanel(page).getByRole("list", { name: "Required dataset parts" }).getByRole("listitem").filter({ hasText: name });

test.describe("with no dataset configured", () => {
  test("Setup explains how to set the folder, and there is no Browse button", async ({ page }) => {
    await page.goto("/setup");

    await expect(datasetPanel(page)).toContainText("--dataset");
    await expect(datasetPanel(page)).toContainText("Synthetic mode works without the dataset");
    await expect(page.getByRole("textbox", { name: "Dataset folder" })).toHaveValue("Not configured");
    await expect(page.getByRole("button", { name: /browse/i })).toHaveCount(0);
  });

  test("the subset table waits for a dataset", async ({ page }) => {
    await page.goto("/setup");

    await expect(subsetPanel(page)).toContainText(/needs a ready dataset/i);
    await expect(subsetPanel(page).getByRole("table")).toHaveCount(0);
  });

  test("the required parts and the parts to skip are listed", async ({ page }) => {
    await page.goto("/setup");

    await expect(part(page, /camera images/)).toContainText("Not checked");
    await expect(part(page, /Ground-truth labels/)).toBeVisible();
    await expect(part(page, /Environment metadata/)).toBeVisible();
    await expect(datasetPanel(page)).toContainText(/Lidar/);
    await expect(datasetPanel(page)).toContainText(/Radar/);
  });
});

test.describe("with the fixture dataset", () => {
  test.use({ baseURL: `http://127.0.0.1:${FIXTURE_PORT}` });

  test("shows the folder read-only and every part as present", async ({ page }) => {
    await page.goto("/setup");

    const folder = page.getByRole("textbox", { name: "Dataset folder" });
    await expect(folder).toHaveValue(/\.e2e-dataset$/);
    await expect(folder).not.toBeEditable();
    for (const name of [/camera images/, /Ground-truth labels/, /Environment metadata/]) {
      await expect(part(page, name)).toContainText("Present");
    }
    await expect(datasetPanel(page)).toContainText("All three required parts are present.");

    const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
    expect(results.violations).toEqual([]);
  });

  test("Re-check picks up a missing part without a restart", async ({ page }) => {
    const metadata = join(FIXTURE_DATASET, "labeltool_labels_refined");
    await page.goto("/setup");
    await expect(part(page, /Environment metadata/)).toContainText("Present");

    renameSync(metadata, `${metadata}.moved`);
    try {
      await page.getByRole("button", { name: "Re-check" }).click();

      await expect(part(page, /Environment metadata/)).toContainText("Missing");
      await expect(part(page, /Environment metadata/)).toContainText("labeltool_labels_refined");
      await expect(datasetPanel(page)).toContainText(/Missing: Environment metadata/);
    } finally {
      renameSync(`${metadata}.moved`, metadata);
    }

    await page.getByRole("button", { name: "Re-check" }).click();
    await expect(part(page, /Environment metadata/)).toContainText("Present");
  });

  test("the subset table shows frames, objects and low n per condition", async ({ page }) => {
    await page.goto("/setup");

    const table = subsetPanel(page).getByRole("table");
    await expect(table.getByRole("rowheader")).toHaveText([
      "Clear · day",
      "Clear · night",
      "Fog · day",
      "Fog · night",
      "Snow · day",
      "Snow · night",
      "Rain · day",
      "Rain · night",
    ]);
    // Clear by day: one frame with a car and a pedestrian; LargeVehicle is the first class with none.
    await expect(conditionRow(page, "Clear · day").getByRole("cell")).toHaveText([
      "1",
      "2",
      "LargeVehicle 0",
      "low n",
    ]);
    // Fog plus snow, twilight, and the malformed label line.
    await expect(subsetPanel(page)).toContainText("3 samples excluded");
    await expect(subsetPanel(page)).toContainText("fog with rain or snow: 1");

    const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
    expect(results.violations).toEqual([]);
  });

  test("the manifest downloads with the chosen seed and cap", async ({ page }) => {
    await page.goto("/setup");
    await subsetPanel(page).getByRole("spinbutton", { name: "Seed" }).fill("42");
    await subsetPanel(page).getByRole("spinbutton", { name: "Frames per condition" }).fill("5");
    await expect(subsetPanel(page)).toContainText("Seed 42, up to 5 frames per condition");

    const [download] = await Promise.all([
      page.waitForEvent("download"),
      subsetPanel(page).getByRole("link", { name: /Download manifest/ }).click(),
    ]);
    const manifest = JSON.parse(readFileSync(await download.path(), "utf8"));

    expect(manifest.seed).toBe(42);
    expect(manifest.cap).toBe(5);
    expect(manifest.vocabulary_version).toBe(1);
    expect(manifest.frames["fog-night"]).toEqual(["2018-02-04_21-00-00_00200"]);
  });
});
