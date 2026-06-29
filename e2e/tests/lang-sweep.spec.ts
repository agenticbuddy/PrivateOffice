import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { provisionUser } from "./helpers";

const here = path.dirname(fileURLToPath(import.meta.url));
// Separate from the HTML reporter folder (which is cleaned on each run).
const outDir = path.join(here, "..", "lang-sweep");

// The full selectable locale set (mirrors frontend i18n/locales.ts).
const LOCALES: { code: string; native: string; dir: "ltr" | "rtl" }[] = [
  { code: "en", native: "English", dir: "ltr" },
  { code: "es", native: "Español", dir: "ltr" },
  { code: "de", native: "Deutsch", dir: "ltr" },
  { code: "fr", native: "Français", dir: "ltr" },
  { code: "pt-BR", native: "Português (Brasil)", dir: "ltr" },
  { code: "ru", native: "Русский", dir: "ltr" },
  { code: "it", native: "Italiano", dir: "ltr" },
  { code: "nl", native: "Nederlands", dir: "ltr" },
  { code: "pl", native: "Polski", dir: "ltr" },
  { code: "uk", native: "Українська", dir: "ltr" },
  { code: "tr", native: "Türkçe", dir: "ltr" },
  { code: "cs", native: "Čeština", dir: "ltr" },
  { code: "zh-CN", native: "简体中文", dir: "ltr" },
  { code: "ja", native: "日本語", dir: "ltr" },
  { code: "ko", native: "한국어", dir: "ltr" },
  { code: "hi", native: "हिन्दी", dir: "ltr" },
  { code: "vi", native: "Tiếng Việt", dir: "ltr" },
  { code: "id", native: "Bahasa Indonesia", dir: "ltr" },
  { code: "th", native: "ไทย", dir: "ltr" },
  { code: "ar", native: "العربية", dir: "rtl" },
  { code: "he", native: "עברית", dir: "rtl" },
  { code: "fa", native: "فارسی", dir: "rtl" },
];

test("UI language sweep across 22 locales", async ({ page }) => {
  fs.mkdirSync(outDir, { recursive: true });
  const user = await provisionUser("sweep", "Sweep User", "test1234", "en");

  // login once
  await page.goto("/login");
  await page.locator("input[type=email]").fill(user.email);
  await page.locator("input[type=password]").fill(user.password);
  await page.locator("button[type=submit]").click();
  await expect(page).toHaveURL("/");

  // English baseline strings, to detect untranslated (fallback) catalogs.
  const baseline = await sample(page);
  const results: any[] = [];

  for (const loc of LOCALES) {
    await page.goto(`/?lang=${encodeURIComponent(loc.code)}`);
    await page.waitForSelector(".navlink", { timeout: 10_000 });
    const s = await sample(page);
    const metrics = await page.evaluate(() => ({
      lang: document.documentElement.lang,
      dir: document.documentElement.dir,
      overflow: document.documentElement.scrollWidth > window.innerWidth + 2,
    }));
    const translated = loc.code === "en" ? true : s.newDoc !== baseline.newDoc;
    results.push({
      code: loc.code,
      native: loc.native,
      expectedDir: loc.dir,
      actualDir: metrics.dir,
      lang: metrics.lang,
      translated,
      horizontalOverflow: metrics.overflow,
      sampleNav: s.nav,
      sampleNewDoc: s.newDoc,
    });
    await page.screenshot({ path: path.join(outDir, `${loc.code}.png`) });

    // hard assertions: page renders and direction is correct
    expect(metrics.dir).toBe(loc.dir);
    expect(metrics.overflow, `horizontal overflow in ${loc.code}`).toBeFalsy();
  }

  fs.writeFileSync(
    path.join(outDir, "lang-report.json"),
    JSON.stringify(results, null, 2),
  );

  const translatedCount = results.filter((r) => r.translated).length;
  expect(translatedCount).toBeGreaterThanOrEqual(20);
});

async function sample(page: import("@playwright/test").Page) {
  // The "New document" primary button text is locale-specific; use it to detect
  // whether a catalog is translated vs falling back to English.
  return {
    nav: (await page.locator(".navlink").first().textContent())?.trim() ?? "",
    newDoc: (await page.locator(".actions .v-primary").first().textContent())?.trim() ?? "",
  };
}
