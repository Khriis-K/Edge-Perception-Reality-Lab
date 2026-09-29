import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const SECTIONS = [
  { id: "setup", label: "Setup" },
  { id: "benchmark", label: "Benchmark" },
  { id: "synthetic", label: "Synthetic" },
  { id: "findings", label: "Findings" },
  { id: "report", label: "Report" },
];

const rail = (page: Page) => page.getByRole("navigation", { name: "Sections" });
const breadcrumb = (page: Page) => page.getByRole("navigation", { name: "Breadcrumb" });
const serverStatus = (page: Page) => page.getByRole("status");

test("opens on Setup with a live connection to the local server", async ({ page, baseURL }) => {
  await page.goto("/");

  await expect(page).toHaveURL(/\/setup$/);
  await expect(serverStatus(page)).toContainText(new URL(baseURL!).host);
});

test("the rail navigates all five sections, updating the indicator and breadcrumb", async ({ page }) => {
  await page.goto("/");

  for (const section of SECTIONS) {
    await rail(page).getByRole("link", { name: section.label }).click();

    await expect(page).toHaveURL(new RegExp(`/${section.id}$`));
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(section.label);
    await expect(breadcrumb(page).locator('[aria-current="page"]')).toHaveText(section.id);

    // The active section is marked in the accessibility tree, and only that one.
    const current = rail(page).locator('[aria-current="page"]');
    await expect(current).toHaveCount(1);
    await expect(current).toHaveAccessibleName(section.label);
  }
});

test("a section URL loads directly, as a real link", async ({ page }) => {
  await page.goto("/findings");

  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Findings");
  await expect(rail(page).getByRole("link", { name: "Findings" })).toHaveAttribute("aria-current", "page");
});

test("the status pill shows disconnected when the backend is unreachable", async ({ page }) => {
  await page.route("**/api/health", (route) => route.abort());

  await page.goto("/setup");

  await expect(serverStatus(page)).toHaveText(/Disconnected/);
});

test("the status pill switches to disconnected when the backend goes down", async ({ page, baseURL }) => {
  await page.goto("/setup");
  await expect(serverStatus(page)).toContainText(new URL(baseURL!).host);

  await page.route("**/api/health", (route) => route.abort());

  await expect(serverStatus(page)).toHaveText(/Disconnected/, { timeout: 10_000 });
});

for (const section of SECTIONS) {
  test(`${section.label} has no accessibility violations`, async ({ page, baseURL }) => {
    await page.goto(`/${section.id}`);
    await expect(serverStatus(page)).toContainText(new URL(baseURL!).host);

    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();

    expect(results.violations).toEqual([]);
  });
}
