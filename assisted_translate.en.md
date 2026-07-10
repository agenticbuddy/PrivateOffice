# Assisted localization of Collabora Online

This document describes a careful, tool-agnostic workflow for fully localizing a Collabora Online-based project with the help of an AI agent. By "agent" we mean any assistant that can read the project, run commands, and verify the result.

The main idea: localizing Collabora Online is not just about filling in the missing keys in JSON. First, you need to understand where exactly each English string is used, which mechanism translates it (ui-json / uno-json — client catalogs, lo-core-mo — compiled core catalogs, different layers of the render-path), and whether it has different contexts (the same string on different screens or in different dialogs may require different translations), and only then make targeted edits.

The danger lies in a false-positive result: if grep finds a translation, it does not mean it is rendered on screen. Editing one screen may break another.

A separate emphasis — controlling the AI agent. The agent may confidently claim that it "checked all languages" or "built a complete table," but in practice it often samples: a few languages, a couple of tabs, the first grep matches, part of the catalogs. Therefore, the result is accepted only when the agent has left verifiable artifacts: a machine table (a structured data file, for example CSV/TSV, not text in the response), a manifest of scenarios (a list of the screens and steps that were checked), a list of input files with hash, screenshots, DOM/text dumps (dumps of text from the page or of the DOM tree), reproduction commands (the exact commands to repeat the check), and numbers that can be recomputed independently.

## Short summary

An untranslated string in `ui-*.json` is not a "fill in the translation and close it" task. A single English `msgid` can occur in different places in the interface and require different translations there (context collision). Some labels don't come from `ui-*.json` at all, but from UNO (LibreOffice internal commands/properties) or from the LibreOffice-core core, — the source has to be identified. Some values (formats, technical terms, function names, brands) are better left in English. A linguistically correct translation can break the UI: button width, RTL layout, tooltip, menu, dialog. Finally, a translation may already be in the catalog but not appear on screen, because the string is drawn by a different layer (a different stack level responsible for rendering), — and the stock LibreOffice language pack must not be dropped in blindly, since Collabora differs from it.

Almost all localization, texts, sizes, and design of the interface elements are achievable without building the LibreOffice core — they live in the Collabora Online layer (data + CSS + a bit of code). Building the core is only needed for rendering the document itself.

The correct path:

1. Collect all English strings.
2. Collect all places where each string occurs.
3. Split the strings by source: `ui-json` (interface texts), `uno-json` (UNO commands/properties), `lo-core-mo` (LibreOffice core strings), frontend i18n, generated/composed text (text assembled from parts on the fly), unresolved (source not identified).
4. Build a map of contexts and possible collisions.
5. Translate the safe cases first.
6. For risky cases, do context splitting (different translations of one `msgid` by place of use) or edit the correct source: PO/MO (LibreOffice translation catalogs) or UNO.
7. Verify every edit by render (open the screen and look at the rendering), not just by grep over files.

## What exactly is hard

In an ordinary application there is often a single localization layer: the code calls `t("Save")`, the catalog stores the translation, the interface shows the translation.

In Collabora Online there are more layers:

| Layer | What lives in it | How it is usually fixed |
| --- | --- | --- |
| Application frontend | The project wrapper around Collabora: login, files, profile, modals | `frontend/src/i18n/messages/*.json` |
| Collabora browser UI (web interface: ribbon, menus) | Ribbon/notebookbar, part of the menus, tooltips, panels, buttons in the web code | `ui-json` — data in `editor/l10n/overrides/client/<lang>.json`, merged at build |
| UNO command labels (LibreOffice command labels) | LibreOffice command labels that Collabora calls via `_UNO(...)` | `uno-json` — `l10n/uno/<locale>.json` or the generation source of these catalogs |
| LibreOffice-core (the core) | Dialogs, server/core UI, `.ui`, gettext, some sidebar and dialog strings | `lo-core-mo` — `.po` (gettext source) -> `.mo` (compiled catalog), then rebuild the image |
| Composite strings | Phrases assembled from several translatable or non-translatable pieces | Rewrite into a single phrase with placeholders |
| System elements | Browser menus, OS-native elements, some file picker/clipboard prompts | Usually outside the application's control |

Editing the wrong layer is useless: editing `lo-core-mo` will not help a string from `ui-json`, and vice versa. That is why you must first determine the source.

The presence of a string in a catalog does not mean the text is taken from there. Example: the string `Clipboard` is present in the client-side `ui-ru.json` with a Russian translation, but the ribbon shows it in English — because that label is drawn by the core, and the client catalog is not used here. The real source is confirmed only by experiment: change the string in the candidate catalog, rebuild, clear the cache, and see whether the screen changed.

One English string may reside in several layers at once; which one actually draws the text is decided by the render path (the path by which a string is rendered onto the screen; determined by experiment, see the "Base terms" section), not by the fact that the string exists in a catalog. In practice most of the gaps were in the client JSON, not in the core — so look there first.

## Why adding a translation directly is dangerous

The same English key may require DIFFERENT translations depending on where it is used, which is why dictionary-style translation by text is dangerous.

Consider the key `Illustrations`. As the name of a ribbon group, the translation `Иллюстрации` is correct. But if there is a composite message:

```text
No + Illustrations
```

then a word-by-word translation gives:

```text
Нет Иллюстрации
```

whereas the correct form is:

```text
Нет иллюстраций
```

English (an analytic language) tolerates short dictionary chunks assembled by concatenation. Inflectional languages — Russian, Ukrainian, and many other languages with declension — suffer more from this kind of message slicing: the grammar breaks (declension, agreement).

Checklist of risky ambiguous words:

| English string | Why it is risky |
| --- | --- |
| `Line` | Line as a shape, a line of text, a border, a chart line, a menu command |
| `Table` | Table as an object, an insert command, a style, a tab, a group |
| `Field` | Form field, data field, pivot table field |
| `Function` | Calc function, insert-function command, function-library section |
| `Range` | Cell range, area, named range |
| `General` | General number format, general settings section, normal mode |
| `Delete` | Delete an object, delete a row, delete a sheet, delete a comment |

Conclusion: tie the translation to the context and place of use (which screen, dialog, role of the string), not just to the English text.

## Base terms

| Term | Meaning |
| --- | --- |
| `msgid` | The English source string or the key by which a translation is looked up |
| context | The environment of a string: application, tab, group, command, tooltip, neighboring words |
| collision | One `msgid` is used with different meanings |
| composed fragment | A string that is part of a phrase rather than a self-contained phrase |
| source class | The layer (or layers) of localization where the string lives: `ui-json` (client catalog), `uno-json` (UNO-command catalog), `lo-core-mo` (compiled PO/MO of the LibreOffice core), frontend i18n. Several layers may exist at once; which one actually renders the text is determined by the render path |
| render path | What actually renders the string on screen: the client `_()`, the server-side JSDialog from the core, or UNO (the API for calling editor functions). Unlike source class, it is determined by experiment (rendering), not by the string's presence in a catalog |
| rendered proof | Proof through the browser: a screenshot, DOM/text inventory (collecting the actual text from the DOM), the UI state. Render is the only truth |
| baseline | The recorded state before an edit (image version, catalogs, screenshots, string lists) as a reference point |
| target locale | The language that must be checked or additionally translated |
| plural form | A word form that depends on number. Russian has 3 forms (1 файл / 2 файла / 5 файлов) |

## General workflow

Split the work into stages; do not start with mass editing of translations.

Stage order:

1. **Preparation.** Identify the edit zones and tools: client text — `ui-json` (client JSON strings); UNO commands (internal commands of the LibreOffice engine) — `uno-json`; core — `lo-core-mo` (compiled PO/MO — source/binary translation catalogs). Understand that a string reaches the screen via its render-path (the layer responsible for rendering), so the presence of a string in a catalog does not guarantee that it is shown.
2. **Editing translations** in the source files of the corresponding zone.
3. **Verification.** Ground truth is render only: check each element on the live screen (Playwright), not against the catalog.

The completion criterion is 100% of translated strings confirmed by render in each zone.

## Inventory tooling (implemented)

The inventory of terms with Russian as the reference is built and reproducible. Rebuild commands and details — `docs/localization/term-map.md`. Three tools:

- **The universe of the translatable** (`build-l10n-catalog.py`) — every string that can be translated at all (client `ui/uno/locore` + core `.mo`), with the current RU and the source class (source class — where the string lives: client ui/uno/locore, core `.mo`). This is the denominator of completeness.
- **Deep render walk** (`editor-l10n-rendered.mjs`, Playwright) — traverses all UI surfaces of all applications, captures the visible text, geometry and context (`app/surface/path/precondition` — application/surface/path/opening precondition) and honestly logs `notReached` (unreachable surfaces).
- **Term map** (`build-l10n-ru-terms.py`) — joins the render with the universe and classifies each term: **simple** (one place, one render, matches the catalog), **complex** (homonym / render-path-mismatch — the render diverges from the catalog / >1 catalog value / multi-source — from several sources), **composite** (glued from fragments). Result: `ru-terms.json` + CSV.

The classification determines the translation strategy.

### How to use this while translating

1. `simple` → translate it pointwise in the appropriate source class.
2. `collisions.csv` (complex) → resolve by context (the render variants and usage sites are visible), splitting keys where necessary. `composites.csv` → rewrite as a whole phrase, not piece by piece.
3. After each block — the regression test `scripts/l10n-regression.sh`: it confirms that only the intended thing changed, nothing broke elsewhere, and the geometry is intact (no overlaps / clipping / going beyond the viewport / zero size). Expectations are maintained in `expectations.json` on top of the golden snapshot (reference snapshot): a term moves from "should stay English" to "translated" — this is how progress is tracked and regressions are caught.

Completeness is counted against the catalog denominator, but is verified by what actually renders (render walk + `notReached`), not by the presence of a string in the catalog.

## Principle of provability

The only ground truth is what is actually rendered on the screen (a screenshot). A JSON catalog, grep, `.mo`, and the fact that `_("...")` is called in the code prove only that the translation *may* apply, not that it applied here. Example: `Clipboard` is in `ui-ru.json`, but renders in English.

Therefore the source and translation of each string are confirmed by a pass **over every object** of the interface (not over a sample): tab, group, button, menu, context menu, dialog, tooltip — with a screenshot for each block. There are two passes: the first collects, the second (preferably a different, stronger model that re-checks what was collected) looks for errors in the screenshots.

The stage ends not with the word "done" but with a set of machine-readable artifacts from which another person/agent can recompute the result. An answer like "checked all strings, found 20 problems" is not acceptable: it is unclear which files, which languages are in scope, where the rest of the strings are, whether this is a full pass or a sample, whether it is reproducible after an image update.

The result is re-checkable if from it one can:

- open the input file by hash and confirm the version is correct;
- recompute the number of strings with a different script and reconcile with the number in the report and in JSON/CSV;
- for any `msgid` (translation string identifier), find all its occurrences (places of use in code/interface);
- match any screenshot with a DOM/text dump;
- see uncovered places.

Cache trap: the render check is done with cache-bust/hard-reload and in a clean browser profile. Some assets (the branding script and the runtime catalogs `ui-<loc>.json`) bypass the usual cache-bust — the assets are cached under an unchanging hash, and it is easy to mistake the old screen for the result of a fix. Therefore additionally verify with a request that bypasses the cache.

### Anti-patterns (do not count as proof)

- a general text answer without raw tables; manual conclusions without a machine-readable artifact;
- screenshots for only one language when "all languages" is claimed;
- grep output without a list of files and extraction rules;
- a "found everything" report without a total entity count; a "top missing" table instead of the full one;
- translation without all occurrences; a patch without justification of the chosen source class (the type of string source: `ui`/`uno`/`locore`/`.mo`);
- a Playwright check without a scenario manifest; the absence of errors as proof of completeness;
- the presence of a string in the catalog (`ui/uno/locore-*.json` or `.mo`) as proof of its display;
- render without cache-bust/hard-reload; a single cache reset as a guarantee of freshness.

The catalogs are distinguished because a string comes from different sources: `ui` — client UI (ribbons, menus), `uno` — UNO commands (internal LibreOffice command identifiers), `locore` — LO core, `.mo` — compiled LibreOffice PO/MO catalogs. They must not be mixed: coverage and patch are specific to each.

### Minimal set of verifiable artifacts

| Stage | What the agent leaves | How to verify |
| --- | --- | --- |
| Baseline | `baseline_manifest.json` with languages, applications, files, hash, container versions | Recompute hash, compare languages with the project code, check that files exist |
| Static extraction | `occurrences.json`, `coverage.csv`, `unresolved.csv`, the extractor run command | Re-run the extractor, recompute regex/AST matches, check random strings |
| Rendered inventory | `scenario_manifest.json`, screenshots, DOM/text dumps, trace/log | Check that all locale/app/state pairs are present, open sample screenshots |
| Collision map | `collisions.csv` with all `msgid`, risk class and occurrence ids | Check that each `msgid` is classified exactly once |
| Translation candidates | `translation_candidates.csv` with source, context, confidence, reason | Check that there are no hard cases and no unresolved |
| Patch | diff, list of approved candidate ids, changed keys | Check that the diff changes only permitted source classes |
| Verification | before/after inventory, screenshots, failures, false positives | Compare with the patch list, check for the absence of new conflicts |

Notes on the columns: coverage/collision map — tables of string coverage and collisions; risk class — the risk class of a replacement (`single-use`, `same-context multi-use`); direct `_()` matches — direct calls of the translation function in the code. The numbers in the artifacts (the number of unique `msgid`, UNO commands, occurrences, the product locale×app×state) are not magical: each is obtained by recomputation from the corresponding input file and must reconcile on re-check.

### Completeness invariants

For each stage the numbers must reconcile:

- the number of languages in the report = the number in `backend/app/services/locales.py`; for each language there is a row in the coverage table;
- each `msgid` from the occurrence map has ≥1 occurrence referencing an existing file, offset, selector, or screen state;
- each rendered English leftover is linked to the occurrence map or marked `unresolved`; each `unresolved` has a reason and a next step;
- each safe candidate (a candidate for a safe replacement) has risk class `single-use` or `same-context multi-use`; a hard case (an ambiguous case — repeated use in different contexts) requires a human decision or is explicitly left unresolved;
- each changed translation has an approved candidate id; each patch key, after the build, is actually present in the active container;
- each changed UI-state has a before/after screenshot or text dump.

If the invariants do not reconcile, the work is not finished, even with a coherent report.

### Stage 1. Fix the baseline

The baseline fixes exactly what is being localized:

- the project version; the Collabora Docker image version;
- the list of all supported languages;
- for each language — the chain of codes: code in the application -> code in the `lang` parameter -> the catalog file actually loaded;
- applications: Writer, Calc, Impress, and Draw if needed; interface modes, if there are several designs;
- the active `bundle.js`, `l10n/ui-*.json`, `l10n/uno/*.json`, `l10n/locore/*.json`; LO resources `.po`/`.mo`/`.ui`, if available;
- test documents for Writer/Calc/Impress; UI states: ribbon tabs, menus, context menu, sidebar, dialogs, tooltips, formulas, tables, charts, pivot tables, images, shapes.

The chain code -> `lang` -> catalog is checked for each language separately. Example: the user selects `ru` -> the application passes the code in `lang` (mapping in `co_lang`: `ru` -> `ru-RU`) -> the editor normalizes the region and loads `ui-ru.json`. An incorrect code (or an extra region) causes the editor to silently fail to load the catalog or to load the wrong one — the language will appear untranslated even though the catalog is on disk; sometimes individual strings also change (the language label, a placeholder like `{ru}`). This is a frequent invisible cause of zero coverage.

Control not based on trusting the agent:

- Request `baseline_manifest.json`, where each row is a concrete input: path, source, size, hash, extraction date, container/commit.
- Recompute the list of languages from the code and compare with the manifest: if the project has 22 languages, the manifest has 22, not "the main ones".
- For each language check which catalogs actually exist (`ui`, `uno`, `locore`, `.mo`); the absence of a catalog is an explicit row in the table, not a silent skip.
- The scope of applications is listed explicitly (Writer, Calc, Impress, shared, and Draw if needed), and excluded ones too.
- Container files are taken from the active image; the proof is the extraction command and the file hash.
- For each language check via network which catalog file the browser actually requested (not which was expected). If none was requested — a hidden cause of zero coverage.

Catch-up is done as a delta, without rewriting the whole report: extend `baseline_manifest.json`, add all languages from `locales.py`, for each indicate the presence of ui-json/uno-json/locore-json/`.mo` and hash/size, output a separate table of missing catalog files, change nothing in the code. The completion criterion is exactly N locale rows, each with the same set of columns.

### Stage 2. Static string inventory

The agent reads the code and catalogs, but rendering is not yet proven. Collect: all `_()` strings; all `_UNO(...)` commands; frontend i18n strings; strings from `ui-*.json`, `uno/*.json`, `locore/*.json`; all LibreOffice PO/MO/UI resources (PO/MO — the text/compiled gettext translation catalog); all places of use of each string.

The key result is the occurrence map: a single machine-readable registry of all occurrences of each English string. Its stable ids are later referenced by the patch, collision map, and verification, so the main artifact is `occurrences.json`/`occurrences.csv`, not Markdown (Markdown is allowed only as a brief summary with a link).

Minimal fields of the occurrence map:

| Field | Why it is needed |
| --- | --- |
| `msgid` | The English string |
| `source_class` | The layer-catalog where the string is declared: `ui-json`, `uno-json`, `locore-json`, `lo-core-mo`, frontend i18n, unresolved (source not found). There may be several values at once |
| `app` | Writer, Calc, Impress, shared |
| `file` | File or bundled segment |
| `line_or_offset` | Where it was found |
| `call_type` | `_()`, `_UNO(...)`, frontend `t()`, generated |
| `control_type` | tab, group, button, tooltip, menu, dialog, message |
| `neighbor_text` | Neighboring words or phrase |
| `command_id` | UNO command id (engine command identifier) or control id, if any |
| `is_fragment` | The string is a piece of a phrase (`_("x")+var`, templates); fragments cannot be translated as a whole, they are marked for manual assembly |
| `render_path` | The layer that actually renders the string on the screen (render-path): `client-_()`, `server-jsdialog-core`, `uno`. Unlike `source_class` (where the string resides), it is confirmed only by experiment |
| `notes` | What to check manually |

`render_path` must not be filled in by guessing from the catalog. It is confirmed by experiment: change the string in the presumed source, rebuild the image, reset the browser cache, and see whether the screen changed. If it changed — the source is correct; if not (like `Clipboard`: it resides in `ui-ru.json`, but is rendered by the core) — the source is different, and editing this catalog is useless.

A string from the screen cannot be compared literally with the catalog. Before comparing, normalize both:

- remove mnemonic markers (`~`, `_`);
- remove the trailing ellipsis (`…`, `...`);
- remove the hotkey hint at the end (`(Ctrl+S)`);
- remove the trailing colon;
- compare strings with substitutions (`{1}`, `%1`) as a template via a regular expression.

Without normalization one string looks like several, and a false "not translated" appears. Core strings in `.mo` must first be unpacked into text (`msgunfmt`, the gettext package).

The coverage table (a translation is present in the catalog → the string is considered translated) is an upper estimate, a hypothesis, not a fact: presence in the catalog does not mean it is the one that renders the text. The percentage is confirmed only by the render pass (Stage 3). It is mandatory to take a sample of strings counted as translated and reconcile them with the actual screen.

Requirements for artifacts:

- `occurrences.json`/`csv` with ALL occurrences (not a sample), each with a stable `occurrence_id`.
- For each `msgid` — `occurrence_count` and ALL places of use (not the first few).
- For each `source_class` — a separate count; the sum over source_class reconciles with the overall total (`extraction_stats.json` with raw counts: `_()`, `_UNO(...)`, frontend keys, catalog keys) or explicitly shows the overlap.
- For `unresolved` — not "unknown" but a field `why_unresolved`: no command map, minified dynamic call, generated text, runtime-only, source outside the bundle.
- `coverage.csv`: a row for each target language, statuses missing/same/translated.
How to check the completeness of the artifact (without trusting the agent):

- With a different command, recompute the `_()` strings and `_UNO(...)` command ids, reconcile with the counts.
- Manually open 20 random occurrence ids and check the source location.
- Take 20 random `msgid` with `occurrence_count > 1` and check that ALL places are listed, not the first ones.
- Check that `coverage.csv` has a row for each language with statuses missing/same/translated.

Signs of partial/fake execution: only the top-20 missing shown; only `ui-*.json` counted without `uno`/`locore`; "found everything" claimed without an extractor command; `msgid` not distinguished from visible text; counts present but no raw rows; a string with several occurrences shows one file.

The report of the browser render check (occurrence map = a map of where each UI string was encountered, with occurrence_id; rendered inventory = what is actually rendered on the screen) contains:

1. English leftovers.
2. Strings that are not in the static map (the static string map from the catalogs).
3. False positives: English values that probably should remain English.

Each English leftover is linked to an occurrence_id or marked `unresolved` — this is the completion criterion.

**Control (not based on trust in the agent).** Before the run — `scenario_manifest.json`: a full list of `locale x app x state x action` pairs. After — `run_manifest.json`: for each scenario id a status (`passed`/`failed`/`skipped`), time, paths to the screenshot and text dump (a text snapshot of the screen content). `skipped` is not allowed without a machine-readable reason: missing fixture, feature unavailable, selector timeout, known out of scope.

- Each `state` is a stable meaningful name (`calc.formulas.function-library-open`, not `screen5`).
- For a dropdown/tooltip an action log is needed, proving that the menu was actually opened.
- Each screenshot must have a paired text dump: it is precisely what enables an automatic diff and a list of English leftovers for comparison with the manual report.

**Independent checks.** The number of rows in `run_manifest` == the number of rows in `scenario_manifest`. For each `passed` there is both a screenshot and a text dump. `failed`/`skipped` do not disappear from the report. Selectively open several screenshots and confirm the language is correct, not a reused image.

**Non-obvious signs of incompleteness.** No `failed`/`skipped`, although a real run almost always yields at least a timeout or out-of-scope. Tooltip/context menu are claimed as checked, but there is no action log.

**How to finish (delta-run).**

```text
Do a delta-run:
1. Build scenario_manifest.json for all supported languages, Writer/Calc/Impress and all declared states.
2. Compare existing screenshots/text dumps with the manifest.
3. Build missing_scenarios.csv.
4. Run only missing_scenarios.
5. Update run_manifest.json, not deleting failed/skipped.

Completion criterion: run_manifest covers 100% of scenario_manifest, each English leftover is linked to an occurrence_id or an unresolved_id.
```

### Stage 4. Collision map

After the static and render inventory, determine which strings are safe to translate.

Risk classes (source class = the class of the string source):

| Class | What it means | Automatic translation |
| --- | --- | --- |
| `single-use` | One `msgid`, one context | Usually yes, after a check |
| `same-context multi-use` | Several places, one meaning | Usually yes, if the translation fits everywhere |
| `mixed-context` | Several places with different meanings | No, splitting or a manual decision is needed |
| `composed-fragment` | A piece of a composed phrase | No, rewrite into a whole phrase |
| `source-mismatch` | Visible in the UI, but the source is not the expected one | No, first determine the source |
| `core-only` | A string from LibreOffice-core | Via PO/MO (gettext catalogs of the core), not via ui-json (flat client JSON) |
| `technical-name` | Format, function, brand, command name | Often keep in English or reconcile terminology |
| `layout-risk` | The translation does not fit or breaks layout/RTL/bidi | Only with a visual check |
| `render-path-mismatch` | The string is in the expected catalog, but is rendered from another layer (render-path = the rendering path), example `Clipboard` | No: editing the catalog does not help, fix the actual rendering layer |
| `plural-form` | Number-dependent forms (1/2/5 in ru, 6 forms in ar) | Via gettext plural in the core; flat JSON does not express them |

RTL locales: separately check direction and layout (`dir`, menu position, overflow) — accounted for in `layout-risk`.

**Command to the agent.**

```text
Split all English msgid into risk classes based on the occurrence map and rendered inventory.
Account for all occurrences, different grammar and RTL, separately single out composed phrases.

Result:
1. A collision map table.
2. For each msgid: risk_class, occurrence_count, list of contexts, affected locales.
3. Safe candidates for auto-translation.
4. Hard cases for a human — with an indication of why a JSON edit is dangerous.
```

**Control (not based on trust in the agent).**

- The collision map covers ALL `msgid` from the occurrence map, not only the problematic ones; each row references an `occurrence_id` (otherwise the class is not proven).
- `single-use` — exactly one occurrence id.
- `same-context multi-use` — several ids and an explanation of why the context is the same.
- `mixed-context` — different context groups listed.
- `composed-fragment` — a fragment pattern: which pieces are joined and where it is visible.
- `technical-name` — why English is acceptable (file format, API-name, function, brand).

**Independent checks.** `set(msgid)` from `occurrences.json` == `set(msgid)` from `collisions.csv`, the difference is empty. Strings with `occurrence_count > 1` did not automatically fall into `single-use`. Rendered leftovers also received a risk class, rather than remaining only in the QA report.

**How to finish.**

```text
Take the full set of msgid from occurrences.json and the current collisions.csv.
Build missing_collision_rows.csv; for each row add risk_class,
for occurrence_count > 1 add context_groups. Do not propose translations.

Completion criterion: set(msgid) in occurrences.json is fully equal to set(msgid) in collisions.csv.
```

### Stage 5. Preparing translations

Prepare the translation as a controlled table, not as free text. For each candidate: the English `msgid`; context; source class; the current translation per language; the proposed translation; the source of the proposal (an existing LO translation, the current catalog, the term base, manual, AI); status (`safe`/`needs human`/`rejected`/`accepted`); notes on grammar/length/RTL.

Ask not "translate everything" but "propose candidates, but do not apply".

**Command to the agent.**

```text
Prepare translation candidates, do not change files.

- Use ONLY single-use and same-context multi-use.
- Do not touch mixed-context, composed-fragment, core-only and unresolved.
- Account for the UI context for each language.
- When unsure, set needs human, do not guess.

Result:
1. A translation candidates table.
2. For each msgid: context, source class, affected locales, proposed translation, confidence, reason.
3. Strings that cannot be translated automatically.
4. Terms requiring a unified glossary.

Completeness control:
- Hard cases do not enter the table.
- Each translation has a reason.
- Each language has a status: proposed, existing, needs human, keep English.
```

### Stage 5 (completion). The safe candidates matrix

From the filtered safe candidates a translation table is built. Control is not based on trusting the agent — the result is checked, not the claims.

**Format.** `translation_candidates.csv` references `msgid`, `risk_class` (the risk class of the string), `occurrence_id` (the id of the place of use), `source_class` (the class of the string source) and `locale`. Each row has a status; an empty status = the work is not finished.

**Provenance.** A translation without `source` and `reason` is not accepted. `source` is one of: `existing-locore` (a ready translation from LibreOffice-core), `existing-uno` (from UNO — engine commands/actions), `LibreOffice-po` (from a LibreOffice .po catalog), `glossary`, `human`, `ai-proposed`. `ai-proposed` has reduced trust until a human approves it; for unverified strings the status `needs human` is mandatory, with a concrete question to the human, not an imitation of confidence.

**Separation of proposed and applied.** The candidate table itself does NOT change localization files — edits go only after an explicit human choice.

**Notes.** For long translations — a layout note: the risk of overflow, a screenshot and a shortened variant are needed. For RTL — a note on the order of placeholders, punctuation, direction.

**The matrix as a completeness criterion.** A `msgid × locale` matrix is built; each cell has a status `existing` / `proposed` / `needs human` / `keep English`. There must be no empty cells. No hard-case string (mixed-context / unresolved / collisional) enters `proposed` without human approval.

**Independent batch checks:**

- risk_class of all strings is `single-use` or `same-context multi-use` (single-use / multi-use in one context), if the task is only about safe candidates;
- in a batch for `ui-json` (the browser JSON catalog of the client UI) there are no strings with source_class `lo-core-mo` (the compiled LibreOffice core .mo);
- each locale has a status for each candidate;
- glossary terms are used consistently;
- 20 random translations are checked against the occurrence context.

**Completion criterion:** there are no empty cells in the matrix, and no hard-case string entered `proposed` without human approval.

### Stage 6. Handling hard cases

Strings filtered out of the safe table as hard cases (collisions, composed phrases) are handled separately: the agent prepares a decision package for the human. It changes nothing, only proposes.

**Package contents:** `decision_id` (so that a future patch references the approved decision, not free text); where the string is visible; all occurrences; the reason for the collision; affected languages; ranked options with pros and cons; what to change in the code or catalogs; a verification plan (tests + screenshots).

**Requirements for options.** Provide 3–5 ranked options (up to 20 — only if there is no simple path), from the most realistic. Each option:

- lists the affected occurrence ids;
- for a split key (splitting one key into several) shows the map `old occurrence ids → new key ids`;
- for edits to PO/MO/UNO (see source classes) justifies why the client `ui-json` is not the source (core/UNO strings do not live in browser JSON);
- for `keep English` explains why this is acceptable: a term, a brand, a technical name, no safe context;
- lists new risks: collisions, fallback, layout, RTL, migration, rollback.

The recommended option is indicated separately, but without implementation.

**Package completeness checks:**

- all occurrences are covered by at least one option;
- the recommended option covers not only the "easy" part of the occurrences;
- split keys do not create technical fallback strings in the English UI;
- each option has a verification plan;
- the human explicitly chooses an option before any edits.

**Completion criterion:** the human can choose an option without asking clarifying questions about where the string occurs and what will break.

## How to make targeted edits

The common template for agent commands below is the same (Task / Context / Result / Completeness check); each section lists only the differences. General control principle: don't take the agent's word for it — every step is confirmed by an artifact (approved list, git diff, before/after catalog, occurrence map, rendered scenario). Terms: `occurrence` — a specific place where a string is used in the code; `single-use` — one occurrence; `same-context multi-use` — several occurrences with a single meaning; `mixed-context` — one string in different meanings; `composed-fragment` — a string that is a piece of a composite phrase; `same-as-English` — a translation that intentionally matches the English. String catalogs: `ui-json` — client UI (buttons, menus), `uno-json` — UNO commands, `lo-core-mo` / `locore-*.json` — LibreOffice core; a string's membership is determined by its source in the code.

### Safe direct `ui-json`

You may edit directly if the string: comes from `ui-json`; is `single-use` or `same-context multi-use`; the translation fits all occurrences equally; is not a composite phrase; does not break width/RTL; has a render-check plan.

Edits are placed as DATA in `editor/l10n/overrides/client/<lang>.json`; at the build step the deployed image (`editor/Dockerfile.online`) merges them into the active `ui-<locale>.json` (`editor/Dockerfile` — stopgap/fallback only). Do not manually edit the already-built file in the container — otherwise the edit is not reproducible on rebuild.

The approved list of safe candidates (`approved_ui_json_candidates.csv`) is prepared before editing: it collects strings that passed the criteria above; the agent works only from it.

Agent command:

```text
Ты исполнитель точечной localization-правки.

Задача: внести только safe direct ui-json переводы.

Контекст:
- Разрешены ТОЛЬКО msgid из approved_ui_json_candidates.csv.
- Не трогай mixed-context, composed-fragment, uno-json, lo-core-mo.
- Клади переводы как данные в editor/l10n/overrides/client/<lang>.json.

Результат:
1. Минимальная правка.
2. Список добавленных ключей по языкам.
3. Обновленный WAL/update-log.
4. Команды проверки.
```

Independent checks (not based on trusting the agent):

- `set(keys in diff)` minus `set(approved candidates)` = empty; the diff changes only the allowed files and keys.
- After the build, extract the active `ui-<locale>.json` from the container and prove that the key actually appeared there, and not only in the source patch (compare the before/after catalog).
- The value did not overwrite a newer or different existing translation in this language.
- `same-as-English` is not mistakenly counted as "not translated".
- The UI does not display technical keys; for each key there is a rendered scenario (id of the rendered screen as proof) or a reason why rendering is impossible in this batch.

If the patch is broader than scope:

```text
Патч шире утвержденного scope. Откати только свои изменения этого batch и пересобери patch.
Разрешено менять ТОЛЬКО keys из approved_ui_json_candidates.csv.
Выведи таблицу: approved key | changed file | old value | new value | rendered scenario id.
Критерий завершения: git diff содержит только разрешенные ключи; update-log описывает только этот batch.
```

### Context separation in code

One `msgid` in different meanings cannot be separated with a single translation. Programmatic context (`msgctxt`/`pgettext`) exists only in the core (`.po`/`.mo`); client catalogs are flat "English string -> translation" dictionaries without technical context. Therefore a homonym on the client is separated only via different keys — by editing the call in the code.

Solutions:

1. If context is unavailable on the client — add a context helper that looks up a hidden context key but, for the English fallback, shows a normal English string.
2. Replace the composite string with a whole phrase using placeholders.
3. Do not split a string from UNO/core into the browser JSON — fix the UNO/LibreOffice source.

The English fallback must NOT display technical keys. Bad: `_("Line|shape-tool")` — with no translation the user sees `Line|shape-tool`. Better: `translateContext("shape-tool", "Line")`, where the fallback remains `Line`.

Agent command (differences from the common template):

```text
Ты разработчик контекстной локализации.

Задача: минимальный способ разделить конфликтующий msgid без поломки английского fallback.

Контекст:
- Один английский текст в нескольких разных смыслах; простая запись в ui-json небезопасна.
- Сохрани нормальный английский интерфейс при отсутствии перевода.

Результат:
1. Предложение API/helper или существующий механизм контекста.
2. Места замены вызовов и новые контекстные ключи.
3. Fallback behavior.
4. План миграции переводов, тесты и рендер-проверки.
```

Independent checks:

- Before the code edit — the `split_plan.csv` table: old msgid, old occurrence ids, new key, new context, fallback.
- After the edit, rebuild the occurrence map (occurrence -> key mapping, built by walking the code) and prove that each old occurrence is either assigned to a new key with exactly the context it was created for, or is explicitly documented keep-old; the old msgid is no longer used in the conflicting place.
- The English UI without translation shows normal text, and not `Line.shapeTool` or `shape-tool|Line`.
- New keys do not collide with existing keys of a different meaning.
- Placeholder order is checked for languages with a different word order; rendered scenarios are run for ALL old places, not just one.

If the split is incomplete:

```text
Контекстный split неполный. Новые переводы не добавляй.
1. По split_plan.csv для каждого old occurrence id покажи, куда он попал.
2. Построй missing_or_unsplit_occurrences.csv и исправь только эти места.
3. Пересобери occurrence map.
Критерий завершения: все old occurrence ids имеют new key или documented keep-old reason.
```

### UNO and LibreOffice-core

`_UNO(...)` strings and LibreOffice-core require special care; a simple `ui-json` edit for them is forbidden.

The correct path:

- find the source UNO command or LO resource, check for the presence of a PO context;
- edit the PO, not the binary `.mo`; build the `.mo` via the gettext toolchain;
- do this at the image build step (Dockerfile), not in a running container — otherwise the change is lost on recreation;
- `gettext` (`msgfmt`/`msgunfmt`) is usually not included in the image — install it;
- make sure Collabora actually uses the new resource, and check all commands with the same English text.

Agent command (differences from the common template):

```text
Ты специалист по LibreOffice/UNO локализации.

Задача: подготовить план исправления строки из uno-json или lo-core-mo.

Контекст:
- Простая правка ui-json ЗАПРЕЩЕНА.
- Найди правильный источник: UNO map, PO, MO, UI resource или generator.
- Не сломай другие команды с таким же английским текстом.

Результат:
1. Источник строки и способ правки (PO, не .mo).
2. Шаг сборки .mo и внедрения в образ.
3. Доказательство, что Collabora использует новый ресурс.
4. Проверка всех команд с тем же английским текстом.
```

Independent checks:

- The diff changes the PO source, not the binary `.mo`; building the `.mo` is done at the image step.
- The active resource in the container contains the new translation (compare before/after).
- All commands with the same English text are checked on render and are not broken.

## Editing UNO/core strings: control and refusal

Before changing anything, the agent is required to show the full **source chain** — the chain from the visible text to the file in the built image:

1. visible text and screen state (where the string is visible);
2. command/dialog id — the UNO command or dialog where it is used;
3. source catalog: PO/UI file (**PO/MO** — gettext translation catalogs) or generator;
4. build command for rebuilding the `.mo` or **uno-json** (the generated UNO string catalog);
5. active container path — the path in the active container/image;
6. all other occurrences of this `msgid` in UNO/core;
7. rollback plan.

No chain — no edit.

Requirements for the plan:

- Do not edit `.mo` manually as the primary path.
- Do not edit **ui-json** (the client string catalog) if the string comes from **core** (the LibreOffice engine/dialogs). Determine this from the source chain (steps 2–3): if the id is an engine command/dialog, the source is core, not ui-json.
- Check the `msgctxt` (the string context) in the `.po`/`.mo`: a single `msgid` may occur in several contexts — you cannot change them all at once without analyzing collisions.
- Check not the `.mo` file, but the **render** — the visible UI: Collabora may take the string from the generated uno-json or another cache (render is the only ground truth).
- Find ALL occurrences of the same English text in UNO/core, not one screen.

What the human verifies independently of the agent (machine-checkable artifacts):

- `msgunfmt` (a gettext tool) shows the expected `msgid`/`msgstr` in the resulting `.mo`.
- The diff of the resulting `.mo` against the **baseline** (the original reference version) changes only in the expected place.
- The active container contains the new `.mo` or the regenerated uno-json.
- The **rendered inventory** (a snapshot of the strings actually rendered) confirms the change in the correct place.
- The **collision map** (a map of msgid collisions by context) is updated if PO-context separates the meaning.

Completion criterion: the agent can explain why the edit will not affect another meaning of the same English string.

Refusal template when the UNO/core plan is incomplete:

```text
План для UNO/core неполный. Не меняй файлы.
Дай source chain (пункты 1–7 выше) и объясни,
почему правка не затронет другой смысл той же английской строки.
```

## How to supervise the agent

Trust must go not to the agent but to the artifacts (result files: manifest, tables, counts, gap lists). A result is accepted only if the counts (numbers) reconcile and all expected rows are present.

### Task contract

You give the agent the task as a contract with mandatory artifacts and a strict scope. First a read-only analysis, then edits in small batches. The scope is fixed before work begins and does not change without a separate list of changes.

Every edit must:

- reference a concrete decision source — an approved candidate or decision id (the approved translation variant / decision record);
- operate only within safe candidates (verified variants) and the permitted source_class (the class of the string's source, e.g. `ui-json` — client UI strings from json; `uno-json` — strings of UNO commands, editor actions; `lo-core-mo` — LibreOffice core strings from mo);
- not touch risky risk_class values: mixed-context, composed-fragment, core-only, unresolved (mixed context, assembled from fragments, core-only, unresolved);
- have rendered proof (before/after — a snapshot of the real screen before/after) for each changed UI scenario, on the actual languages and applications: ru/uk/ar/zh-CN, Writer/Calc/Impress.

Mandatory artifacts (files):

1. machine-readable manifest (`run_manifest.json`);
2. a full CSV/JSON table;
3. Markdown summary;
4. counts/invariants (an invariant — a control equality by which the counts reconcile);
5. a list of gaps/skips/unresolved;
6. reproduction commands (how to repeat the extraction — the pulling of strings).

Canonical task template:

```text
Роль:
Ты не переводчик, а аудитор локализации. Твоя цель - доказуемо собрать полный artifact.

Scope:
Перечисли включённые языки, приложения, файлы, UI-состояния. Не расширяй и не сужай scope без отдельного списка changes.

Forbidden:
Не делай summary-only и sample. Не пропускай failed/skipped. Не вноси правки без ссылки на approved candidate.
Внеси переводы только для source_class=ui-json. Не трогай risk_class mixed-context, composed-fragment, core-only, unresolved.

Required artifacts:
1. machine-readable manifest;
2. full CSV/JSON table;
3. Markdown summary;
4. counts/invariants;
5. list of gaps/skips/unresolved;
6. reproduction commands.

Acceptance:
Работа принимается ТОЛЬКО если counts сходятся и все expected rows присутствуют.
Проверь: пересобери образ, открой Writer/Calc/Impress на ru/uk/ar/zh-CN, приложи rendered evidence.
Если любой шаг не получается или не успеваешь всё покрыть, остановись и выдай missing_work.csv, не угадывай.
```

### How to catch partial completion

Signs of an incomplete pass: a sample slipped in instead of the full set ("the main languages", "the key screens", "for example", "top N" instead of the complete list); no rows for failed/skipped; no raw JSON/CSV; no hash of the input files; no way to repeat the extraction; no link from the summary to the raw rows; no references from the patch to an approved decision/candidate; no before/after evidence.

Do not ask "check more carefully" — you will get another summary. Give a delta-task for the specific missing artifact with an explicit completion criterion.

### How to force rework to a complete result

The rework mechanics via sets:

1. Build the expected set (everything expected: languages, applications, scenarios, `msgid`).
2. Build the actual set (what has actually been checked and is present in the table/screenshots).
3. Build the gap set = `expected - actual`.
4. Run ONLY the gap set — this prevents doing another selective general pass.
5. Recompute the invariant.

Completion criterion: `missing_after = 0`, or every remaining row has status `blocked` with a reason.

Example command:

```text
Не делай повторный общий аудит.

1. Прочитай expected_scenarios.csv.
2. Прочитай run_manifest.json.
3. Построй missing_scenarios.csv как expected - actual.
4. Прогони только missing_scenarios.csv.
5. Обнови run_manifest.json.
6. Выведи counts: expected, before_actual, missing_before, added, missing_after.

Критерий завершения: missing_after = 0 или каждая оставшаяся строка имеет статус blocked с причиной.
```

### Acceptance checklist

The output is accepted only if all items are satisfied; if even one is missing, the result is preliminary:

- there are full expected set, actual set, and gap set;
- there are machine-readable rows and a reproducible command;
- the counts reconcile;
- skipped/failed are not hidden;
- the raw rows can be spot-checked;
- the patch references approved ids;
- the rendered proof covers the changed states.

## How to verify completeness

A single screenshot or a single reconciliation is not enough: completeness is proven by several independent reconciliations where the numbers agree (invariants). Otherwise it is a retelling, not an audit.

Minimal set of independent reconciliations:

1. Static extraction (how many strings are found in the code).
2. Catalog coverage (how many strings exist in the catalogs for each language).
3. Occurrence map (where each string is used).
4. Rendered inventory (what is actually visible in the browser).
5. Collision map (where one English text has different meanings).
6. Rendered regression + visual proof (what changed after the patch, before/after screenshots).
7. False positives (English strings that should remain).

Mandatory: all 22 languages go through the same set of scenarios, not a sample of languages and tabs. Additionally, we look for strings that are visible in the render but absent from static extraction, and vice versa; collisions of one translation across different meanings; compound phrases assembled from separate words; broken RTL languages; labels overflowing out of buttons; technical keys instead of the English fallback; missing icons, tooltips, and menus.

Completeness and quality are different things. Agreeing numbers prove that the translation exists, is visible, and the result is reproducible, but they do not prove its correctness. Correctness is verified by a separate pass of a strong model directly against the render, and a final polish by a native domain expert (who knows the domain terminology).

### Checks by type of work

Terms: static extraction — extracting strings from code; occurrence map — where a string is used; collision map — a map of identical texts with different meanings; catalog coverage — coverage of catalogs by translations; context split — separating one text across contexts; source_class — the source layer of a string (ui/uno/locore/.mo); risk_class — an assessment of translation risk; source chain — the chain "string → its source down to the edit". Artifacts (`*.json`, `*.csv`, coverage matrix, manifest) — report files that the agent generates; each is required as evidence.

| Work | What the agent usually leaves unfinished | How to verify independently | How to close the gap |
| --- | --- | --- | --- |
| Baseline | Takes a subset of languages or the wrong container | Compare the locale set against the code, recompute the hash of the extracted files | Require `baseline_manifest.json` and `missing_catalogs.csv` |
| Static extraction | Gives a summary instead of a full occurrence map | Recount `_()`, `_UNO(...)`, i18n keys with a different script | Require `occurrences.json`, `extraction_stats.json`, `unresolved.csv` |
| Catalog coverage | Checks only `ui-*.json` | Compare `ui`, `uno`, `locore`, `.mo` separately | Require a coverage matrix for each source class |
| Rendered inventory | Checks one language or one tab | Compare `scenario_manifest` and `run_manifest` | Require `missing_scenarios.csv` and a delta-run |
| Collision map | Classifies only the obvious problems | Compare set(msgid) of the occurrence map and the collision map | Require full coverage of all `msgid` |
| Translation candidates | Translates everything indiscriminately | Check risk_class and source_class for each candidate row | Remove hard cases from the batch and require statuses per locale |
| Direct ui-json patch | Changes more keys than approved | Compare the diff keys against the approved candidates | Narrow the patch down to the approved set |
| Context split | Splits part of the occurrences, leaves the conflicting spots | Compare old occurrence ids with new occurrence ids | Require `missing_or_unsplit_occurrences.csv` |
| UNO/core patch | Proposes the wrong layer for the fix | Check the source chain down to `.po/.mo/uno json` and the rendered UI | Require a source-chain report down to the edit |
| Verification | Shows only the successful screenshots | Check failed/skipped and the before/after text dump | Require a full verification manifest |
| Upgrade maintenance | Ports old patches blindly | Compare old/new occurrence map and changed contexts | Require a release diff matrix |

Here ui/uno/locore/.mo are the four source layers of strings: ui-json (the client interface), uno-json (UNO commands — the internal commands of the LibreOffice engine), lo-core (the LO core) and its compiled `.mo` (binary catalogs from `.po`).

### Example of independent invariants

The agent must show HOW a number was recomputed by a different method, otherwise the report is not accepted. Suppose the static report claims:

```text
locales = 22
direct_ui_msgid = 436
referenced_uno_labels = 300
global_uno_labels = 813
```

Then independent checks of these numbers must exist:

```text
count(locales_from_project) == 22
count(unique direct _() msgid in selected code segments) == 436
count(unique resolved UNO labels from referenced commands) == 300
count(unique labels in global UNO map) == 813
```

### How to accept partially blocked work

Sometimes a full pass is impossible: Playwright is busy, a fixture won't open, the source is minified, a `.po` is missing, a command is created dynamically. A blocked state is legitimate, but it must be explicit. For each blocked item the following fields are required:

| Field | What to write |
| --- | --- |
| `blocked_id` | A stable id |
| `scope_item` | Exactly what is not covered |
| `reason` | Why it is not covered |
| `attempted` | What has already been tried |
| `needed` | What is needed to close it |
| `risk` | What may be incorrect because of the block |
| `owner` | Agent, human, external tool |
| `next_check` | How to return to the check |

The phrase "could not verify" without these fields does not count as a report.

## How to maintain the final artifacts

Besides the edits, you need documents that record coverage and decisions.

Recommended files (baseline — the starting snapshot of the state; occurrence — each occurrence of an interface string; render-path/"layer" — where a string is fixed: the client JSON or the core `.mo`):

| File | Purpose |
| --- | --- |
| `localization_baseline.md` | Image version, list of languages, covered applications |
| `localization_occurrences.json` | Occurrence map: a machine-readable map of all occurrences with their contexts |
| `localization_coverage.md` | Summary of translated/missing/same by language |
| `localization_collisions.md` | All context risks |
| `translation_candidates.md` | Translation candidates and their statuses |
| `translation_decisions.md` | Human decisions on hard cases |
| `translation_verification.md` | Final checks and screenshots |
| `translation_glossary.md` | Terms that must be translated consistently |

The starting baseline artifact (the first inventory snapshot) already exists in the project:

```text
docs/COLLABORA_LOCALIZATION_STATIC_INVENTORY.md
```

This is not the end. The next step is an occurrence map with contexts and a rendered inventory (a list of interface strings that are actually rendered).

The pass produces two artifacts:

- `.qa/l10n/REPORT.md` — a coverage report: how many visible strings there are, how many are translated for each language, and a breakdown of the gaps into "fixed in the client JSON" and "only via the core `.mo`".
- `.qa/l10n/visible-coverage.csv` — a machine matrix: one row per interface string, with a status for each language.

Together they provide a verifiable basis for deciding what to fix and in which layer.

## Strategy for working with Collabora sources

Main principle: **from sources we build only Collabora Online** — the coolwsd server (the editor's backend daemon) and the browser bundle (the compiled client JS/CSS). **We do NOT build the LibreOffice/Collabora Office core from sources** — we take it as a pinned prebuilt binary (engine-assets — the LO engine's prebuilt files). Core strings are edited as data, not by rebuilding.

Reason: in deep localization, everything we change in the UI (texts, sizes, design) lives in the Online layer, not in the core; that is also where string concatenation in JS and the contextual translation API live.

The quick path we are moving away from:

```text
FROM collabora/code:latest
```

from there the Dockerfile edits the already-built `bundle.js`, `bundle.css`, `cool.html`, `l10n/ui-*.json` via `sed`/`cp`. Acceptable as a temporary crutch (a branding trifle, a hotfix), but not as the foundation of localization, because:

- `latest` is nondeterministic — today and tomorrow it is different bytes;
- minified `bundle.js` gives no contextual separation of strings (identical text with different meanings cannot be split apart);
- a `sed` patch against a built file breaks with any upstream change;
- you cannot properly add a contextual localization API;
- after an update you cannot trace which source file produced a string.

We pin the version hard and **as a pair**: the Collabora Online commit/tag AND the core engine-assets version — both in `upstream.json`, and they must match. Reason: strings (`msgid` — the source text, `msgctxt` — the context discriminator in gettext) are version-dependent. Therefore a version update is a separate controlled event with full translation acceptance, not "pulled latest." When building from sources, you backport upstream security fixes yourself — another reason to keep updates under control.

The steps below are a ladder for moving away from the prebuilt image; there is a single end point — building Online from pinned sources. If possible, you can jump straight to the target level.

### Step 1 (temporary): remove the nondeterminism of the prebuilt image

Until building from sources is in place:

1. Do not use `collabora/code:latest`.
2. Pin the image by digest or tag.
3. Record the pinned image in the baseline (a fixed reference).
4. Hash the active artifacts: `bundle.js`, `ui-*`, `uno/*`, `locore/*`, `.mo`.
5. Build any report only against this baseline.

```text
collabora/code@sha256:<digest>
```

(template command for the release-engineer agent to check pinning).

### Step 2 (intermediate): patches as units, not long `sed` chains

While the image is still prebuilt, we keep changes not as `sed` chains but as described **patch units** — atomic patches with metadata.

```text
editor/
  Dockerfile
  patches/
    collabora-online/
      0001-contextualize-line-label.patch
    libreoffice-core/
      0001-ru-pivot-field-translation.patch
  scripts/
    extract-active-collabora-assets.sh
    build-l10n-occurrence-map.py
  manifests/
    upstream.json
    patchset.json
```

The requirements for a patch as a unit coincide with the layer proof (see "Which layer to fix"): what it changes, why this is the right layer, which upstream digest it relates to, which `occurrence ids` (identifiers of specific string occurrences) it closes, which rendered scenario confirms the result, how to roll it back.

### Target level: building from pinned sources

The project's working foundation. From sources we build **Collabora Online**, keeping not a copy but a fork or submodule of a pinned commit. **We do NOT build the LO core** — a pinned prebuilt binary (engine-assets); its `.mo` files (compiled gettext catalogs) are edited as data from our `.po` files (text translation catalogs).

What each layer allows changing **without building the core**:

- **Texts** — data (the client `ui/uno/locore-<lang>.json` + the core `.mo` from our `.po`) plus a bit of code in Online to un-concatenate glued phrases;
- **Sizes** — CSS (partly JS);
- **Design** (colors, shapes, spacing, icons) — CSS + SVG replacement; this is how the glass theme was already done.

```text
third_party/
  collabora-online/       # submodule/fork, pinned commit (BUILT from sources)
editor/
  engine/                 # LO core engine-assets (prebuilt binary, NOT sources)
  l10n/overrides/
    core/<lang>.po        # core string translations, with msgctxt → compiled into .mo
    client/<lang>.json    # client string overlays
  patches/                # ONLY Online code (contextual API, un-gluing concatenations)
  build/                  # deterministic Online build + data overlay
  manifests/
    upstream.json
    patchset.json
```

The key separation — **translations are DATA, patches are only CODE**. Translations (`.po` with `msgctxt` + JSON overlays) are deterministically compiled into `.mo` and catalogs, are easy to review, and scale to 30–40 languages. Patches are only code (a new contextual API, rewriting glued phrases into whole ones with placeholders). They are not mixed in one change.

A fork/submodule is better than a copy because: upstream history is preserved (rebase/merge); the differences from upstream are visible; it is easier to check applicability to a new version; there is less risk of editing the generated output instead of the source.

Where to send things upstream — don't confuse the channels: **translations go to Weblate** (the LibreOffice/Collabora translation platform); **code changes** (contextual API, concatenation fixes) go as an ordinary PR to Collabora Online or LibreOffice.

### Which layer to fix (core or client)

Part of the interface comes not from Online but from LibreOffice-core (`.ui` files, gettext `.po/.mo`, UNO command metadata — the LO engine's internal commands, dialogs, sidebar). The layer of a string — "Online client vs LO-core" — is chosen **by proof, not by eye** (this is render-path attribution — determining by which path a string reaches the screen). Before each edit, prove:

- the string really comes from LO-core, not from the client `ui-json`/`uno-json` (the catalogs of client ribbon/menu strings and UNO commands);
- there is a specific PO/UI/source file;
- there is a build path down to `.mo` or a generated resource;
- there is a rendered scenario confirming the result on screen.

Client strings are edited in our JSON overlays, core strings in our `.po` with `msgctxt`.

### When to build the LO core from sources after all

Almost never. Only if you need to change **the rendering of the document itself** (how the core draws the Calc grid, a slide, text in cells) or **the core's C++ behavior**. This is document content, not UI elements — it is not needed for texts, sizes, and design.

This is the heaviest path: hours even on a fast machine, an image up to ~30 GB. Even the official "CODE for Web" build does NOT rebuild the core — it drops in prebuilt engine-assets. A full core build is an optional escalation, not our default.

### What not to do

- copy the entire Collabora source without an upstream link;
- live on `latest`;
- edit minified `bundle.js` as the primary way of making changes;
- bulk-import PO/JSON without an occurrence/collision map (maps of string occurrences and conflicts);
- mix app translations, browser-UI, and LO-core in one patch batch;
- keep translations as code patches instead of data files (`.po`/JSON overlays);
- roll a version update to production without full translation acceptance.

### Completeness control for the source strategy

The source strategy = building the editor from pinned sources rather than editing a prebuilt image. It requires separate artifacts:

| Artifact | What it proves |
| --- | --- |
| `upstream.json` | Which Collabora and LibreOffice version is used |
| `patchset.json` | Which patches are applied, what they relate to, which occurrence (string occurrence sites) they close |
| `source-build.md` | How to build the editor image from source or a series of patches |
| `source-diff-report.md` | How the fork differs from upstream |
| `generated-vs-source-map.json` | How the generated output (built/compiled files, not edited by hand) relates to the source files |
| `release-diff-matrix.csv` | What changed on an upstream update |

Invariants:

- the editor image must not be `latest`;
- Online is built from pinned sources; the LO core is a pinned prebuilt binary/engine-assets; the Online version and the LO-core version are pinned in `upstream.json` and **match** (are aligned with each other);
- translations are stored as data (PO/MO — binary translation catalogs, JSON overlays), not as code patches; code patches are allowed only for code;
- every code patch has an upstream base commit, owner, and reason; a patch without a link to a commit or image digest is not accepted;
- every translation entry and every code patch references occurrence ids; every source-level split updates the occurrence map (string traceability);
- generated output is not edited if a source-level path is available;
- every version update passes full acceptance before promotion to production and recomputes the release diff matrix.

Command to the agent:

```text
You are the architect of the source-level strategy for Collabora localization.

Task: propose how to move from patches over a prebuilt image to a reproducible source-level scheme.

Result:
1. The current way of building the editor.
2. The risks of the current way.
3. A minimal pinning plan (version pinning).
4. A patch-series plan for the current repo.
5. A fork/submodule plan for Collabora Online.
6. A separate decision on whether LibreOffice-core source is needed.
7. A list of new artifacts.
8. A step-by-step migration plan.

Completeness control:
- The current image/tag/digest is specified.
- It is explicitly separated which edits remain image-level and which become source-level.
- There is a rollback plan.
- There is an upstream update strategy.
- There is a way to verify that patches apply to the correct version.
```

## How to maintain after Collabora updates

When updating Collabora, you must not blindly port the old patch: a version update is a controlled event with full acceptance testing, not the transfer of a single patch.

Collabora is not stock LibreOffice: it has its own strings and its own notebookbar. Therefore any import of someone else's translation or language pack is checked against the version and the contexts.

The order is as follows:

1. Bring up the new pinned version **first in a non-prod environment**, without touching prod: a new Collabora Online commit + a **matching** version of the prebuilt core/engine-assets (prebuilt engine binaries).
2. **Rebuild Online from source** for the new version; the core is taken as a prebuilt binary/engine-assets and is not rebuilt.
3. Run the **full acceptance test, not smoke**:
   - rebuild the occurrence map (the map of string occurrences) and coverage;
   - run render-ground-truth (truth by the fact of rendering — a screenshot of each object) across **all** target languages;
   - do a drift-diff (a comparison of string discrepancies) of the entire interface against the previous version.
4. Analyze what the update broke: moved or renamed `msgid`, changed `msgctxt`, new English strings, removed strings, re-appeared merges of several strings into one.
5. Re-apply (rebase) our translation data and code patches onto the new version and fix the breakages.
6. **Only after passing the full acceptance test** — promotion to prod.

This acceptance test is a mandatory CI gate before promotion: the same checks (coverage, render-ground-truth, drift-diff) are run on every version bump. The acceptance criterion is a screenshot of each object plus a second verification pass (a repeated control pass, see "Principle of evidence").

Command to the agent:

```text
You are a localization release auditor after a Collabora update.

Task: compare the old and new baseline and state which localization patches are safe to port.

Context:
- Old patches may have been tied to old source strings.
- New PO/JSON (translation files) may have different contexts.
- You cannot port en masse without verification.

Result:
1. Table of unchanged keys.
2. Table of removed keys.
3. Table of new keys.
4. Table of changed occurrences.
5. List of patches and translation entries that can be kept.
6. List of patches and translation entries that need to be reviewed.
7. Full acceptance plan (not smoke): render-ground-truth across all languages + drift-diff against the previous version.

Completeness control:
- Every old patch key must be classified (unchanged/removed/new/changed).
- Every new English leftover (a remaining untranslated string) must be linked to a source class (the source string class).
- If the context has changed, the patch/translation must be marked needs review.
```

## Scaling to many languages

When there are not 4 languages but 30-40, the work is not repeated for each one. It is split into two levels:

- The surface is captured once. The occurrence map (a list of all the places where each string appears) is language-independent - it is built a single time.
- Per-language coverage is computed from data: strings are checked against the language's catalogs and its `.mo` (compiled translation catalog). This is a pure file-based computation, without a browser, and it scales to any number of languages.

Data cannot verify how the translation actually looks on screen: line wrapping, overflowing a button, RTL layout, contextual collisions (the same key in different places requires a different translation). This is only visible in the render, and it must be checked for each language. The browser is the bottleneck (one per instance). The solution is to parallelize: several VMs, one language per machine, each with its own editor and browser instance; the screen passes run in parallel.

## Practical rollout order

Three phases: inventory and mapping, batch processing of safe strings, manual work on hard cases.

1. Finish the occurrence map (a map of all occurrences of translatable text) via `scripts/build-l10n-catalog.py` — automated, see "Inventory tooling".
2. Produce the rendered inventory (what is actually rendered on screen) via Playwright, `e2e/scripts/editor-l10n-rendered.mjs` — automated.
3. Build the collision map (a map of conflicting terms) via `scripts/build-l10n-ru-terms.py` — automated.
4. Isolate safe candidates — strings with a single, non-conflicting translation (per the occurrence and collision maps); the rest go into hard cases.
5. Agree on a glossary for frequent terms.
6. Add a small batch of safe strings to `ui-json` (the client-side interface JSON catalog).
7. Rebuild the image.
8. Check the active catalogs — that exactly the intended catalog versions made it into the build.
9. Run the Playwright smoke (a quick check) across all languages.
10. Run the full Playwright pass on the key languages: ru, uk, ar, zh-CN, plus a few European ones and RTL.
11. Fix width, RTL, and compound-phrase issues.
12. For hard cases, a human makes the decision.
13. Apply context split (splitting an identical string across contexts) or PO/MO/UNO (the LibreOffice text catalogs and UNO strings) changes in small batches.
14. After each batch, update the maps (occurrence, collision) and the verification report.

## Minimal definition of done

A localization batch is complete if:

- all changed strings are in the occurrence map (the registry of affected occurrences) — the accounting is complete;
- every changed string has a risk classification (risk class); strings in forbidden classes are not touched without a separate decision;
- the translation is entered into the correct source class (the string's source container) and is actually present in the active container at runtime — that is, it was picked up, not just written;
- the rendered inventory (the inventory of the actual render — this is the ground truth) after the edit shows no new English remnants in the affected places;
- the regression test (`scripts/l10n-regression.sh`) is green — with no failures: no text-changes outside the intended block and no new layout defects (overlaps / clipping / overflow beyond the viewport); confirmed with screenshots;
- RTL and UI width are checked for the affected languages;
- there is a report of false positives (false triggers);
- there is a rollback plan (reverting the changes);
- the update-log describes what was changed and why.

## Agent and human roles

The AI agent prepares and checks the translation, but does not translate autonomously: it does not "catch up on translations" without context. Terms are approved and the result is accepted by a human.

The agent's role:

- gather the facts and show every place where strings are used;
- separate the safe from the dangerous;
- propose options;
- apply only the approved, pinpoint edits;
- prove the result by render (an actual screen, not the presence of a string in the catalog).

The human's role:

- approve terminology;
- decide mixed-context cases (one string in different meanings);
- choose how to split keys (splitting one key into separate keys by context);
- accept the risk of leaving an English term;
- give final acceptance of the visual result;
- check translation quality as a native-speaker subject-matter expert — the presence of a string does not equal its quality.
