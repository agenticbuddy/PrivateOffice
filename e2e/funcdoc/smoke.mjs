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
  // The editor session accumulates browser-side state (DOM churn / WS) and, past ~120 UI operations,
  // POISONS all further input — the NEXT sheet then silently takes nothing (seeds + inserts all drop).
  // Fix: reload the doc page periodically (openDoc re-acquires the iframe). Sheets are independent and
  // every edit is saved before a reload, so a fresh page simply resumes a clean session. `frame` is a
  // `let` so the closured helpers below always see the current iframe.
  let frame;
  const openDoc = async () => {
    await page.goto(`${BASE}/file/${nodeId}`);
    await page.frameLocator("iframe[name=coframe]").locator("canvas").first().waitFor({ state: "visible", timeout: 90000 });
    frame = page.frame({ name: "coframe" });
    await page.waitForTimeout(4000);
  };
  // (openDoc is invoked at the start of each sheet — a fresh session per sheet, see the loop below)

  const uno = (c) => frame.evaluate((cmd) => window.app.map.sendUnoCommand(cmd), c);
  // the Name Box mirrors the active cell — the ground truth for WHERE the next keystroke lands
  const activeCell = async () => frame.evaluate(() => {
    const el = document.querySelector("#addressInput-input") || document.querySelector("#addressInput input");
    return el ? (el.value || "") : "";
  }).catch(() => "");
  // VERIFIED navigation: rapid-fire GoToCell drifts (~40% wrong at scale) — a seed/formula then lands in the
  // WRONG cell and corrupts a neighbour. Confirm the cursor actually arrived; retry, then fall back to typing
  // the address into the Name Box (deterministic). Root fix for the #1 failure — used by every read & write.
  const goto = async (cell) => {
    for (let i = 0; i < 4; i++) {
      await uno(`.uno:GoToCell?ToPoint:string=${cell}`); await page.waitForTimeout(70);
      if ((await activeCell()).toUpperCase() === cell.toUpperCase()) return;
    }
    await frame.locator("#addressInput-input").fill(cell).catch(() => {});
    await frame.locator("#addressInput-input").press("Enter").catch(() => {});
    await page.waitForTimeout(90);
  };
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
  // Seeds drive every formula, so a seed that lands WRONG (positional drift under rapid GoToCell — the #1
  // failure — put "10" into a date cell; or a value drifted one cell over) makes referencing formulas
  // diverge across sheets. A non-empty check is NOT enough (wrong content is still non-empty): verify the
  // committed cell holds EXACTLY the intended text, and retry. Non-fatal so one stubborn seed can't nuke a
  // long run — unrecovered ones are recorded and surface in check.py's report.
  const readBarRaw = async () => (await frame.locator("#sc_input_window, .inputbar_container").first().innerText().catch(() => "")).trim();
  const seedMatches = (bar, text) => {
    const b = (bar.split("\n")[0] || "").trim().replace(/\s/g, "");
    const t = text.trim().replace(/\s/g, "");
    return b === t;                                 // formula seeds keep localized names; values match raw
  };
  const typeSeed = async (cell, text) => {
    for (let attempt = 0; attempt < 4; attempt++) {
      await typeVal(cell, text);
      await goto(cell); await page.waitForTimeout(60);
      if (seedMatches(await readBarRaw(), text)) return true;
      await clearCell(cell);                         // wipe drifted/partial content before retrying
    }
    return false;
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
  // ---- method: Function Wizard (type formula into #ed_formula, click ОК), verified + retried ----
  // (the dialog occasionally fails to open on a category switch → #ed_formula/#ok-button time out; the
  // old fire-once version then threw. Retry the whole open→fill→OK, verifying the committed formula.)
  const wizardInsert = async (ru, inner, cell) => {
    for (let attempt = 0; attempt < 3; attempt++) {
      await goto(cell); await clearOverlay();        // START each attempt with NO dialog open (else a
      await uno(".uno:FunctionDialog");              // second .uno:FunctionDialog stacks/toggles modals
      const ed = frame.locator("#ed_formula");       // and wedges the whole UI → cascades to later sheets)
      try { await ed.waitFor({ state: "visible", timeout: 6000 }); }
      catch { await clearOverlay(); continue; }       // dialog was slow/failed to open — clean-retry
      await ed.fill(`=${ru}(${inner})`);
      await page.waitForTimeout(200);
      await frame.locator("#ok-button").first().click().catch(() => {});
      // array-returning functions (РОСТ/ТЕНДЕНЦИЯ/МУМНОЖ…) commit as {=…} and the spill takes a beat to
      // settle — read the bar too soon and verify sees nothing, wasting all 3 retries. Give it room.
      await page.waitForTimeout(550); await clearOverlay();
      await goto(cell); await page.waitForTimeout(150);
      if (inserted(await barFormula(), ru, inner)) return;
      await clearCell(cell);
    }
    throw new Error(`wizardInsert failed after 3 attempts: ${ru} @ ${cell}`);
  };
  // ---- formula-bar verification (shared by every insert method) ----
  const readBar = async () => (await frame.locator("#sc_input_window, .inputbar_container").first().innerText().catch(() => "")).trim();
  // the bar duplicates the formula over two lines and wraps array formulas as {=…}: take line 1, strip braces
  const barFormula = async () => (await readBar()).split("\n")[0].trim().replace(/^\{|\}$/g, "");
  // the cell references inside `inner` ($BE$1, B1:B3, $BA$12:$BC$16 …) — every one must survive into the cell
  const refTokens = (inner) => inner.match(/\$?[A-Za-z]+\$?\d+(?::\$?[A-Za-z]+\$?\d+)?/g) || [];
  // an insert is GOOD when the committed formula names the right function AND kept every arg reference
  // (catches empty cells, wrong function, AND a dropped argument — without demanding byte-exact formatting,
  // since the core may reformat). For literal-only args (no refs) it just requires non-empty parens.
  const inserted = (bar, ru, inner) => {
    if (!bar.startsWith(`=${ru}(`)) return false;
    if (inner.trim() === "") return true;          // zero-arg function (ЛОЖЬ/ПИ/СЕГОДНЯ…): =RU() IS correct
    const refs = refTokens(inner);
    if (refs.length) return refs.every((r) => bar.includes(r));
    return bar !== `=${ru}()`;                     // literal args present
  };
  const clearCell = async (cell) => { await goto(cell); await page.keyboard.press("Delete"); await page.waitForTimeout(40); await clearOverlay(); };
  // ---- method: direct typing ----
  const directInsert = async (ru, inner, cell) => {
    // type + commit, then VERIFY via the formula bar; retry if the keystrokes were swallowed
    // (short names like ASC occasionally drop). Never Escape mid-edit — that would cancel the cell.
    for (let attempt = 0; attempt < 3; attempt++) {
      await goto(cell); await clearOverlay();
      await page.keyboard.type(`=${ru}(${inner})`, { delay: 10 });
      await page.keyboard.press("Enter"); await page.waitForTimeout(80); await clearOverlay();
      await goto(cell); await page.waitForTimeout(60);
      if (inserted(await barFormula(), ru, inner)) return;
      await clearCell(cell);                         // wipe a partial formula before retrying
    }
    // all 3 attempts were swallowed — THROW so the caller counts a failure (not ok++). Otherwise a
    // silently-empty direct-insert cell would pass the smoke green (reviewer bug 1).
    throw new Error(`directInsert failed after 3 attempts: ${ru} @ ${cell}`);
  };
  // ---- method: ribbon menu, verified + retried (was fire-and-forget → whole categories dropped silently
  // under load; now mirrors directInsert: menu-click + fill, verify the committed formula, retry up to 3×) ----
  const menuInsertVerified = async (btn, ru, inner, cell) => {
    for (let attempt = 0; attempt < 3; attempt++) {
      await goto(cell); await clearOverlay();
      await menuInsert(btn, ru);
      await fillSel(ru, inner);
      await goto(cell); await page.waitForTimeout(60);
      if (inserted(await barFormula(), ru, inner)) return;
      await clearCell(cell);
    }
    throw new Error(`menuInsert failed after 3 attempts: ${ru} @ ${cell}`);
  };

  // Reload budget: a single session survives ~150 ops, so reload well under that WITHIN a sheet, and
  // ALWAYS open the doc fresh at the start of each sheet (cross-sheet poisoning is the dominant failure).
  const RELOAD_EVERY = 120;
  let ops = 0;
  const enterSheet = async (tab, formulaTab) => {
    await frame.locator(".spreadsheet-tab").nth(tab).click();
    await page.waitForTimeout(700);
    if (formulaTab) { await frame.locator("#Formula-tab-label").first().click().catch(() => {}); await page.waitForTimeout(700); }
  };
  const saveAndWait = async () => { await uno(".uno:Save"); await page.waitForTimeout(8000); };
  // reload mid-sheet once we cross the op budget, restoring the sheet + ribbon context we were in
  const tick = async (tab, formulaTab) => {
    if (++ops < RELOAD_EVERY) return;
    await saveAndWait(); await openDoc(); await enterSheet(tab, formulaTab); ops = 0;
  };

  for (const sh of SHEETS) {
    await openDoc();                 // FRESH session per sheet — the single most important robustness step
    ops = 0;
    await enterSheet(sh.tab, false);
    // seeds first (values), on a neutral tab — switching to Формулы BEFORE typing seeds could eat the
    // first seed keystroke (observed: $BE$1 dropped on the menu sheet -> text funcs #VALUE!)
    for (const s of plan.seeds) { await typeSeed(s.cell, s.text); await tick(sh.tab, false); }
    // RE-VERIFY & repair: even with a per-seed check at type time, entering a LATER seed can drift onto an
    // EARLIER, already-verified cell (observed: BD3 date seed clobbered to "10"). A final pass re-reads every
    // seed and re-types only the mismatches; re-typing the bad ones doesn't touch the good ones, so it
    // converges in a couple rounds even for a systematic drift.
    let seedFails = [];
    for (let round = 0; round < 3; round++) {
      seedFails = [];
      for (const s of plan.seeds) {
        await goto(s.cell); await page.waitForTimeout(30);
        if (!seedMatches(await readBarRaw(), s.text)) seedFails.push(s);
        await tick(sh.tab, false);
      }
      if (!seedFails.length) break;
      for (const s of seedFails) await typeSeed(s.cell, s.text);
    }
    if (seedFails.length) out.seedFails = (out.seedFails || []).concat(seedFails.map((s) => `${sh.name}:${s.cell}`));
    const formulaTab = sh.method === "menu";
    if (formulaTab) { await frame.locator("#Formula-tab-label").first().click().catch(() => {}); await page.waitForTimeout(700); }
    let ok = 0, fail = [];
    for (const b of plan.blocks) {
      const items = SUBSET ? b.items.slice(0, SUBSET) : b.items;
      await typeVal(b.header_cell, b.label); await tick(sh.tab, formulaTab);
      for (const it of items) { await typeVal(it.name_cell, it.ru); await tick(sh.tab, formulaTab); }
      for (const it of items) {
        try {
          await goto(it.f_cell); await clearOverlay();  // no stale autocomplete overlay eating input
          if (sh.method === "menu") await menuInsertVerified(it.btn, it.ru, it.inner, it.f_cell);
          else if (sh.method === "wizard") await wizardInsert(it.ru, it.inner, it.f_cell);
          else await directInsert(it.ru, it.inner, it.f_cell);
          ok++;
        } catch (e) { fail.push(it.ru); await page.keyboard.press("Escape").catch(() => {}); await clearOverlay(); }
        await tick(sh.tab, formulaTab);
      }
    }
    await saveAndWait();             // persist this sheet before the next one reopens the doc
    out.sheets.push({ name: sh.name, method: sh.method, inserted: ok, failed: fail });
  }

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
