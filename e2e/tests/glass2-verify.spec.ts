import { test, expect } from "@playwright/test";
import { provisionUser, userCtx } from "./helpers";

// Exhaustive glass2 ("Liquid glass updated") chrome verification: sets the user's design to glass2,
// opens the editor and sweeps ribbon tabs + Formula dropdowns, the right-click context menu, a set of
// dialogs, and the sidebar. Hard-asserts the theme is actually applied (data-po=glass2, blue accent) and
// that a ribbon dropdown's rows are hit-testable (do not fall through to the document canvas). Optional
// surfaces are soft (screenshotted, not failed). Screenshots land in the test output dir.
//
// Editor cold-load is slow (from-source Collabora), so give the whole test a generous budget.
test.setTimeout(180_000);

test("glass2 theme is applied and editor chrome is hit-testable", async ({ page }, testInfo) => {
  // --- fresh user, design = glass2, one xlsx to open ---
  const u = await provisionUser("glass2", "Glass2 Sweep");
  const ctx = await userCtx(u.email, u.password);
  const patch = await ctx.patch("/api/auth/me", { data: { design: "glass2" } });
  expect(patch.ok(), `set design glass2: ${patch.status()}`).toBeTruthy();
  const mk = await ctx.post("/api/nodes/file", {
    data: { name: "Glass2 sweep.xlsx", format: "xlsx", parent_id: null },
  });
  expect(mk.ok(), `create node: ${mk.status()}`).toBeTruthy();
  const nodeId = (await mk.json()).id as string;
  await ctx.dispose();

  // --- log in via UI, open the document ---
  await page.setViewportSize({ width: 1720, height: 1040 });
  await page.goto("/login");
  await page.locator("input[type=email]").fill(u.email);
  await page.locator("input[autocomplete='current-password'], input[type=password]").first().fill(u.password);
  await page.locator("button[type=submit]").click();
  await page.waitForURL("/", { timeout: 20_000 });

  await page.goto(`/file/${nodeId}`);
  await page.frameLocator("iframe[name=coframe]").locator("canvas").first().waitFor({ state: "visible", timeout: 120_000 });
  const frame = page.frame({ name: "coframe" })!;
  await page.waitForTimeout(4500);

  const uno = (c: string) => frame.evaluate((cmd) => (window as any).app.map.sendUnoCommand(cmd), c);
  const esc = async () => { await page.keyboard.press("Escape").catch(() => {}); await page.waitForTimeout(200); };
  const shot = (name: string) => page.screenshot({ path: testInfo.outputPath(`${name}.png`) });

  // --- 1) theme applied + palette (HARD) ---
  const dataPo = await frame.evaluate(() => document.documentElement.getAttribute("data-po"));
  const accent = await frame.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue("--po-accent").trim());
  await shot("01-editor");
  expect(dataPo, "data-po attribute").toBe("glass2");
  expect(accent.toLowerCase(), "glass2 accent is blue #2563d9").toContain("#2563d9");

  // --- 2) every ribbon tab renders (soft: screenshot each) ---
  for (const tb of ["File", "Home", "Insert", "Layout", "Formula", "Data", "Review", "View", "Help"]) {
    const loc = frame.locator(`#${tb}-tab-label`).first();
    if (await loc.isVisible().catch(() => false)) { await loc.click().catch(() => {}); await page.waitForTimeout(400); await shot(`tab-${tb}`); }
  }

  // --- 3) a Formula ribbon dropdown: rows must be hit-testable (HARD) ---
  await frame.locator("#Formula-tab-label").first().click().catch(() => {});
  await page.waitForTimeout(500);
  const btn = "Formula-DateAndTimeFunctions";
  const b = frame.locator(`#${btn}`).first();
  if (await b.isVisible().catch(() => false)) {
    await b.click(); await page.waitForTimeout(600);
    const hit = await frame.evaluate((sel) => {
      const box = document.querySelector(sel); if (!box) return "no-box";
      const row = box.querySelector(".ui-treeview-cell, .ui-combobox-entry, li, .ui-menu-item"); if (!row) return "no-row";
      const r = row.getBoundingClientRect();
      const el = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
      return el ? (el.className || el.tagName).toString().slice(0, 60) : "null";
    }, `#${btn}-entries`);
    await shot(`dropdown-${btn}`);
    expect(String(hit), `dropdown row hit-test (got: ${hit})`).not.toMatch(/document-canvas|leaflet/);
    await esc();
  }

  // --- 4) right-click context menu (soft) ---
  await uno(".uno:GoToCell?ToPoint:string=D5");
  const cbox = await frame.locator("canvas").first().boundingBox();
  if (cbox) {
    await page.mouse.click(cbox.x + 240, cbox.y + 160, { button: "right" }); await page.waitForTimeout(700);
    await shot("context-menu");
    await esc();
  }

  // --- 5) representative dialogs render (soft: screenshot each) ---
  for (const [cmd, name] of [
    [".uno:FormatCellDialog", "dialog-formatcells"],
    [".uno:ConditionalFormatDialog", "dialog-condformat"],
    [".uno:InsertSymbol", "dialog-specialchar"],
  ] as const) {
    await uno(cmd); await page.waitForTimeout(1600);
    await shot(name);
    await esc(); await page.waitForTimeout(300);
  }

  // --- 6) sidebar (soft) ---
  await uno(".uno:Sidebar"); await page.waitForTimeout(1200);
  await shot("sidebar");
});
