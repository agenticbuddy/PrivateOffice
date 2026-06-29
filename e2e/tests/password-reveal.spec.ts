import { test, expect } from "@playwright/test";
import { provisionUser } from "./helpers";

test("password field can be revealed and hidden", async ({ page }) => {
  await page.goto("/login");
  const pwd = page.locator("input[autocomplete='current-password']");
  await pwd.fill("secret123");

  // starts masked
  await expect(pwd).toHaveAttribute("type", "password");

  // click the eye toggle -> revealed as plain text
  await page.locator(".reveal").click();
  await expect(pwd).toHaveAttribute("type", "text");
  await expect(pwd).toHaveValue("secret123");
  await page.screenshot({ path: "password-revealed.png" });

  // click again -> masked
  await page.locator(".reveal").click();
  await expect(pwd).toHaveAttribute("type", "password");
});

test("downloading a Cyrillic-named file keeps the name and extension", async ({ page }) => {
  const u = await provisionUser("dl", "Downloader", "test1234", "en");

  await page.goto("/login");
  await page.locator("input[type=email]").fill(u.email);
  await page.locator("input[autocomplete='current-password']").fill(u.password);
  await page.locator("button[type=submit]").click();
  await expect(page).toHaveURL("/");

  // create a Cyrillic-named spreadsheet (shares the page's session cookie)
  await page.request.post("/api/nodes/file", {
    data: { name: "Отчёт за июнь", format: "xlsx" },
  });
  await page.reload();

  const row = page.locator(".rowitem", { hasText: "Отчёт за июнь.xlsx" });
  await expect(row).toBeVisible();

  const dl = page.waitForEvent("download");
  await row.locator('button[title="Download"]').click();
  const file = await dl;
  expect(file.suggestedFilename()).toBe("Отчёт за июнь.xlsx");
});
