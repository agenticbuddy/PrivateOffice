import { test, expect } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { provisionUser } from "./helpers";

const here = path.dirname(fileURLToPath(import.meta.url));
const fx = (n: string) => path.join(here, "..", "fixtures", n);

test("user cycle: every capability at least once", async ({ page }) => {
  const alice = await provisionUser("alice", "Alice E2E", "test1234", "en");
  const bob = await provisionUser("bobby", "Bob Helper", "test1234", "en");

  // 1) login (password)
  await page.goto("/login");
  await page.locator("input[type=email]").fill(alice.email);
  await page.locator("input[type=password]").fill(alice.password);
  await page.locator("button[type=submit]").click();
  await expect(page).toHaveURL("/"); // Start landing
  await page.goto("/files");
  await expect(page.getByRole("heading", { name: /My files/i })).toBeVisible();

  // 2) create folder
  await page.getByRole("button", { name: /New folder/i }).click();
  await page.locator(".modal input").fill("Projects");
  await page.getByRole("button", { name: /^Create$/ }).click();
  await expect(page.locator(".rowitem", { hasText: "Projects" })).toBeVisible();

  // 3) create document (docx)
  await page.getByRole("button", { name: /New document/i }).click();
  await page.locator(".modal input").first().fill("MyDoc");
  await page.getByRole("button", { name: /^Create$/ }).click();
  await expect(page.locator(".rowitem", { hasText: "MyDoc" })).toBeVisible();

  // 4) upload a supported file (xlsx)
  await page.locator('input[type=file]').setInputFiles(fx("sample.xlsx"));
  await expect(page.locator(".rowitem", { hasText: "sample.xlsx" })).toBeVisible();

  // 5) upload an unsupported file -> rejected with a toast
  await page.locator('input[type=file]').setInputFiles(fx("bad.bin"));
  await expect(page.locator(".toast.tone-danger")).toBeVisible();
  await expect(page.locator(".rowitem", { hasText: "bad.bin" })).toHaveCount(0);

  // 6) share the folder with Bob (reader)
  const folderRow = page.locator(".rowitem", { hasText: "Projects" });
  await folderRow.locator('button[title="Share"]').click();
  // search by the unique email so the candidate list resolves to exactly one row
  await page.locator(".search").fill(bob.email);
  await page.locator(".result", { hasText: bob.email }).click();
  await expect(page.locator(".current .row", { hasText: bob.email })).toBeVisible();
  await page.locator(".drawer .x").click();

  // 7) open the document in the editor
  await page.locator(".rowitem", { hasText: "MyDoc" }).click();
  await expect(page).toHaveURL(/\/file\//);
  await expect(page.locator(".nm")).toContainText("MyDoc");
  const frame = page.frameLocator('iframe[name=coframe]');
  // CO is same-origin (proxied); it renders document tiles to <canvas>.
  await expect(frame.locator("canvas").first()).toBeVisible({ timeout: 60_000 });
  await page.screenshot({ path: "report-editor.png" });

  // back to files
  await page.getByRole("button", { name: /Back to files/i }).click();
  await expect(page).toHaveURL("/files");

  // 8) download a file
  const dl = page.waitForEvent("download");
  await page.locator(".rowitem", { hasText: "sample.xlsx" }).locator('button[title="Download"]').click();
  expect((await dl).suggestedFilename()).toContain("sample.xlsx");

  // 9) change interface language in profile (en -> de); language is the 2nd select
  //    (1st is the Appearance/design picker)
  await page.goto("/profile");
  await page.locator("select").nth(1).selectOption({ label: "Deutsch" });
  await expect(page.locator("html")).toHaveAttribute("lang", "de");

  // 10) delete a node (the folder)
  await page.goto("/files");
  const row = page.locator(".rowitem", { hasText: "Projects" });
  await row.locator("button.del").click();
  await page.locator(".modal").getByRole("button", { name: /löschen|Delete/i }).click();
  await expect(page.locator(".rowitem", { hasText: "Projects" })).toHaveCount(0);

  // 11) logout (user menu in the rail)
  await page.locator(".userbtn").click();
  await page.getByRole("button", { name: /Log out|Abmelden/i }).click();
  await expect(page).toHaveURL(/\/login/);
});
