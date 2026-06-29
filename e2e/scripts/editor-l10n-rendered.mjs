import { chromium, request } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const BASE_URL = process.env.BASE_URL || "http://localhost:8088";
const PASSWORD = "test1234";

const LOCALES = [
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

const APPS = [
  { key: "writer", format: "docx", label: "Writer" },
  { key: "calc", format: "xlsx", label: "Calc" },
  { key: "impress", format: "pptx", label: "Impress" },
];

const TEXT_ALLOWLIST = new Set([
  "PrivateOffice",
  "Document name",
  "100",
  "A1",
  "1",
  "0",
  "OK",
]);

const args = parseArgs(process.argv.slice(2));
const selectedLocales = selectByCode(LOCALES, args.locales);
const selectedApps = selectByKey(APPS, args.apps);
const screenshotMode = args.screenshots || "main";
const outDir = path.resolve(args.out || ".qa/l10n-rendered");

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

const browser = await chromium.launch({ headless: true });
const admin = await request.newContext({
  baseURL: BASE_URL,
  httpCredentials: { username: "admin", password: "123" },
});

try {
  for (const locale of selectedLocales) {
    const user = await provisionUser(admin, locale);
    const context = await browser.newContext({ viewport: { width: 1792, height: 1200 } });
    const page = await context.newPage();
    page.setDefaultTimeout(20_000);
    await login(page, user.email, PASSWORD);
    const files = {};
    for (const app of selectedApps) {
      files[app.key] = await createFile(page, locale.code, app);
    }

    for (const app of selectedApps) {
      await runApp(page, locale, app, files[app.key]);
    }
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

console.log(`Rendered l10n artifacts written to ${outDir}`);
console.log(`Scenarios: ${runManifest.length}; failed: ${runManifest.filter((r) => r.status !== "passed").length}`);

async function runApp(page, locale, app, file) {
  await page.goto(`${BASE_URL}/file/${file.id}`);
  const frame = await waitForEditorFrame(page);
  const initialScenario = scenario(locale, app, "initial", file);
  await capture(page, frame, initialScenario, { screenshot: shouldScreenshot("initial") });

  const tabs = await visibleTabs(frame);
  for (const tab of tabs) {
    const state = tab.id.replace(/-tab-label$/, "") || slug(tab.text || "tab");
    const s = scenario(locale, app, `tab-${state}`, file, { tab });
    try {
      await clickById(frame, tab.id);
      await page.waitForTimeout(700);
      await capture(page, frame, s, { screenshot: shouldScreenshot(s.state) });
    } catch (error) {
      recordFailure(s, error);
    }
  }

  const home = tabs.find((t) => t.id === "Home-tab-label");
  if (home) {
    try {
      await clickById(frame, home.id);
      await page.waitForTimeout(300);
    } catch {
      // Best effort: context-menu capture can still try the canvas.
    }
  }
  const contextScenario = scenario(locale, app, "context-menu", file);
  try {
    await frame.locator("canvas").first().click({ button: "right", position: { x: 220, y: 220 }, timeout: 10_000 });
    await page.waitForTimeout(700);
    await capture(page, frame, contextScenario, { screenshot: shouldScreenshot("context-menu") });
    await page.keyboard.press("Escape").catch(() => {});
  } catch (error) {
    recordFailure(contextScenario, error);
  }
}

async function capture(page, frame, s, options = {}) {
  scenarioManifest.push({
    scenario_id: s.scenario_id,
    locale: s.locale,
    app: s.app,
    state: s.state,
    file_id: s.file_id,
    file_name: s.file_name,
    expected_dir: s.expected_dir,
  });

  const started = new Date().toISOString();
  try {
    const data = await frame.evaluate(() => {
      const visible = (el) => {
        const style = window.getComputedStyle(el);
        const rect = el.getBoundingClientRect();
        return style.visibility !== "hidden" && style.display !== "none" && rect.width > 0 && rect.height > 0;
      };
      const norm = (value) => (value || "").replace(/\s+/g, " ").trim();
      const controls = Array.from(document.querySelectorAll("button,[role='button'],[aria-label],[title],input,select,textarea,.ui-tab,.unotoolbutton,.ui-content"))
        .filter(visible)
        .map((el) => ({
          tag: el.tagName,
          id: el.id || "",
          className: String(el.className || ""),
          text: norm(el.textContent),
          aria: norm(el.getAttribute("aria-label")),
          title: norm(el.getAttribute("title")),
          role: norm(el.getAttribute("role")),
        }));
      const bodyText = document.body.innerText || "";
      const htmlAttrs = {
        lang: document.documentElement.lang || "",
        dir: document.documentElement.dir || "",
      };
      return {
        url: location.href,
        title: document.title,
        bodyText,
        htmlAttrs,
        controls,
      };
    });
    const lines = uniqueLines([
      ...data.bodyText.split(/\r?\n/),
      ...data.controls.flatMap((c) => [c.text, c.aria, c.title]),
    ]);
    const jsonPath = path.join("json", `${s.scenario_id}.json`);
    const textPath = path.join("text", `${s.scenario_id}.txt`);
    writeJson(path.join(outDir, jsonPath), { scenario: s, data, lines });
    fs.writeFileSync(path.join(outDir, textPath), lines.join("\n") + "\n");

    let screenshotPath = "";
    if (options.screenshot) {
      screenshotPath = path.join("screenshots", `${s.scenario_id}.png`);
      await page.screenshot({ path: path.join(outDir, screenshotPath), fullPage: false });
    }

    visibleRows.push({
      scenario_id: s.scenario_id,
      locale: s.locale,
      app: s.app,
      state: s.state,
      lines,
      controls: data.controls.length,
      text_line_count: lines.length,
      screenshot: screenshotPath,
    });
    runManifest.push({
      scenario_id: s.scenario_id,
      status: "passed",
      started,
      ended: new Date().toISOString(),
      text_path: textPath,
      json_path: jsonPath,
      screenshot_path: screenshotPath,
      line_count: lines.length,
      control_count: data.controls.length,
      lang: data.htmlAttrs.lang,
      dir: data.htmlAttrs.dir,
    });
  } catch (error) {
    recordFailure(s, error, started);
  }
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
        leftovers.push({
          locale: row.locale,
          app: row.app,
          state: row.state,
          text: normalized,
          scenario_id: row.scenario_id,
          screenshot: row.screenshot,
        });
      }
    }
  }
  return leftovers;
}

function writeMarkdownReport(filePath) {
  const passed = runManifest.filter((r) => r.status === "passed").length;
  const failed = runManifest.length - passed;
  const leftovers = readCsvRows(path.join(outDir, "english-leftovers.csv"));
  const byLocale = new Map();
  const byApp = new Map();
  for (const row of leftovers) {
    byLocale.set(row.locale, (byLocale.get(row.locale) || 0) + 1);
    byApp.set(row.app, (byApp.get(row.app) || 0) + 1);
  }
  const lines = [
    "# Rendered Collabora Localization Inventory",
    "",
    "Phase 2 rendered inventory generated by Playwright against the live local stack.",
    "",
    "## Scope",
    "",
    `- Base URL: \`${BASE_URL}\``,
    `- Locales requested: ${selectedLocales.map((l) => l.code).join(", ")}`,
    `- Apps requested: ${selectedApps.map((a) => a.label).join(", ")}`,
    "- States: initial editor load, every visible notebookbar tab, and one document canvas context menu per app.",
    `- Screenshots mode: \`${screenshotMode}\``,
    "",
    "## Results",
    "",
    `- Scenarios recorded: ${runManifest.length}`,
    `- Passed: ${passed}`,
    `- Failed/skipped: ${failed}`,
    `- Visible text rows: ${visibleRows.length}`,
    `- English leftover candidate rows: ${leftovers.length}`,
    "",
    "## Candidate English Leftovers By Locale",
    "",
    table(["Locale", "Candidate rows"], [...byLocale.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))),
    "",
    "## Candidate English Leftovers By App",
    "",
    table(["App", "Candidate rows"], [...byApp.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))),
    "",
    "## Artifacts",
    "",
    "- `scenario_manifest.json`: expected scenarios.",
    "- `run_manifest.json`: executed scenarios and paths to artifacts.",
    "- `visible-text.jsonl`: machine-readable visible text inventory.",
    "- `english-leftovers.csv`: exact-match candidate English leftovers against the English baseline for the same app/state.",
    "- `text/`: normalized text dumps.",
    "- `json/`: DOM/control dumps.",
    "- `screenshots/`: screenshots captured according to screenshot mode.",
    "",
    "## Limits",
    "",
    "This pass proves rendered top-level editor states, visible notebookbar tabs, and one context menu. It does not yet exhaust every dropdown, modal dialog, tooltip, or document-object contextual state. Candidate English leftovers are exact baseline matches and still need human/source-class triage before patching.",
    "",
  ];
  fs.writeFileSync(filePath, lines.join("\n"));
}

function scenario(locale, app, state, file, extra = {}) {
  return {
    scenario_id: `${safe(locale.code)}__${app.key}__${safe(state)}`,
    locale: locale.code,
    expected_dir: locale.dir,
    app: app.key,
    app_label: app.label,
    state,
    file_id: file.id,
    file_name: file.name,
    ...extra,
  };
}

function recordFailure(s, error, started = new Date().toISOString()) {
  scenarioManifest.push({
    scenario_id: s.scenario_id,
    locale: s.locale,
    app: s.app,
    state: s.state,
    file_id: s.file_id,
    file_name: s.file_name,
    expected_dir: s.expected_dir,
  });
  runManifest.push({
    scenario_id: s.scenario_id,
    status: "failed",
    started,
    ended: new Date().toISOString(),
    error: String(error?.message || error),
  });
}

async function waitForEditorFrame(page) {
  await page.frameLocator("iframe[name=coframe]").locator("canvas").first().waitFor({ state: "visible", timeout: 90_000 });
  const frame = page.frame({ name: "coframe" });
  if (!frame) throw new Error("Editor iframe coframe was not found");
  await page.waitForTimeout(1_000);
  return frame;
}

async function visibleTabs(frame) {
  return frame.locator("button.ui-tab.notebookbar:visible").evaluateAll((els) =>
    els.map((el) => ({
      id: el.id || "",
      text: (el.textContent || "").replace(/\s+/g, " ").trim(),
      aria: el.getAttribute("aria-label") || "",
      className: String(el.className || ""),
    })).filter((x) => x.id),
  );
}

async function clickById(frame, id) {
  await frame.locator(`[id="${cssAttr(id)}"]`).click({ timeout: 10_000 });
}

async function provisionUser(admin, locale) {
  const email = `l10n-rendered.${safe(locale.code)}.${Date.now()}.${Math.floor(Math.random() * 1e6)}@example.com`;
  const created = await admin.post("/admin/api/users", {
    data: { email, full_name: `L10N ${locale.code}`, locale: locale.code },
  });
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
  const response = await page.request.post(`${BASE_URL}/api/nodes/file`, {
    data: { name, format: app.format, parent_id: null },
  });
  if (!response.ok()) throw new Error(`create ${localeCode}/${app.key} failed: ${response.status()} ${await response.text()}`);
  return response.json();
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
  const out = [];
  const seen = new Set();
  for (const value of values) {
    const normalized = normalizeText(value);
    if (!normalized || seen.has(normalized)) continue;
    seen.add(normalized);
    out.push(normalized);
  }
  return out;
}

function normalizeText(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function looksEnglish(value) {
  return /[A-Za-z]{2,}/.test(value) && !/^https?:/.test(value);
}

function safe(value) {
  return String(value).replace(/[^A-Za-z0-9_.-]+/g, "_");
}

function slug(value) {
  return safe(String(value).toLowerCase()).replace(/^_+|_+$/g, "") || "state";
}

function cssAttr(value) {
  return String(value).replace(/\\/g, "\\\\").replace(/"/g, '\\"');
}

function writeJson(filePath, value) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, JSON.stringify(value, null, 2) + "\n");
}

function writeJsonLines(filePath, rows) {
  fs.writeFileSync(filePath, rows.map((row) => JSON.stringify(row)).join("\n") + "\n");
}

function writeCsv(filePath, rows) {
  const headers = rows.length ? Object.keys(rows[0]) : ["locale", "app", "state", "text", "scenario_id", "screenshot"];
  const lines = [headers.join(",")];
  for (const row of rows) {
    lines.push(headers.map((h) => csvCell(row[h] ?? "")).join(","));
  }
  fs.writeFileSync(filePath, lines.join("\n") + "\n");
}

function readCsvRows(filePath) {
  if (!fs.existsSync(filePath)) return [];
  const [headerLine, ...lines] = fs.readFileSync(filePath, "utf8").trim().split(/\r?\n/);
  if (!headerLine) return [];
  const headers = parseCsvLine(headerLine);
  return lines.filter(Boolean).map((line) => {
    const cells = parseCsvLine(line);
    return Object.fromEntries(headers.map((h, i) => [h, cells[i] || ""]));
  });
}

function csvCell(value) {
  const text = String(value);
  if (/[",\n]/.test(text)) return `"${text.replace(/"/g, '""')}"`;
  return text;
}

function parseCsvLine(line) {
  const out = [];
  let cur = "";
  let quoted = false;
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (quoted) {
      if (ch === '"' && line[i + 1] === '"') {
        cur += '"';
        i += 1;
      } else if (ch === '"') {
        quoted = false;
      } else {
        cur += ch;
      }
    } else if (ch === '"') {
      quoted = true;
    } else if (ch === ",") {
      out.push(cur);
      cur = "";
    } else {
      cur += ch;
    }
  }
  out.push(cur);
  return out;
}

function table(headers, rows) {
  if (!rows.length) return "_No rows._";
  const lines = [
    `| ${headers.join(" |")} |`,
    `| ${headers.map(() => "---").join(" | ")} |`,
  ];
  for (const row of rows) lines.push(`| ${row.map((x) => String(x).replace(/\|/g, "\\|")).join(" | ")} |`);
  return lines.join("\n");
}
