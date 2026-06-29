import { test, expect } from "@playwright/test";
import { uniqEmail, provisionUser, userCtx, createFolderApi } from "./helpers";

// Admin pages are gated by nginx BasicAuth; the browser context supplies it.
test.use({ httpCredentials: { username: "admin", password: "123" } });

test("admin cycle: every capability at least once", async ({ page }) => {
  const email = uniqEmail("adm");

  // 1) create user via the admin UI (Users tab)
  await page.goto("/admin");
  await page.getByRole("tab", { name: /Users/i }).click();
  await page.getByRole("button", { name: /New user/i }).click();
  await page.locator('input[type=email]').fill(email);
  await page.locator(".nform input").nth(1).fill("E2E Person");
  await page.getByRole("button", { name: /Create user/i }).click();

  // appears in the list
  const row = page.locator(".urow", { hasText: email });
  await expect(row).toBeVisible();

  // 2) open user detail
  await row.click();
  await expect(page.getByRole("heading", { name: "E2E Person" })).toBeVisible();

  // 3) edit bio/locale/active and save
  await page.locator(".ta").fill("Updated by e2e");
  await page.getByRole("button", { name: /^Save$/ }).first().click();

  // 4) generate magic link
  await page.getByRole("button", { name: /Generate link/i }).click();
  await expect(page.locator(".linkbox")).toHaveValue(/\/login\?magic=/);

  // 5) set a password
  await page.locator('input[type=password]').fill("e2epass123");
  await page.getByRole("button", { name: /^Save$/ }).last().click();

  // 6) statistics tab
  await page.getByRole("tab", { name: /Statistics/i }).click();
  await expect(page.locator(".stat").first()).toBeVisible();

  // 7) history tab
  await page.getByRole("tab", { name: /History/i }).click();
  await expect(page.locator(".pane")).toBeVisible();
});

test("admin can delete a user's node", async ({ page }) => {
  const u = await provisionUser("admdel", "Delete Target");
  const ctx = await userCtx(u.email, u.password);
  const folder = await createFolderApi(ctx, "ToBeDeleted");
  await ctx.dispose();

  await page.goto(`/admin/users/${u.id}`);
  await page.getByRole("tab", { name: /Statistics/i }).click();
  const node = page.locator(".node", { hasText: "ToBeDeleted" });
  await expect(node).toBeVisible();
  await node.locator("button.del").click();
  await expect(page.locator(".node", { hasText: "ToBeDeleted" })).toHaveCount(0);
  expect(folder.id).toBeTruthy();
});
