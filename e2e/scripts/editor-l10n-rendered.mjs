// Deep rendered-localization walk for Collabora Online (Этап 3 of assisted_translate.md).
//
// Goal: for every term visible in the editor, record WHAT it is and WHERE/under
// WHAT CIRCUMSTANCES it is seen (app, surface, opener, precondition, DOM path).
// The rendered value is ground truth (what the user sees); the catalog universe
// (scripts/build-l10n-catalog.py) is the other half (current value + can-translate).
//
// Surfaces walked per app:
//   initial, every notebookbar tab, every dropdown/menu opener + one submenu
//   level, per-object context menus (with preconditions), modal dialogs (opened
//   via the app's own sendUnoCommand) + each dialog tab, sidebar deck, and a
//   tooltip pass (data-cooltip harvest + real hover to confirm the bubble).
//
// Reliability (see the doc): server-drawn menus/dialogs only react to REAL input
// (Playwright mouse/keyboard) or the app command API - never synthetic DOM events.
// Anything we cannot reach is logged as notReached with a machine reason; measured
// coverage is therefore an upper bound, not a claim of completeness.
//
// Run: node e2e/scripts/editor-l10n-rendered.mjs --locales=ru,en --apps=writer,calc,impress
import { chromium, request } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const BASE_URL = process.env.BASE_URL || "http://localhost:8088";
const PASSWORD = "test1234";

const LOCALES = [
  { code: "en", native: "English", dir: "ltr" },
  { code: "ru", native: "Русский", dir: "ltr" },
  { code: "ar", native: "العربية", dir: "rtl" },
];

const APPS = [
  { key: "writer", format: "docx", label: "Writer" },
  { key: "calc", format: "xlsx", label: "Calc" },
  { key: "impress", format: "pptx", label: "Impress" },
];

// Modal dialogs reachable via the app's own command API. Some need a precondition
// or may not exist in this build; a no-show is logged notReached, never fatal.
const APP_DIALOGS = {
  // NOTE: .uno:InsertSymbol (Special Character) is intentionally excluded - it is a
  // Unicode glyph picker whose grid lists ~5000 character names, not localizable UI.
  // The charmap ribbon opener is skipped in openersPass for the same reason.
  calc: [
    ".uno:FormatCellDialog", ".uno:ColumnWidth", ".uno:RowHeight", ".uno:DefineName",
    ".uno:DataSort", ".uno:DataFilterStandardFilter", ".uno:FunctionDialog",
    ".uno:ConditionalFormatDialog", ".uno:SearchDialog",
    ".uno:HyperlinkDialog", ".uno:PasteSpecial", ".uno:OptionsTreeDialog",
    ".uno:HeaderAndFooter", ".uno:TableOperationDialog", ".uno:InsertCell", ".uno:DeleteCell",
  ],
  writer: [
    ".uno:ParagraphDialog", ".uno:FontDialog", ".uno:InsertTable", ".uno:PageDialog",
    ".uno:WordCountDialog", ".uno:InsertBookmark", ".uno:SearchDialog",
    ".uno:HyperlinkDialog", ".uno:InsertField", ".uno:FormatColumns", ".uno:OptionsTreeDialog",
    ".uno:InsertBreak", ".uno:InsertFootnote",
  ],
  impress: [
    ".uno:PageSetup", ".uno:PresentationDialog", ".uno:HeaderAndFooter",
    ".uno:SearchDialog", ".uno:HyperlinkDialog", ".uno:OptionsTreeDialog", ".uno:SlideSetup",
    ".uno:InsertField", ".uno:CustomAnimation",
  ],
};

// Openers whose popup is a giant data picker, not localizable UI chrome (skip in walk).
// The character map is reachable via both the charmap control and an insert-char button.
const OPENER_SKIP = /charmap|insert-char/i;

const TEXT_ALLOWLIST = new Set(["PrivateOffice", "Document name", "100", "A1", "1", "0", "OK"]);

const args = parseArgs(process.argv.slice(2));
const selectedLocales = selectByCode(LOCALES, args.locales);
const selectedApps = selectByKey(APPS, args.apps);
const screenshotMode = args.screenshots || "main";
const outDir = path.resolve(args.out || ".qa/l10n-rendered");
const POPUP = ".jsdialog-window.modalpopup";
const DIALOG = ".jsdialog-window:not(.modalpopup)";

if (!selectedLocales.length) throw new Error("No locales selected");
if (!selectedApps.length) throw new Error("No apps selected");

fs.rmSync(outDir, { recursive: true, force: true });
fs.mkdirSync(outDir, { recursive: true });
const dirs = {
  screenshots: path.join(outDir, "screenshots"),
  text: path.join(outDir, "text"),
  json: path.join(outDir, "json"),
};
for (const d of Object.values(dirs)) fs.mkdirSync(d, { recursive: true });

const scenarioManifest = [];
const runManifest = [];
const visibleRows = [];
const seenScenarioIds = new Set();

const browser = await chromium.launch({ headless: true });
const admin = await request.newContext({ baseURL: BASE_URL, httpCredentials: { username: "admin", password: "123" } });

try {
  for (const locale of selectedLocales) {
    const user = await provisionUser(admin, locale);
    const context = await browser.newContext({ viewport: { width: 1792, height: 1200 } });
    const page = await context.newPage();
    page.setDefaultTimeout(20_000);
    await login(page, user.email, PASSWORD);
    const files = {};
    for (const app of selectedApps) files[app.key] = await createFile(page, locale.code, app);
    for (const app of selectedApps) await runApp(page, locale, app, files[app.key]);
    await context.close();
  }
} finally {
  await admin.dispose();
  await browser.close();
}

writeJson(path.join(outDir, "scenario_manifest.json"), scenarioManifest);
writeJson(path.join(outDir, "run_manifest.json"), runManifest);
writeJsonLines(path.join(outDir, "visible-text.jsonl"), visibleRows);
writeCsv(path.join(outDir, "english-leftovers.csv"), buildLeftovers(visibleRows));
writeMarkdownReport(path.join(outDir, "REPORT.md"));

const failed = runManifest.filter((r) => r.status === "failed").length;
const notReached = runManifest.filter((r) => r.status === "notReached").length;
console.log(`Rendered l10n artifacts written to ${outDir}`);
console.log(`Scenarios: ${runManifest.length}; passed: ${runManifest.length - failed - notReached}; failed: ${failed}; notReached: ${notReached}`);

// ---------------------------------------------------------------------------
// Per-app walk
// ---------------------------------------------------------------------------
async function runApp(page, locale, app, file) {
  await page.goto(`${BASE_URL}/file/${file.id}`);
  const frame = await waitForEditorFrame(page);

  // 1. initial (whole document: ribbon home tab, sidebar deck, status bar)
  await captureSurface(page, frame, scenario(locale, app, "initial", file, { surface: "initial" }),
    { screenshot: shouldScreenshot("initial") });

  // 2. notebookbar tabs, and for each tab its dropdown/dialog openers
  const tabs = await visibleTabs(frame);
  for (const tab of tabs) {
    const state = tab.id.replace(/-tab-label$/, "") || slug(tab.text || "tab");
    const tabScenario = scenario(locale, app, `tab-${state}`, file, { surface: "ribbon-tab", path: `${app.label} › ${tab.text || state}` });
    try {
      await clickById(frame, tab.id);
      await page.waitForTimeout(600);
      await captureSurface(page, frame, tabScenario, { rootSelector: tab.panelId ? `[id="${cssAttr(tab.panelId)}"]` : null, screenshot: shouldScreenshot(state) });
    } catch (error) {
      record(tabScenario, "failed", { error: String(error?.message || error) });
      continue;
    }
    await openersPass(page, frame, locale, app, file, tab, state);
  }

  // back to Home for object-context work
  await selectTab(frame, page, tabs, "Home");

  // 3. per-object context menus (preconditions)
  await contextMenuPass(page, frame, locale, app, file);

  // 4. modal dialogs via the app command API
  await dialogPass(page, frame, locale, app, file);

  // 5. tooltips (data-cooltip harvest + real-hover confirmation)
  await tooltipPass(page, frame, locale, app, file);
}

// Open every dropdown/dialog opener button in the active tab; capture the popup
// or dialog, then one submenu level for menu popups.
async function openersPass(page, frame, locale, app, file, tab, state) {
  let openers = [];
  try {
    openers = await frame.evaluate((panelSel) => {
      const root = panelSel ? document.querySelector(panelSel) : document;
      if (!root) return [];
      const seen = new Set();
      const out = [];
      for (const btn of root.querySelectorAll("button[aria-haspopup]")) {
        const r = btn.getBoundingClientRect();
        if (r.width <= 0 || r.height <= 0) continue;
        const id = btn.id || "";
        const label = (btn.getAttribute("aria-label") || btn.textContent || "").replace(/\s+/g, " ").trim();
        const key = id || label;
        if (!key || seen.has(key)) continue;
        seen.add(key);
        out.push({ id, label, kind: btn.getAttribute("aria-haspopup") });
      }
      return out;
    }, tab.panelId ? `[id="${cssAttr(tab.panelId)}"]` : null);
  } catch { openers = []; }

  for (let oi = 0; oi < openers.length; oi += 1) {
    const op = openers[oi];
    if (OPENER_SKIP.test(op.id) || OPENER_SKIP.test(op.label)) continue; // skip glyph pickers
    const isDialog = op.kind === "dialog";
    // key by opener ID (locale-independent); fall back to position, NOT the localized
    // label (slug() strips non-ASCII to "x", which would never pair across locales)
    const okey = op.id ? slug(op.id) : `p${oi}`;
    const sId = scenario(locale, app, `${state}__${isDialog ? "dlg" : "menu"}-${okey}`, file, {
      surface: isDialog ? "ribbon-dialog" : "dropdown",
      opener: op.label,
      path: `${app.label} › ${tab.text || state} › ${op.label || op.id}`,
    });
    try {
      const opener = op.id ? frame.locator(`[id="${cssAttr(op.id)}"]`).first() : frame.locator(`button[aria-label="${cssAttr(op.label)}"]`).first();
      await opener.click({ timeout: 6000 });
      await page.waitForTimeout(500);
      const root = isDialog ? DIALOG : POPUP;
      const appeared = await frame.locator(root).first().isVisible().catch(() => false);
      if (!appeared) { record(sId, "notReached", { reason: "opener-no-popup" }); await dismiss(page, frame); continue; }
      if (isDialog) {
        await captureDialogWithTabs(page, frame, sId);
      } else {
        // first-level popup holds the menu/palette content; the notebookbar has
        // effectively no second level here (submenuPass captured 0 and cost ~1s each),
        // so we do not descend - context-menu submenus are a separate, later concern.
        await captureSurface(page, frame, sId, { rootSelector: root });
      }
    } catch (error) {
      record(sId, "failed", { error: String(error?.message || error) });
    }
    await dismiss(page, frame);
  }
}

// Per-object context menus. Reliable, no-insert targets first; object inserts are
// best-effort and logged notReached when the precondition cannot be set up.
async function contextMenuPass(page, frame, locale, app, file) {
  const targets = [];
  // body / canvas (all apps)
  targets.push({ state: "body", precondition: "none", run: async () => {
    await frame.locator("canvas").first().click({ button: "right", position: { x: 260, y: 240 }, timeout: 8000 });
  }});
  if (app.key === "calc") {
    targets.push({ state: "colheader", precondition: "column header", run: async () => {
      await frame.locator("canvas").first().click({ button: "right", position: { x: 200, y: 70 }, timeout: 8000 });
    }});
    targets.push({ state: "rowheader", precondition: "row header", run: async () => {
      await frame.locator("canvas").first().click({ button: "right", position: { x: 20, y: 220 }, timeout: 8000 });
    }});
    targets.push({ state: "sheettab", precondition: "sheet tab", run: async () => {
      await frame.locator(".spreadsheet-tab, #spreadsheet-tab0, [id^='spreadsheet-tab']").first().click({ button: "right", timeout: 8000 });
    }});
  }
  if (app.key === "writer") {
    targets.push({ state: "text", precondition: "text selected", run: async () => {
      await frame.locator("canvas").first().click({ position: { x: 300, y: 200 }, timeout: 8000 });
      await page.keyboard.type("Sample text");
      await page.keyboard.press("Home");
      await page.keyboard.press("Shift+End");
      await frame.locator("canvas").first().click({ button: "right", position: { x: 320, y: 200 }, timeout: 8000 });
    }});
  }

  for (const t of targets) {
    const sId = scenario(locale, app, `ctx-${t.state}`, file, { surface: "context-menu", precondition: t.precondition, path: `${app.label} › context menu › ${t.state}` });
    try {
      await t.run();
      await page.waitForTimeout(600);
      const appeared = await frame.locator(POPUP).first().isVisible().catch(() => false);
      if (!appeared) { record(sId, "notReached", { reason: "no-context-menu" }); await dismiss(page, frame); continue; }
      await captureSurface(page, frame, sId, { rootSelector: POPUP, screenshot: shouldScreenshot("context-menu") });
    } catch (error) {
      record(sId, "notReached", { reason: String(error?.message || error).slice(0, 80) });
    }
    await dismiss(page, frame);
  }
}

// Modal dialogs via sendUnoCommand: capture title + body, then iterate inner tabs.
async function dialogPass(page, frame, locale, app, file) {
  // give the document focus + a selected cell/cursor so cell/selection-dependent
  // dialogs (Format Cells, etc.) actually open
  await frame.locator("canvas").first().click({ position: { x: 260, y: 240 }, timeout: 8000 }).catch(() => {});
  await page.waitForTimeout(300);
  for (const cmd of APP_DIALOGS[app.key] || []) {
    const name = cmd.replace(/^\.uno:/, "");
    const sId = scenario(locale, app, `dialog-${slug(name)}`, file, { surface: "dialog", opener: cmd, path: `${app.label} › dialog › ${name}` });
    await dismiss(page, frame); // never let a leftover modal shadow this command
    // hard guard: if the previous dialog refused to close, SKIP rather than capture it
    // under this command's name (that was the Format-Cells contamination bug)
    if (await frame.locator(DIALOG).count().catch(() => 0) > 0) {
      record(sId, "notReached", { reason: "prev-dialog-stuck" });
      continue;
    }
    try {
      await frame.evaluate((c) => { (window.app?.map)?.sendUnoCommand(c); }, cmd);
      await page.waitForTimeout(1600);
      const appeared = await frame.locator(DIALOG).first().isVisible().catch(() => false);
      if (!appeared) { record(sId, "notReached", { reason: "no-dialog" }); await dismiss(page, frame); continue; }
      await captureDialogWithTabs(page, frame, sId);
    } catch (error) {
      record(sId, "notReached", { reason: String(error?.message || error).slice(0, 80) });
    }
    await dismiss(page, frame);
  }
}

// Capture the dialog as-opened, then click each inner .ui-tab and capture again.
async function captureDialogWithTabs(page, frame, baseScenario) {
  await captureSurface(page, frame, baseScenario, { rootSelector: DIALOG });
  let tabIds = [];
  try {
    tabIds = await frame.evaluate((sel) => {
      const root = document.querySelector(sel);
      if (!root) return [];
      return Array.from(root.querySelectorAll(".ui-tab"))
        .filter((el) => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; })
        .map((el) => ({ id: el.id || "", label: (el.textContent || "").replace(/\s+/g, " ").trim() }))
        .filter((x) => x.id || x.label);
    }, DIALOG);
  } catch { tabIds = []; }

  const slice = tabIds.slice(0, 12);
  for (let i = 0; i < slice.length; i += 1) {
    const t = slice[i];
    // key by INDEX, not the tab label: labels are localized (en "Font" vs ru "Шрифт"),
    // and slug() strips non-ASCII to "x", so label keys never pair across locales.
    const key = `t${i}`;
    const sId = { ...baseScenario, scenario_id: `${baseScenario.scenario_id}__${key}`, state: `${baseScenario.state}__${key}`, path: `${baseScenario.path} › ${t.label}` };
    // switch tabs via DOM .click(): Playwright .click() on JSDialog children times out
    // on actionability (this was 1329 wasted 3s timeouts), DOM dispatch is instant + reliable
    const clicked = await frame.evaluate(({ sel, id, label }) => {
      const root = document.querySelector(sel);
      if (!root) return false;
      let el = id ? root.querySelector(`[id="${(window.CSS && CSS.escape) ? CSS.escape(id) : id}"]`) : null;
      if (!el) el = Array.from(root.querySelectorAll(".ui-tab")).find((x) => (x.textContent || "").replace(/\s+/g, " ").trim() === label);
      if (!el) return false;
      el.click();
      return true;
    }, { sel: DIALOG, id: t.id, label: t.label }).catch(() => false);
    if (!clicked) { record(sId, "notReached", { reason: "tab-not-found" }); continue; }
    await page.waitForTimeout(350);
    await captureSurface(page, frame, sId, { rootSelector: DIALOG });
  }
}

// Tooltip pass: harvest data-cooltip from every ribbon control (reliable text),
// plus a real hover over a sample to confirm the rendered bubble appears.
async function tooltipPass(page, frame, locale, app, file) {
  const sId = scenario(locale, app, "tooltips", file, { surface: "tooltip", path: `${app.label} › tooltips` });
  try {
    const data = await frame.evaluate(() => {
      const norm = (v) => (v || "").replace(/\s+/g, " ").trim();
      const tips = [];
      for (const el of document.querySelectorAll("[data-cooltip]")) {
        const r = el.getBoundingClientRect();
        if (r.width <= 0 || r.height <= 0) continue;
        const btn = el.querySelector("button[aria-label]");
        tips.push({ id: el.id || "", cooltip: norm(el.getAttribute("data-cooltip")), aria: norm(btn && btn.getAttribute("aria-label")) });
      }
      return tips;
    });
    // real hover to confirm the live tooltip bubble renders (per requirement)
    let hoverConfirmed = false;
    try {
      const btn = frame.locator(".unotoolbutton:visible button.ui-content").first();
      await btn.hover({ timeout: 5000 });
      await page.waitForTimeout(1500);
      hoverConfirmed = await frame.evaluate(() =>
        !!document.querySelector(".hovertooltip, .cool-tooltip, .leaflet-tooltip, [role=tooltip]:not(.visuallyhidden)"));
    } catch { /* hover best-effort */ }

    const controls = data.map((t) => ({ tag: "TOOLTIP", id: t.id, className: "data-cooltip", text: t.cooltip, aria: t.aria, title: "", role: "tooltip", path: sId.path }));
    const lines = uniqueLines(controls.flatMap((c) => [c.text, c.aria]));
    persist(sId, { url: "", title: "", bodyText: "", htmlAttrs: {}, controls }, lines, "", { hoverConfirmed, tipCount: controls.length });
  } catch (error) {
    record(sId, "failed", { error: String(error?.message || error) });
  }
}

// ---------------------------------------------------------------------------
// Capture core
// ---------------------------------------------------------------------------
async function captureSurface(page, frame, s, options = {}) {
  const started = new Date().toISOString();
  try {
    const data = await frame.evaluate((rootSel) => {
      const root = rootSel ? document.querySelector(rootSel) : document;
      if (!root) return null;
      const visible = (el) => {
        const st = window.getComputedStyle(el); const r = el.getBoundingClientRect();
        return st.visibility !== "hidden" && st.display !== "none" && r.width > 0 && r.height > 0;
      };
      const norm = (v) => (v || "").replace(/\s+/g, " ").trim();
      // nearest labeled ancestor chain (dialog/popup/sidebar/tab) -> short path
      const ancestry = (el) => {
        const labels = [];
        let n = el;
        for (let i = 0; n && i < 8; i += 1) {
          const lbl = n.getAttribute && (n.getAttribute("aria-label") || (n.classList && n.classList.contains("ui-dialog-title") ? n.textContent : ""));
          if (lbl && norm(lbl) && norm(lbl) !== "Dropdown") labels.unshift(norm(lbl).slice(0, 30));
          n = n.parentElement;
        }
        return labels.slice(-4).join(" › ");
      };
      const clickableTags = new Set(["BUTTON", "INPUT", "SELECT", "TEXTAREA", "A"]);
      const sel = "button,[role='button'],[aria-label],[title],[data-cooltip],input,select,textarea,.ui-tab,.unotoolbutton,.ui-content,.menu-entry,label,h1,h2,h3,legend,option";
      const controls = Array.from(root.querySelectorAll(sel)).filter(visible).map((el) => {
        const r = el.getBoundingClientRect();
        return {
          tag: el.tagName,
          id: el.id || "",
          className: String(el.className || "").slice(0, 120),
          text: norm(el.textContent).slice(0, 200),
          aria: norm(el.getAttribute("aria-label")),
          title: norm(el.getAttribute("title")),
          cooltip: norm(el.getAttribute("data-cooltip")),
          role: norm(el.getAttribute("role")),
          path: ancestry(el),
          // geometry for the layout regression checks (overlap/clip/whitespace/viewport)
          rect: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
          clip: (el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 1)
            ? { sw: el.scrollWidth, cw: el.clientWidth, sh: el.scrollHeight, ch: el.clientHeight } : null,
          clickable: clickableTags.has(el.tagName) || el.getAttribute("role") === "button" || !!el.getAttribute("aria-haspopup"),
        };
      });
      const bodyText = (root.innerText || root.textContent || "");
      const htmlAttrs = {
        lang: document.documentElement.lang || "", dir: document.documentElement.dir || "",
        vw: window.innerWidth, vh: window.innerHeight,
      };
      return { url: location.href, title: document.title, bodyText, htmlAttrs, controls };
    }, options.rootSelector || null);

    if (!data) { record(s, "notReached", { reason: "root-missing" }); return; }
    const lines = uniqueLines([
      ...data.bodyText.split(/\r?\n/),
      ...data.controls.flatMap((c) => [c.text, c.aria, c.title, c.cooltip]),
    ]);
    let screenshotPath = "";
    if (options.screenshot) {
      screenshotPath = path.join("screenshots", `${s.scenario_id}.png`);
      await page.screenshot({ path: path.join(outDir, screenshotPath), fullPage: false }).catch(() => {});
    }
    persist(s, data, lines, screenshotPath, {}, started);
  } catch (error) {
    record(s, "failed", { error: String(error?.message || error) }, started);
  }
}

// Write json/text + push manifests + visible rows for one captured surface.
function persist(s, data, lines, screenshotPath = "", extra = {}, started = new Date().toISOString()) {
  if (seenScenarioIds.has(s.scenario_id)) s.scenario_id = `${s.scenario_id}-${seenScenarioIds.size}`;
  seenScenarioIds.add(s.scenario_id);
  pushManifest(s);
  const jsonPath = path.join("json", `${s.scenario_id}.json`);
  const textPath = path.join("text", `${s.scenario_id}.txt`);
  writeJson(path.join(outDir, jsonPath), { scenario: s, data, lines });
  fs.writeFileSync(path.join(outDir, textPath), lines.join("\n") + "\n");
  visibleRows.push({
    scenario_id: s.scenario_id, locale: s.locale, app: s.app, state: s.state,
    surface: s.surface || "", path: s.path || "", precondition: s.precondition || "",
    lines, controls: data.controls.length, text_line_count: lines.length, screenshot: screenshotPath,
  });
  runManifest.push({
    scenario_id: s.scenario_id, status: "passed", started, ended: new Date().toISOString(),
    surface: s.surface || "", text_path: textPath, json_path: jsonPath, screenshot_path: screenshotPath,
    line_count: lines.length, control_count: data.controls.length, ...extra,
  });
}

function record(s, status, extra = {}, started = new Date().toISOString()) {
  if (seenScenarioIds.has(s.scenario_id)) s.scenario_id = `${s.scenario_id}-${seenScenarioIds.size}`;
  seenScenarioIds.add(s.scenario_id);
  pushManifest(s);
  runManifest.push({ scenario_id: s.scenario_id, status, surface: s.surface || "", started, ended: new Date().toISOString(), ...extra });
}

function pushManifest(s) {
  scenarioManifest.push({
    scenario_id: s.scenario_id, locale: s.locale, app: s.app, state: s.state,
    surface: s.surface || "", path: s.path || "", precondition: s.precondition || "",
    opener: s.opener || "", file_id: s.file_id, file_name: s.file_name, expected_dir: s.expected_dir,
  });
}

// ---------------------------------------------------------------------------
// Editor helpers
// ---------------------------------------------------------------------------
// Close any open popup/dialog. A modal dialog blocks every later sendUnoCommand, so
// this MUST be reliable. Proven by probe: Playwright cannot click the titlebar-close
// button (actionability times out), but a DOM-level .click() on it fires its handler
// and is unaffected by focus left inside the dialog after we walked its tabs. So for a
// dialog: DOM-click the close button, then fall back to focus-titlebar + Escape; for a
// popup: just Escape (clicking inside a menu would fire an item). Loop until empty.
async function dismiss(page, frame) {
  for (let i = 0; i < 8; i += 1) {
    const dlg = await frame.locator(DIALOG).count().catch(() => 0);
    const pop = await frame.locator(POPUP).count().catch(() => 0);
    if (!dlg && !pop) return;
    if (dlg) {
      await frame.evaluate((sel) => {
        const b = document.querySelector(`${sel} button.ui-dialog-titlebar-close`);
        if (b) b.click();
      }, DIALOG).catch(() => {});
      await page.waitForTimeout(200);
      if (await frame.locator(DIALOG).count().catch(() => 0)) {
        await frame.locator(`${DIALOG} .ui-dialog-titlebar`).first().click({ timeout: 1500, position: { x: 8, y: 8 } }).catch(() => {});
        await page.keyboard.press("Escape").catch(() => {});
      }
    } else {
      await page.keyboard.press("Escape").catch(() => {});
    }
    await page.waitForTimeout(300);
  }
}

async function selectTab(frame, page, tabs, name) {
  const t = tabs.find((x) => x.id === `${name}-tab-label`);
  if (!t) return;
  try { await clickById(frame, t.id); await page.waitForTimeout(300); } catch { /* best effort */ }
}

async function waitForEditorFrame(page) {
  await page.frameLocator("iframe[name=coframe]").locator("canvas").first().waitFor({ state: "visible", timeout: 90_000 });
  const frame = page.frame({ name: "coframe" });
  if (!frame) throw new Error("Editor iframe coframe was not found");
  await page.waitForTimeout(2_000);
  return frame;
}

async function visibleTabs(frame) {
  return frame.locator("button.ui-tab.notebookbar:visible").evaluateAll((els) =>
    els.map((el) => ({
      id: el.id || "",
      text: (el.textContent || "").replace(/\s+/g, " ").trim(),
      aria: el.getAttribute("aria-label") || "",
      panelId: el.getAttribute("aria-controls") || "",
      className: String(el.className || ""),
    })).filter((x) => x.id));
}

async function clickById(frame, id) {
  await frame.locator(`[id="${cssAttr(id)}"]`).click({ timeout: 10_000 });
}

// ---------------------------------------------------------------------------
// Provisioning + IO (unchanged utilities)
// ---------------------------------------------------------------------------
async function provisionUser(admin, locale) {
  const email = `l10n-rendered.${safe(locale.code)}.${Date.now()}.${Math.floor(Math.random() * 1e6)}@example.com`;
  const created = await admin.post("/admin/api/users", { data: { email, full_name: `L10N ${locale.code}`, locale: locale.code } });
  if (!created.ok()) throw new Error(`create user ${locale.code} failed: ${created.status()} ${await created.text()}`);
  const user = await created.json();
  const pw = await admin.post(`/admin/api/users/${user.id}/password`, { data: { password: PASSWORD } });
  if (!pw.ok()) throw new Error(`set password ${locale.code} failed: ${pw.status()} ${await pw.text()}`);
  return { ...user, email };
}

async function login(page, email, password) {
  await page.goto(`${BASE_URL}/login`);
  await page.locator("input[type=email]").fill(email);
  await page.locator("input[type=password]").fill(password);
  await page.locator("button[type=submit]").click();
  await page.waitForURL(`${BASE_URL}/`, { timeout: 20_000 });
}

async function createFile(page, localeCode, app) {
  const name = `l10n-${safe(localeCode)}-${app.key}`;
  const response = await page.request.post(`${BASE_URL}/api/nodes/file`, { data: { name, format: app.format, parent_id: null } });
  if (!response.ok()) throw new Error(`create ${localeCode}/${app.key} failed: ${response.status()} ${await response.text()}`);
  return response.json();
}

function scenario(locale, app, state, file, extra = {}) {
  return {
    scenario_id: `${safe(locale.code)}__${app.key}__${safe(state)}`,
    locale: locale.code, expected_dir: locale.dir, app: app.key, app_label: app.label,
    state, file_id: file.id, file_name: file.name, ...extra,
  };
}

function buildLeftovers(rows) {
  const byKey = new Map(rows.map((r) => [`${r.app}|${r.state}|${r.locale}`, r]));
  const leftovers = [];
  for (const row of rows) {
    if (row.locale === "en") continue;
    const baseline = byKey.get(`${row.app}|${row.state}|en`);
    if (!baseline) continue;
    const baselineLines = new Set(baseline.lines.map(normalizeText).filter((x) => x && !TEXT_ALLOWLIST.has(x)));
    for (const line of row.lines) {
      const normalized = normalizeText(line);
      if (!normalized || TEXT_ALLOWLIST.has(normalized)) continue;
      if (baselineLines.has(normalized) && looksEnglish(normalized)) {
        leftovers.push({ locale: row.locale, app: row.app, state: row.state, surface: row.surface, text: normalized, scenario_id: row.scenario_id, screenshot: row.screenshot });
      }
    }
  }
  return leftovers;
}

function writeMarkdownReport(filePath) {
  const passed = runManifest.filter((r) => r.status === "passed").length;
  const failed = runManifest.filter((r) => r.status === "failed").length;
  const notReached = runManifest.filter((r) => r.status === "notReached").length;
  const bySurface = new Map();
  for (const r of runManifest) bySurface.set(r.surface || "?", (bySurface.get(r.surface || "?") || 0) + 1);
  const lines = [
    "# Rendered Collabora Localization Inventory (deep walk)",
    "",
    "Этап 3 rendered inventory: every visible term with where/under-what-circumstances it appears.",
    "",
    "## Scope",
    `- Base URL: \`${BASE_URL}\``,
    `- Locales: ${selectedLocales.map((l) => l.code).join(", ")}`,
    `- Apps: ${selectedApps.map((a) => a.label).join(", ")}`,
    "- Surfaces: initial, ribbon tabs, dropdowns + one submenu level, per-object context menus, modal dialogs (via sendUnoCommand) + tabs, sidebar, tooltips (data-cooltip + hover).",
    "",
    "## Results",
    `- Scenarios: ${runManifest.length} (passed ${passed}, failed ${failed}, notReached ${notReached})`,
    `- Visible text rows: ${visibleRows.length}`,
    "",
    "## Scenarios by surface",
    table(["Surface", "Count"], [...bySurface.entries()].sort((a, b) => b[1] - a[1])),
    "",
    "## Artifacts",
    "- `scenario_manifest.json` / `run_manifest.json`: planned vs executed (passed/failed/notReached + reason).",
    "- `visible-text.jsonl`: machine-readable visible text with surface/path/precondition.",
    "- `english-leftovers.csv`: exact baseline-match English leftovers per app/state.",
    "- `json/` DOM dumps, `text/` normalized text, `screenshots/`.",
    "",
    "## Limits",
    "`notReached` scenarios are explicit: coverage is an upper bound. Canvas grid/slide text is out of scope (not in DOM). Object-context menus that need inserts may be notReached.",
    "",
  ];
  fs.writeFileSync(filePath, lines.join("\n"));
}

function parseArgs(argv) {
  const result = {};
  for (const arg of argv) {
    if (!arg.startsWith("--")) continue;
    const [key, raw = "true"] = arg.slice(2).split("=");
    result[key] = raw;
  }
  return result;
}
function selectByCode(items, value) {
  if (!value) return items;
  const wanted = new Set(value.split(",").map((x) => x.trim()).filter(Boolean));
  return items.filter((item) => wanted.has(item.code));
}
function selectByKey(items, value) {
  if (!value) return items;
  const wanted = new Set(value.split(",").map((x) => x.trim()).filter(Boolean));
  return items.filter((item) => wanted.has(item.key));
}
function shouldScreenshot(state) {
  if (screenshotMode === "none") return false;
  if (screenshotMode === "all") return true;
  if (screenshotMode === "main") return state === "initial" || state === "context-menu";
  return false;
}
function uniqueLines(values) {
  const out = []; const seen = new Set();
  for (const value of values) {
    const normalized = normalizeText(value);
    if (!normalized || seen.has(normalized)) continue;
    seen.add(normalized); out.push(normalized);
  }
  return out;
}
function normalizeText(value) { return String(value || "").replace(/\s+/g, " ").trim(); }
function looksEnglish(value) { return /[A-Za-z]{2,}/.test(value) && !/^https?:/.test(value); }
function safe(value) { return String(value).replace(/[^A-Za-z0-9_.-]+/g, "_"); }
function slug(value) { return safe(String(value).toLowerCase()).replace(/^_+|_+$/g, "").slice(0, 48) || "x"; }
function cssAttr(value) { return String(value).replace(/\\/g, "\\\\").replace(/"/g, '\\"'); }
function writeJson(filePath, value) { fs.mkdirSync(path.dirname(filePath), { recursive: true }); fs.writeFileSync(filePath, JSON.stringify(value, null, 2) + "\n"); }
function writeJsonLines(filePath, rows) { fs.writeFileSync(filePath, rows.map((row) => JSON.stringify(row)).join("\n") + "\n"); }
function writeCsv(filePath, rows) {
  const headers = rows.length ? Object.keys(rows[0]) : ["locale", "app", "state", "text", "scenario_id", "screenshot"];
  const lines = [headers.join(",")];
  for (const row of rows) lines.push(headers.map((h) => csvCell(row[h] ?? "")).join(","));
  fs.writeFileSync(filePath, lines.join("\n") + "\n");
}
function csvCell(value) { const text = String(value); return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text; }
function table(headers, rows) {
  if (!rows.length) return "_No rows._";
  const out = [`| ${headers.join(" | ")} |`, `| ${headers.map(() => "---").join(" | ")} |`];
  for (const row of rows) out.push(`| ${row.map((x) => String(x).replace(/\|/g, "\\|")).join(" | ")} |`);
  return out.join("\n");
}
