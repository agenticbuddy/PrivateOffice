// Diagnostic probe: discover the REAL DOM selectors of the live Collabora build
// before we extend the deep walk. We do not guess selectors for popups / menus /
// tooltips / sidebar / dialogs - we open each surface with real input (or the
// app's own command API) and report what actually appeared.
//
// Run: node e2e/scripts/probe-editor-dom.mjs   (stack must be up)
// Output: console summary + .qa/l10n/_probe.json
import { chromium, request } from "@playwright/test";
import fs from "node:fs";

const BASE_URL = process.env.BASE_URL || "http://localhost:8088";
const PASSWORD = "test1234";
const report = { steps: [] };
const log = (step, data) => { report.steps.push({ step, ...data }); console.log(`\n### ${step}`); console.log(JSON.stringify(data, null, 1)); };

// candidate containers we scan for after each action
const SCAN = [
  ".jsdialog-container", ".jsdialog-window", ".jsdialog.modalpopup", ".jsdialog",
  ".modalpopup", ".ui-dialog", ".lokdialog", ".vertical.cool-annotation",
  ".context-menu", ".context-menu-list", ".menu-entry", "[role=menu]", "ul.context-menu",
  "[role=tooltip]", ".ui-tooltip", ".leaflet-tooltip", ".hovertooltip", ".tooltip",
  "#sidebar-dock-wrapper", "#sidebar-panel", ".sidebar-panel", ".sidebar",
  ".notebookbar-popup", ".unotoolbutton", ".unoarrowsplit", "[aria-haspopup='true']",
  ".has-dropdown", ".menubutton", ".ui-pushbutton.menubutton", ".ui-listbox",
];

const scanFn = (selectors) => {
  const out = {};
  for (const sel of selectors) {
    let els = [];
    try { els = Array.from(document.querySelectorAll(sel)); } catch { continue; }
    const vis = els.filter((el) => {
      const s = getComputedStyle(el); const r = el.getBoundingClientRect();
      return s.visibility !== "hidden" && s.display !== "none" && r.width > 0 && r.height > 0;
    });
    if (vis.length) {
      out[sel] = {
        total: els.length, visible: vis.length,
        sample: (vis[0].outerHTML || "").slice(0, 300),
        text: (vis[0].textContent || "").replace(/\s+/g, " ").trim().slice(0, 120),
      };
    }
  }
  return out;
};

const admin = await request.newContext({ baseURL: BASE_URL, httpCredentials: { username: "admin", password: "123" } });
const browser = await chromium.launch({ headless: true });
try {
  // provision + login (en for readable labels)
  const email = `probe.${Date.now()}@example.com`;
  const cr = await admin.post("/admin/api/users", { data: { email, full_name: "Probe", locale: "en" } });
  const user = await cr.json();
  await admin.post(`/admin/api/users/${user.id}/password`, { data: { password: PASSWORD } });
  const ctx = await browser.newContext({ viewport: { width: 1792, height: 1200 } });
  const page = await ctx.newPage();
  page.setDefaultTimeout(20000);
  await page.goto(`${BASE_URL}/login`);
  await page.locator("input[type=email]").fill(email);
  await page.locator("input[type=password]").fill(PASSWORD);
  await page.locator("button[type=submit]").click();
  await page.waitForURL(`${BASE_URL}/`, { timeout: 20000 });

  // create + open a calc file
  const fr = await page.request.post(`${BASE_URL}/api/nodes/file`, { data: { name: "probe-calc", format: "xlsx", parent_id: null } });
  const file = await fr.json();
  await page.goto(`${BASE_URL}/file/${file.id}`);
  await page.frameLocator("iframe[name=coframe]").locator("canvas").first().waitFor({ state: "visible", timeout: 90000 });
  const frame = page.frame({ name: "coframe" });
  await page.waitForTimeout(2500);

  // 1. globals + command API
  log("globals", await frame.evaluate(() => {
    const keys = Object.keys(window).filter((k) => /^(app|map|L|cool|Cool|_)/.test(k)).slice(0, 40);
    const hasSend = !!(window.app && window.app.map && typeof window.app.map.sendUnoCommand === "function");
    const hasMapSend = !!(window.map && typeof window.map.sendUnoCommand === "function");
    return { keys, app: typeof window.app, map: typeof window.map, L: typeof window.L, sendUno_app_map: hasSend, sendUno_map: hasMapSend };
  }));

  // 2. notebookbar openers in the Home tab
  log("ribbon-openers", await frame.evaluate(() => {
    const sel = "button[aria-haspopup='true'], .unoarrowsplit, .menubutton, [class*='arrow'][class*='uno'], .ui-pushbutton.menubutton";
    const els = Array.from(document.querySelectorAll(sel)).filter((el) => {
      const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0;
    });
    return { count: els.length, sample: els.slice(0, 12).map((el) => ({ id: el.id, cls: String(el.className).slice(0, 80), aria: el.getAttribute("aria-label"), haspopup: el.getAttribute("aria-haspopup") })) };
  }));

  // 3. open a ribbon dropdown with a REAL click, scan for popup
  try {
    const opener = frame.locator("button[aria-haspopup='true']:visible, .unoarrowsplit:visible, .menubutton:visible").first();
    await opener.click({ timeout: 8000 });
    await page.waitForTimeout(800);
    log("after-dropdown-click", await frame.evaluate(scanFn, SCAN));
    await page.keyboard.press("Escape").catch(() => {});
  } catch (e) { log("after-dropdown-click", { error: String(e).slice(0, 200) }); }

  // 4. hover a ribbon button, scan for tooltip
  try {
    await page.waitForTimeout(400);
    const btn = frame.locator(".unotoolbutton:visible, button.ui-content:visible").first();
    await btn.hover({ timeout: 8000 });
    await page.waitForTimeout(1500);
    log("after-hover", await frame.evaluate(scanFn, [".hovertooltip", "[role=tooltip]", ".ui-tooltip", ".leaflet-tooltip", ".tooltip", "#tooltip", ".jsdialog.hovertooltip"]));
  } catch (e) { log("after-hover", { error: String(e).slice(0, 200) }); }

  // 5. right-click canvas, scan for context menu
  try {
    await frame.locator("canvas").first().click({ button: "right", position: { x: 240, y: 220 }, timeout: 8000 });
    await page.waitForTimeout(800);
    log("after-rightclick", await frame.evaluate(scanFn, [".context-menu", ".context-menu-list", "ul.context-menu", "[role=menu]", ".menu-entry", ".jsdialog.modalpopup", ".modalpopup"]));
    await page.keyboard.press("Escape").catch(() => {});
  } catch (e) { log("after-rightclick", { error: String(e).slice(0, 200) }); }

  // 6. sidebar via UNO command
  try {
    await frame.evaluate(() => { (window.app?.map || window.map)?.sendUnoCommand(".uno:Sidebar"); });
    await page.waitForTimeout(1500);
    log("after-sidebar-uno", await frame.evaluate(scanFn, ["#sidebar-dock-wrapper", "#sidebar-panel", ".sidebar-panel", ".sidebar", "#sidebar-content-panel", ".ui-content.sidebar"]));
  } catch (e) { log("after-sidebar-uno", { error: String(e).slice(0, 200) }); }

  // 7. dialog via UNO command (Format Cells)
  try {
    await frame.evaluate(() => { (window.app?.map || window.map)?.sendUnoCommand(".uno:FormatCellDialog"); });
    await page.waitForTimeout(2000);
    const r = await frame.evaluate(scanFn, [".jsdialog-container", ".jsdialog-window", ".jsdialog.modalpopup", ".ui-dialog", ".lokdialog", ".jsdialog", "[role=dialog]", ".ui-dialog-title", ".ui-tab"]);
    log("after-dialog-uno", r);
    await page.keyboard.press("Escape").catch(() => {});
  } catch (e) { log("after-dialog-uno", { error: String(e).slice(0, 200) }); }

  await ctx.close();
} finally {
  await admin.dispose();
  await browser.close();
  fs.mkdirSync(".qa/l10n", { recursive: true });
  fs.writeFileSync(".qa/l10n/_probe.json", JSON.stringify(report, null, 1));
  console.log("\nprobe written to .qa/l10n/_probe.json");
}
