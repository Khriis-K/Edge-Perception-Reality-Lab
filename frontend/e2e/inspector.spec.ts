import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

// The workbench targets desktop widths of 1280 px and up; below that the inspector becomes a drawer.
const WIDE = { width: 1280, height: 900 };
const NARROW = { width: 1279, height: 900 };

const panel = (page: Page) => page.getByRole("complementary", { name: "Inspector" });
const drawer = (page: Page) => page.getByRole("dialog", { name: "Inspector" });
const toggle = (page: Page) => page.getByRole("button", { name: "Inspector", exact: true });
const workArea = (page: Page) => page.getByRole("main");

async function axeViolations(page: Page) {
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  return results.violations;
}

test.describe("at 1280 px and up", () => {
  test.use({ viewport: WIDE });

  test("the inspector is a fixed right panel, with no drawer toggle", async ({ page }) => {
    await page.goto("/setup");

    await expect(panel(page)).toBeVisible();
    await expect(panel(page)).toContainText("Select something to see its details.");
    const box = (await panel(page).boundingBox())!;
    expect(box.x + box.width).toBe(WIDE.width);
    await expect(toggle(page)).toHaveCount(0);
    await expect(drawer(page)).toHaveCount(0);
  });

  test("has no accessibility violations", async ({ page }) => {
    await page.goto("/setup");
    await expect(panel(page)).toBeVisible();

    expect(await axeViolations(page)).toEqual([]);
  });
});

test.describe("below 1280 px", () => {
  test.use({ viewport: NARROW });

  test("the inspector collapses, and the work area runs to the right edge", async ({ page }) => {
    await page.goto("/setup");

    await expect(toggle(page)).toBeVisible();
    await expect(panel(page)).toHaveCount(0);
    const box = (await workArea(page).boundingBox())!;
    expect(box.x + box.width).toBe(NARROW.width);
  });

  test("the toggle opens the inspector as a drawer over the work area, which keeps its width", async ({ page }) => {
    await page.goto("/setup");
    const before = (await workArea(page).boundingBox())!;

    await toggle(page).click();

    await expect(drawer(page)).toBeVisible();
    await expect(drawer(page)).toContainText("Select something to see its details.");
    expect(await workArea(page).boundingBox()).toEqual(before);
  });

  test("focus moves into the drawer, and Escape returns it to the toggle", async ({ page }) => {
    await page.goto("/setup");

    await toggle(page).focus();
    await page.keyboard.press("Enter");
    await expect(drawer(page)).toBeFocused();

    await page.keyboard.press("Escape");
    await expect(drawer(page)).toHaveCount(0);
    await expect(toggle(page)).toBeFocused();
  });

  test("the close button returns focus to the toggle", async ({ page }) => {
    await page.goto("/setup");
    await toggle(page).click();

    await drawer(page).getByRole("button", { name: "Close" }).click();

    await expect(drawer(page)).toHaveCount(0);
    await expect(toggle(page)).toBeFocused();
  });

  test("an open drawer closes when the window widens, and stays closed on narrowing again", async ({ page }) => {
    await page.goto("/setup");
    await toggle(page).click();
    await expect(drawer(page)).toBeFocused();

    await page.setViewportSize(WIDE);
    await expect(panel(page)).toBeVisible();
    await page.setViewportSize(NARROW);

    await expect(toggle(page)).toBeVisible();
    await expect(drawer(page)).toHaveCount(0);
  });

  test("Tab stays inside the open drawer", async ({ page }) => {
    await page.goto("/setup");
    await toggle(page).click();
    await expect(drawer(page)).toBeFocused();

    for (let i = 0; i < 4; i++) {
      await page.keyboard.press("Tab");
      const inside = await drawer(page).evaluate((el) => el.closest(".bp6-overlay")!.contains(document.activeElement));
      expect(inside).toBe(true);
    }
  });

  test("a drawer taller than the window scrolls its body, and the header stays put (#45)", async ({ page }) => {
    await page.setViewportSize({ width: NARROW.width, height: 400 });
    await page.goto("/synthetic");
    await page.getByLabel("Sample video").selectOption("synthetic-traffic");
    await page.getByRole("button", { name: "Start run" }).click();
    await expect(page.getByRole("region", { name: "Frame viewer" })).toBeVisible({ timeout: 15_000 });
    await toggle(page).click();
    await expect(drawer(page)).toBeFocused();

    const latency = drawer(page).getByRole("region", { name: "Latency" });
    const header = drawer(page).getByRole("heading", { name: "Inspector" });
    const viewportHeight = 400;
    expect((await latency.boundingBox())!.y).toBeGreaterThan(viewportHeight);

    await drawer(page).hover();
    await page.mouse.wheel(0, 5000);

    await expect(async () => {
      const box = (await latency.boundingBox())!;
      expect(box.y + box.height).toBeLessThanOrEqual(viewportHeight + 1); // sub-pixel rounding
    }).toPass();
    await expect(header).toBeInViewport();
  });

  test("has no accessibility violations, with the drawer closed or open", async ({ page }) => {
    await page.goto("/setup");
    await expect(toggle(page)).toBeVisible();
    expect(await axeViolations(page)).toEqual([]);

    await toggle(page).click();
    await expect(drawer(page)).toBeFocused();
    expect(await axeViolations(page)).toEqual([]);
  });
});
