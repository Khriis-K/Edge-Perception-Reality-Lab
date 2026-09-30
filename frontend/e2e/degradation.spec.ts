import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

// The stub runner (see playwright.config.ts) finds the synthetic sample's bright car even through
// fog at 0.8, so both panes have labelled boxes. The default sample is the 300-frame Kraków clip,
// too slow under the stub, so these tests pick the synthetic one.

const inspector = (page: Page) => page.getByRole("complementary", { name: "Inspector" });
const settings = (page: Page) => inspector(page).getByRole("region", { name: "Degradation" });
const viewer = (page: Page) => page.getByRole("region", { name: "Frame viewer" });
const pane = (page: Page, name: "Clean" | "Degraded") => viewer(page).getByRole("figure", { name: `${name} frame` });
const boxes = (page: Page, name: "Clean" | "Degraded") =>
  pane(page, name).getByRole("list", { name: `${name} detections (model outputs)` }).getByRole("listitem");

async function configureFog(page: Page) {
  await page.goto("/synthetic");
  await settings(page).getByLabel("Type").selectOption("fog");
  await settings(page).getByLabel("Severity").fill("0.8");
  await settings(page).getByLabel("Seed").fill("42");
}

async function runOnSyntheticSample(page: Page) {
  await page.getByLabel("Sample video").selectOption("synthetic-traffic");
  await page.getByRole("button", { name: "Start run" }).click();
  await expect(viewer(page)).toBeVisible({ timeout: 15_000 });
}

test("the inspector offers the five degradations with severity, derived parameters and seed", async ({ page }) => {
  await page.goto("/synthetic");

  await expect(settings(page).getByLabel("Type").locator("option")).toHaveText([
    "Darkness",
    "Gaussian blur",
    "Synthetic fog",
    "Gaussian noise",
    "JPEG compression",
  ]);

  await configureFog(page);
  const parameters = settings(page).getByRole("definition");
  await expect(settings(page).getByText("0.80", { exact: true })).toBeVisible();
  await expect(settings(page).getByRole("term")).toHaveText(["transmission", "airlight"]);
  await expect(parameters).toHaveText(["0.280", "0.800"]);
  await expect(settings(page).getByLabel("Seed")).toHaveValue("42");

  // Parameters follow the choice, straight from the server's derivation.
  await settings(page).getByLabel("Type").selectOption("jpeg");
  await settings(page).getByLabel("Severity").fill("1");
  await expect(settings(page).getByRole("term")).toHaveText(["quality"]);
  await expect(parameters).toHaveText(["5"]);
});

test("a fog run shows clean and degraded panes on the same frame while scrubbing", async ({ page }) => {
  await configureFog(page);
  const started = page.waitForRequest((r) => r.method() === "POST" && new URL(r.url()).pathname === "/api/jobs");
  await runOnSyntheticSample(page);

  // The run carries exactly the one degradation set in the inspector.
  expect((await started).postDataJSON()).toEqual({
    sample_id: "synthetic-traffic",
    degradation: { kind: "fog", severity: 0.8, seed: 42 },
  });
  await expect(pane(page, "Degraded")).toContainText("Degraded: fog, severity 0.80");

  for (const index of [0, 30, 47]) {
    await viewer(page).getByLabel("Frame", { exact: true }).fill(String(index));
    for (const [name, variant] of [
      ["Clean", "clean"],
      ["Degraded", "degraded"],
    ] as const) {
      await expect(pane(page, name)).toContainText(`frame ${index + 1}`);
      await expect(pane(page, name).getByRole("img")).toHaveAttribute("src", new RegExp(`/frames/${variant}/${index}$`));
    }
  }

  // Both images load at the video size, and fog really changed the degraded one.
  const brightness = (name: "Clean" | "Degraded") =>
    pane(page, name)
      .getByRole("img")
      .evaluate(async (img: HTMLImageElement) => {
        await img.decode();
        const canvas = document.createElement("canvas");
        [canvas.width, canvas.height] = [img.naturalWidth, img.naturalHeight];
        const context = canvas.getContext("2d")!;
        context.drawImage(img, 0, 0);
        const { data } = context.getImageData(0, 0, canvas.width, canvas.height);
        let sum = 0;
        for (let i = 0; i < data.length; i += 4) sum += data[i];
        return { width: img.naturalWidth, mean: sum / (data.length / 4) };
      });
  const [clean, degraded] = [await brightness("Clean"), await brightness("Degraded")];
  expect(clean.width).toBe(320);
  expect(degraded.width).toBe(320);
  expect(degraded.mean).toBeGreaterThan(clean.mean + 50); // fog lifts the dark road toward the airlight
});

test("the experiment records the degradation, its derived parameters and the seed", async ({ page }) => {
  await configureFog(page);
  const completed = page.waitForResponse((r) => /\/api\/experiments\/[^/]+$/.test(new URL(r.url()).pathname));
  await runOnSyntheticSample(page);

  const experiment = await (await completed).json();

  expect(experiment.degradation).toEqual({
    kind: "fog",
    severity: 0.8,
    seed: 42,
    parameters: { transmission: expect.closeTo(0.28, 6), airlight: 0.8 },
  });
});

test("every box in both panes carries a text label", async ({ page }) => {
  await configureFog(page);
  await runOnSyntheticSample(page);

  for (const name of ["Clean", "Degraded"] as const) {
    await expect(boxes(page, name)).toHaveText(["car 0.90", "person 0.30"]);
  }
});

test("metrics counted over too few detections are labelled low n", async ({ page }) => {
  // Darkness 0.5 dims the stub's bright car below what it detects: 96 clean detections, 0 degraded.
  await page.goto("/synthetic");
  await settings(page).getByLabel("Type").selectOption("darkness");
  await settings(page).getByLabel("Severity").fill("0.5");
  await runOnSyntheticSample(page);

  const metrics = inspector(page).getByRole("region", { name: "Stability" });
  const metric = (name: string) =>
    metrics.getByLabel("Clip stability").locator("div").filter({ has: page.getByText(name, { exact: true }) });
  await expect(metric("Retention rate")).toContainText("0 / 96 clean detections");
  await expect(metric("Retention rate")).not.toContainText("low n");
  await expect(metric("Class changes")).toContainText("of 96 clean detections");
  await expect(metric("Class changes")).not.toContainText("low n");
  await expect(metric("Introduced rate")).toContainText("low n");
  await expect(metric("Median confidence shift")).toContainText("low n");
  await expect(metrics).toContainText("counted over fewer than 30 detections (or retained pairs)");
  await expect(metrics).toContainText("consecutive frames of the same object are not independent evidence");
});

test("the side-by-side view and the inspector have no accessibility violations", async ({ page }) => {
  await configureFog(page);
  await runOnSyntheticSample(page);
  await expect(boxes(page, "Degraded")).toHaveCount(2);

  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();

  expect(results.violations).toEqual([]);
});
