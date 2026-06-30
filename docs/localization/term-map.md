# RU reference term map — where the data lives and how to rebuild it

The term map answers, for one reference language (RU first): **every term that may
need translation, its current value, where/under what circumstances it is seen on
screen, and how risky it is to translate** (simple / complex / composite). It is the
input to Stage 4 (collision map) and the per-term translation work in
`assisted_translate.md`.

Everything below is regenerable. The generated artifacts live under `.qa/` (gitignored);
the **tooling and this doc are tracked**, so the knowledge of where/how to get the map
survives even though the data dumps do not.

## The two halves

A term map needs a denominator (what *can* be translated) and ground truth (what is
*actually* on screen, and where). Neither alone is enough — see the `Clipboard` /
render-path caveat in `assisted_translate.md`.

| Half | What | Source | Generator | Artifact |
|---|---|---|---|---|
| **Universe** (denominator + current value) | Every translatable string + its current RU value + source class | client catalogs + LO core `.mo` in the running editor container | `scripts/build-l10n-catalog.py` | `.qa/ru-term-inventory/ru-catalog.json` |
| **Rendered** (ground truth + context) | Every visible term + where/under-what-circumstances it appears | live editor via Playwright (real input + the app command API) | `e2e/scripts/editor-l10n-rendered.mjs` | `.qa/ru-term-inventory/rendered/` |
| **Term map** (the join) | Universe ∪ Rendered, classified simple/complex/composite | reconcile of the two above | `scripts/build-l10n-ru-terms.py` | `.qa/ru-term-inventory/ru-terms.json` + CSVs |

## Where the source data is (and how to read it)

**Client catalogs** (flat `{english: translation}`, no msgctxt) — in the editor container:
- `/usr/share/coolwsd/browser/dist/l10n/ui-<lang>.json`   → source class `client-ui`
- `/usr/share/coolwsd/browser/dist/l10n/uno/<lang>.json`  → source class `client-uno`
- `/usr/share/coolwsd/browser/dist/l10n/locore/<lang>.json` → source class `client-locore`

**LO core gettext** (supports msgctxt + plural) — in the editor container:
- `/opt/collaboraoffice/program/resource/<lang>/LC_MESSAGES/*.mo` → source class `core-mo`
- `msgunfmt` is NOT installed in the image; we parse `.mo` with the Python stdlib
  `gettext` on the host (no container mutation). One module per file (`sw`=Writer,
  `sc`=Calc, `sd`=Impress, `cui`=shared dialogs, `svx`/`svl`/`vcl`/... = shared).

**Live render** (the only ground truth) — driven by Playwright against `http://localhost:8088`:
- Menus, dropdowns, submenus and context menus are server-drawn: they react only to
  REAL mouse/keyboard events, never to synthetic DOM events.
- Modal dialogs are opened via the app's own command API
  (`window.app.map.sendUnoCommand('.uno:FormatCellDialog')`) — reliable and locale-independent.
- Tooltips are not in the static DOM; their text is in the `data-cooltip` attribute on
  each control (harvested directly) and confirmed by a real hover pass.
- A modal dialog blocks every later `sendUnoCommand`, so each dialog must be closed
  before the next is opened. The titlebar close button is NOT reliably clickable
  (Playwright actionability times out); the working close is: focus the dialog
  (click its `.ui-dialog-titlebar`) then press Escape.
- Canvas grid / slide text is out of scope (not in the DOM).

Key live globals (same-origin `iframe[name=coframe]`): `window.app.map.sendUnoCommand`,
`window._` (client catalog lookup), `window._UNO` (UNO-command label lookup).

## Surfaces walked (per app: Writer / Calc / Impress)

`initial` · every notebookbar tab · every dropdown/dialog opener (`button[aria-haspopup]`)
+ one submenu level · per-object context menus (with preconditions: cell, column/row
header, sheet tab, selected text, …) · modal dialogs (curated `.uno:*` list) + each
inner tab · sidebar deck · tooltips (`data-cooltip` + hover).

Completeness is measured, not assumed: `scenario_manifest.json` (planned) vs
`run_manifest.json` (executed: `passed` / `failed` / `notReached` + machine reason).
`notReached` never disappears; measured coverage is an upper bound.

## Per-term record (`ru-terms.json`, plus CSV views)

```jsonc
{
  "en": "Insert",                         // english term (from the en baseline render)
  "ru_rendered": "Вставка",               // current value ON SCREEN (ground truth)
  "ru_rendered_variants": ["..."],        // present iff >1 distinct rendering (homograph)
  "ru_catalog": "Вставка",                // current value in the catalog (editable source)
  "source_class": "client-ui",            // client-ui|client-uno|client-locore|core-mo
  "classification": "simple",             // simple | complex | composite
  "reason": null,                         // mixed-render | render-path-mismatch | catalog-homograph | multi-source | space-fragment
  "render_mismatch": false,               // catalog translated but English on screen
  "occurrence_count": 3, "location_count": 1,
  "apps": ["calc"], "surfaces": ["ribbon-tab"],
  "contexts": ["Calc › Insert"],          // human paths where seen
  "occurrences": [ { "app","surface","path","precondition","scenario_id","control_id","field","ru" } ]
}
```

Classification (the user's simple/complex/composite = Stage 4 risk classes):
- **simple** = one place, one rendering, matches catalog, no mismatch, not a fragment → translate pointwise.
- **complex** = homograph on screen / render-path mismatch / >1 catalog value / multi-source → needs context split or manual decision.
- **composite** = glued at runtime (leading/trailing-space msgid or a known concat) → rewrite as a whole phrase, never translate in place.

## Rebuild (stack must be up: `./scripts/up.sh`)

```bash
# 1. universe (fast, deterministic) → .qa/ru-term-inventory/ru-catalog.json
python3 scripts/build-l10n-catalog.py --lang ru --out .qa/ru-term-inventory/ru-catalog.json

# 2. deep rendered walk (Playwright; run from e2e/, modules resolve there) → .qa/ru-term-inventory/rendered/
cd e2e && npm run ru-term-inventory

# 3. reconcile + classify → .qa/ru-term-inventory/ru-terms.json and CSVs
python3 scripts/build-l10n-ru-terms.py \
  --catalog .qa/ru-term-inventory/ru-catalog.json \
  --rendered .qa/ru-term-inventory/rendered/json \
  --out .qa/ru-term-inventory/ru-terms.json
```

CSV views written next to `ru-terms.json`:
- `terms.csv` - one row per English term.
- `occurrences.csv` - one row per visible occurrence of a term.
- `collisions.csv` - complex terms needing context decisions.
- `composites.csv` - template/fragment terms that should be handled as whole phrases.
- `unresolved.csv` - missing source-class or render-path mismatch rows.

Scaling to all 22 locales is Stage 5: rerun step 2 with the full `--locales` list and
join per language; the universe (step 1) takes `--lang <code>` per language.

Live counts are in each artifact's `meta` block (do not hardcode them here — they drift).
`e2e/scripts/probe-editor-dom.mjs` is the throwaway diagnostic used to discover the live
selectors above; rerun it after a Collabora re-pin if selectors change.

## Regression test (localization + layout)

Run after translating each block (did ONLY the intended terms change, nothing else broke?)
and during redesign (is everything present, visible, correctly laid out?). The deep walk now
also captures per-control geometry (`rect`, horizontal-`clip`, `clickable`, viewport `vw/vh`).

- `scripts/l10n-regression-check.py` — checks a candidate walk against a GOLDEN snapshot
  (per-control text changes), per-block EXPECTATIONS (`.qa/ru-term-inventory/expectations.json`:
  `expect: translate|keep-english`, optionally a pinned RU), and absolute LAYOUT rules
  (overlap of clickable controls, horizontal text clip, viewport-exit, zero-size; `--whitespace`
  adds large-gap detection for redesign). Report → `.qa/ru-term-inventory/regression/report.{md,json}`.
- `scripts/l10n-regression.sh [candidate_dir]` — one command: walk → check → report.
- `scripts/workflows/l10n-regression.workflow.js` — the Workflow form: runs the walk+checker,
  then spawns one Playwright agent per deviation to adversarially confirm it (false positives
  dropped, real breakage surfaced with a severity), then a synthesized confirmed report.
  Invoke via the Workflow tool: `Workflow({ scriptPath: "scripts/workflows/l10n-regression.workflow.js" })`.

Expectations model is **hybrid**: the golden snapshot catches any drift immediately; as each
block is translated you add its terms to `expectations.json` (they move from expected-English to
translated), so the test grows from "nothing should change" toward "this is the approved state".
The checker emits CANDIDATES; the Workflow (or a human, or Claude with Playwright) confirms each.
