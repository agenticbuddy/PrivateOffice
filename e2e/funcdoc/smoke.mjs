// FUNCTIONS-CHECK SMOKE TEST — builds a 3-sheet workbook where the SAME set of function formulas
// is entered three different ways through the live editor UI, to verify both that the core computes
// them AND that each insertion path of our fixed interface works for a real user:
//   • "Через меню"   — ribbon Формулы → category dropdown → click localized function → fill args
//   • "Через мастер" — Function Wizard: type the formula into #ed_formula, click ОК
//   • "Прямой ввод"  — type =ИМЯ(args) straight into the cell
// Names + seed data are entered as plain values (allowed). Env: SUBSET=N funcs/category (fast smoke);
// NODE=<id> to build into an existing node; default uploads a fresh 3-sheet template.
import { chromium, request } from "@playwright/test";
import fs from "node:fs";
const BASE = "http://localhost:8088";
const BOT = "functions-check.bot.1782967998794@example.com", PW = "test1234";
const MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
const plan = JSON.parse(fs.readFileSync("/tmp/funcdoc-ui-plan.json", "utf8"));
const SUBSET = process.env.SUBSET ? parseInt(process.env.SUBSET, 10) : 0;
const SHEETS = [
  { tab: 0, name: "Через меню", method: "menu" },
  { tab: 1, name: "Через мастер", method: "wizard" },
  { tab: 2, name: "Прямой ввод", method: "direct" },
];
const browser = await chromium.launch({ headless: true });
const out = { sheets: [] };
try {
  // upload a fresh 3-empty-named-sheet template (or reuse NODE)
  let nodeId = process.env.NODE;
  const u = await request.newContext({ baseURL: BASE });
  const login = await u.post("/api/auth/login", { data: { email: BOT, password: PW } });
  if (!login.ok()) throw new Error(`login failed: HTTP ${login.status()}`);
  if (!nodeId) {
    const up = await u.post("/api/nodes/upload", { multipart: { file: { name: "Проверка функций.xlsx", mimeType: MIME, buffer: fs.readFileSync("/tmp/funcdoc-template.xlsx") } } });
    // Check the HTTP status BEFORE .json() — otherwise an upload that fails (e.g. MinIO/CO out of disk)
    // surfaces as an opaque JSON-parse error instead of the real cause.
    if (!up.ok()) throw new Error(`node upload failed: HTTP ${up.status()} — check storage/disk (${(await up.text()).slice(0, 120)})`);
    nodeId = (await up.json()).id;
  }
  await u.dispose();
  out.file = nodeId;

  const ctx = await browser.newContext({ viewport: { width: 1680, height: 1000 } });
  const page = await ctx.newPage(); page.setDefaultTimeout(25000);
  await page.goto(`${BASE}/login`);
  await page.locator("input[type=email]").fill(BOT);
  await page.locator("input[type=password]").fill(PW);
  await page.locator("button[type=submit]").click();
  await page.waitForURL(`${BASE}/`, { timeout: 20000 });
  await page.goto(`${BASE}/file/${nodeId}`);
  await page.frameLocator("iframe[name=coframe]").locator("canvas").first().waitFor({ state: "visible", timeout: 90000 });
  const frame = page.frame({ name: "coframe" });
  await page.waitForTimeout(4000);

  const uno = (c) => frame.evaluate((cmd) => window.app.map.sendUnoCommand(cmd), c);
  const goto = async (cell) => { await uno(`.uno:GoToCell?ToPoint:string=${cell}`); await page.waitForTimeout(70); };
  const clearOverlay = async () => {
    for (let i = 0; i < 4; i++) {
      const ov = await frame.locator(".jsdialog-overlay, #formulaautocompletePopup-overlay").first().isVisible().catch(() => false);
      const md = await frame.locator(".jsdialog-window:not(.modalpopup)").first().isVisible().catch(() => false);
      if (!ov && !md) break;
      await page.keyboard.press("Escape").catch(() => {}); await page.waitForTimeout(110);
    }
  };
  const typeVal = async (cell, text) => {
    await goto(cell); await page.keyboard.type(text, { delay: 3 });
    await page.keyboard.press("Enter"); await page.waitForTimeout(40); await clearOverlay();
  };
  // ---- method: ribbon menu ----
  const menuInsert = async (btn, ru) => {
    await clearOverlay();
    await frame.locator(`#${btn[0]}`).first().click();
    await frame.locator(`#${btn[0]}-entries`).first().waitFor({ state: "visible", timeout: 8000 });
    await frame.locator(`#${btn[0]}-entries`).getByText(ru, { exact: true }).first().click();
    await page.waitForTimeout(500);
  };
  const fillSel = async (ru, inner) => {
    await page.keyboard.press("Home");
    for (let i = 0; i < ru.length + 2; i++) await page.keyboard.press("ArrowRight");
    await page.keyboard.press("Shift+End");
    await page.keyboard.type(inner + ")", { delay: 8 });
    await page.keyboard.press("Enter"); await page.waitForTimeout(110); await clearOverlay();
  };
  // ---- method: Function Wizard (type formula into #ed_formula, click ОК) ----
  const wizardInsert = async (ru, inner) => {
    await uno(".uno:FunctionDialog"); await page.waitForTimeout(1500);
    await frame.locator("#ed_formula").fill(`=${ru}(${inner})`);
    await page.waitForTimeout(250);
    await frame.locator("#ok-button").first().click();
    await page.waitForTimeout(350); await clearOverlay();
  };
  // ---- method: direct typing ----
  const readBar = async () => (await frame.locator("#sc_input_window, .inputbar_container").first().innerText().catch(() => "")).trim();
  const directInsert = async (ru, inner, cell) => {
    // type + commit, then VERIFY via the formula bar; retry if the keystrokes were swallowed
    // (short names like ASC occasionally drop). Never Escape mid-edit — that would cancel the cell.
    for (let attempt = 0; attempt < 3; attempt++) {
      await goto(cell); await clearOverlay();
      await page.keyboard.type(`=${ru}(${inner})`, { delay: 10 });
      await page.keyboard.press("Enter"); await page.waitForTimeout(80); await clearOverlay();
      await goto(cell); await page.waitForTimeout(60);
      if ((await readBar()).startsWith("=")) return;
    }
    // all 3 attempts were swallowed — THROW so the caller counts a failure (not ok++). Otherwise a
    // silently-empty direct-insert cell would pass the smoke green (reviewer bug 1).
    throw new Error(`directInsert failed after 3 attempts: ${ru} @ ${cell}`);
  };

  for (const sh of SHEETS) {
    await frame.locator(".spreadsheet-tab").nth(sh.tab).click();
    await page.waitForTimeout(700);
    // seeds first (values), while on a neutral tab — switching to Формулы BEFORE typing seeds could
    // eat the first seed keystroke (observed: $BE$1 dropped on the menu sheet -> text funcs #VALUE!)
    for (const s of plan.seeds) await typeVal(s.cell, s.text);
    if (sh.method === "menu") { await frame.locator("#Formula-tab-label").first().click().catch(() => {}); await page.waitForTimeout(700); }
    let ok = 0, fail = [];
    for (const b of plan.blocks) {
      const items = SUBSET ? b.items.slice(0, SUBSET) : b.items;
      await typeVal(b.header_cell, b.label);
      for (const it of items) await typeVal(it.name_cell, it.ru);
      for (const it of items) {
        try {
          await goto(it.f_cell); await clearOverlay();  // no stale autocomplete overlay eating input
          if (sh.method === "menu") { await menuInsert(it.btn, it.ru); await fillSel(it.ru, it.inner); }
          else if (sh.method === "wizard") await wizardInsert(it.ru, it.inner);
          else await directInsert(it.ru, it.inner, it.f_cell);
          ok++;
        } catch (e) { fail.push(it.ru); await page.keyboard.press("Escape").catch(() => {}); await clearOverlay(); }
      }
    }
    out.sheets.push({ name: sh.name, method: sh.method, inserted: ok, failed: fail });
  }

  await uno(".uno:Save");
  await page.waitForTimeout(10000);
  await ctx.close();
  out.done = true;
} catch (e) { out.error = String(e).slice(0, 200); }
finally {
  await browser.close();
  console.log(JSON.stringify(out));
  // FAIL the process if the build itself broke (error, or any sheet failed to insert a function).
  // Computation correctness is asserted separately by check.py against the produced node.
  const totalFailed = (out.sheets || []).reduce((n, s) => n + (s.failed ? s.failed.length : 0), 0);
  if (out.error || !out.done || totalFailed > 0) {
    console.error(`SMOKE BUILD FAILED — error=${out.error || "none"}, insertion failures=${totalFailed}`);
    process.exit(1);
  }
}
