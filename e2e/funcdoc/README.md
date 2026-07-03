# Functions-check smoke test

Builds a 3-sheet Calc workbook where the **same** set of ~448 localized function formulas is entered
**three different ways through the live editor UI**, then verifies both that the core computes them and
that each insertion path of our fixed interface works for a real user.

| Sheet | Method | What it exercises |
|---|---|---|
| **Через меню** | ribbon *Формулы* → category dropdown → click the localized function → args fill the placeholder template | our localized-function-name fix + `.uno:InsertFunction` path |
| **Через мастер** | Function Wizard: the formula is typed into the wizard's formula field (`#ed_formula`) and confirmed with **ОК** | the wizard dialog's parse + insert path |
| **Прямой ввод** | `=ИМЯ(аргументы)` typed straight into the cell | the inline cell-edit path |

Function **names** and the **seed data** each formula references are entered as plain values (allowed);
only the formula cells go through the three UI methods. All three sheets share the same layout and must
produce identical values.

## Run

```bash
cd e2e/funcdoc
python3 gen.py            # funcs.json + menu-map.json -> /tmp/funcdoc-ui-plan.json + /tmp/funcdoc.json
python3 template.py       # -> /tmp/funcdoc-template.xlsx (3 empty named sheets)
SUBSET=3 node smoke.mjs   # fast smoke: 3 funcs/category on each sheet; prints {"file": <node-id>, ...}
python3 check.py <node-id>   # ASSERTS correctness — exits 1 on any regression
```

- `SUBSET=N` limits to N functions per category (fast). Omit `SUBSET` to build **all 448** on every sheet
  (~80 min). `NODE=<id>` builds into an existing node instead of a fresh upload.
- Auth: uploads/edits as the controlled bot `functions-check.bot…@example.com`; verification downloads via
  the admin API. See the source headers for the exact endpoints.

### This is a real pass/fail test (not just a diagnostic)

- **`smoke.mjs` exits 1** if it errors or any sheet fails to *insert* a function (`failed > 0`).
- **`check.py` exits 1** if, for a formula filled on at least one sheet, any of:
  - **MISSING** — some sheet did not fill it (a dropped insertion/seed),
  - **DIVERGE** — the three sheets disagree (ok on one, error on another → an insertion-path bug, not a
    core bug — this is what caught the earlier dropped-`$BE$1` seed),
  - **UNEXPECTED** — it errors on *all* sheets but is not in `check.py`'s `ALLOWLIST`.
- A CI wrapper should therefore run both and gate on their exit codes; a silently-broken insertion path
  can no longer look green.

## Data

- `funcs.json` — the function inventory `[{en, cat, ru}]` (from the pinned Collabora source function arrays,
  minus the 9 dead `_ADD`/`_EXCEL2003` aliases).
- `menu-map.json` — `{localized_name → ribbon_button_id}` dumped from the live UI (the ribbon groups
  functions differently than the source category arrays, e.g. *Математические* holds 232, *Ссылки* only 5).

## Expected result

Every function **inserts** via every method (0 insertion failures). A small tail is inherently
non-computable in a static sheet and is expected to error on all three sheets identically — these are the
`ALLOWLIST` in `check.py`: by-design `#Н/Д` (`НД`, `ТЕКУЩ`, `ТИП.ОШИБКИ`), external (`ВЕБСЛУЖБА`, `DDE`,
`ДСВТ`), dynamic-array (`ФИЛЬТР`, `СОРТПО`, `LET`), and exotic add-ins/strict signatures (`OPT_*`,
`ПРЕДСКАЗ.ETS`, `ФУРЬЕ`, `ЦЕНАПЕРВНЕРЕГ`, …). Because the tail is the same formula on each sheet, any
per-sheet divergence points at an insertion-path bug, not a core bug — and now fails the test.
