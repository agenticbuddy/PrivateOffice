import { test, expect } from "@playwright/test";
import { adminCtx, uniqEmail } from "./helpers";

// BasicAuth for the /admin area is supplied by the context (no native dialog).
test.use({ httpCredentials: { username: "admin", password: "123" } });

const PASSWORD = "123456";

test("admin sets a user's password via UI, then that user logs in", async ({ page }) => {
  // fresh, password-less user (does not touch real accounts like vasya)
  const ctx = await adminCtx();
  const email = uniqEmail("setpw");
  const created = await (
    await ctx.post("/admin/api/users", {
      data: { email, full_name: "Set Pw", locale: "en" },
    })
  ).json();
  await ctx.dispose();

  // --- admin sets the password through the admin UI ---
  await page.goto(`/admin/users/${created.id}`);
  await page.locator('input[type=password]').fill(PASSWORD);
  await page.getByRole("button", { name: /^Save$/ }).last().click();
  await expect(page.locator(".toast")).toBeVisible();

  // --- that user logs in by password ---
  await page.goto("/login");
  await page.locator("input[type=email]").fill(email);
  await page.locator("input[autocomplete='current-password']").fill(PASSWORD);
  await page.locator("button[type=submit]").click();

  await expect(page).toHaveURL("/"); // Start landing
  await expect(page.getByRole("heading", { name: /Welcome back/i })).toBeVisible();
  await page.screenshot({ path: "scenario-setpw-loggedin.png" });
});

test("new user: magic-link login -> change own password -> login by password", async ({ page }) => {
  const email = uniqEmail("newbie");

  // --- admin creates the user and issues a passwordless link (UI) ---
  await page.goto("/admin");
  await page.getByRole("tab", { name: /Users/i }).click();
  await page.getByRole("button", { name: /New user/i }).click();
  await page.locator('input[type=email]').fill(email);
  await page.locator(".nform input").nth(1).fill("New Comer");
  await page.getByRole("button", { name: /Create user/i }).click();

  await page.locator(".urow", { hasText: email }).click();
  await page.getByRole("button", { name: /Generate link/i }).click();
  const magicUrl = await page.locator(".linkbox").inputValue();
  expect(magicUrl).toContain("/login?magic=");

  // --- new user opens the magic link and is signed in ---
  await page.goto(magicUrl);
  await expect(page).toHaveURL("/"); // Start landing
  await expect(page.getByRole("heading", { name: /Welcome back/i })).toBeVisible();

  // --- new user sets their own password in Profile ---
  await page.goto("/profile");
  await page.locator('input[type=password]').fill(PASSWORD);
  await page.getByRole("button", { name: /^Save|Speichern$/ }).last().click();
  await expect(page.locator(".toast")).toBeVisible();

  // --- log out ---
  await page.locator(".user").click();
  await page.getByRole("button", { name: /Log out|Abmelden/i }).click();
  await expect(page).toHaveURL(/\/login/);

  // --- log in by the freshly-set password ---
  await page.locator("input[type=email]").fill(email);
  await page.locator("input[type=password]").fill(PASSWORD);
  await page.locator("button[type=submit]").click();
  await expect(page).toHaveURL("/"); // Start landing
  await expect(page.getByRole("heading", { name: /Welcome back/i })).toBeVisible();
  await page.screenshot({ path: "scenario-newuser-loggedin.png" });
});
