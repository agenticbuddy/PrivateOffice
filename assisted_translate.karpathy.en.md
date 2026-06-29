# Assisted localization of Collabora Online

ok so this is a walkthrough of how to fully localize a Collabora Online–based project, with an AI agent doing most of the legwork. I'm deliberately not tying it to a specific tool. When I say "agent" below I mean any assistant that can read the project, run commands, poke at the code, write up reports, propose edits, and then verify its own work: Codex CLI, Claude Code, an OpenRouter agent, a local LLM agent, whatever. The reasoning is the same regardless of which one you point at the problem.

The one mental model I want you to walk away with is this: localizing Collabora Online is *not* "fill in the missing keys in a JSON file." That's the trap. The real task is to first understand where each English string actually shows up, by which mechanism it gets translated, whether it carries different meanings in different places — and *only then* make targeted edits. Translation second, attribution first.

I'm writing this as a working manual, not a cheat sheet, on purpose. If you're seeing Collabora Online for the first time, knowing the list of files isn't enough — you also need the intuition for *why* an innocent-looking action like "add a translation to JSON" can give you a false positive: one screen gets fixed, another quietly breaks, and your grep cheerfully reports "the translation is there." That gap between "the string exists in a catalog" and "the string is what's drawn on screen" is the whole ballgame, and we'll keep coming back to it.

There's a second theme running through this: how to actually *control* the agent. Here's the thing to realize about agents — they will confidently tell you they "checked all languages" or "built the full table," when in practice they sampled: a few languages, a couple of tabs, the first grep hits, part of the catalogs. This is normal LLM behavior, not malice. So the rule we'll enforce is that the agent's output counts only when it leaves behind *verifiable artifacts*: a machine-readable table, a scenario manifest, a list of input files with hashes, screenshots, DOM/text dumps, reproduction commands, and numbers you can recompute yourself. Trust the artifacts, not the prose.

## Short conclusion

Let me give you the punchline up front, because it's the single most expensive lesson here: if a string is not translated in `ui-*.json`, that does *not* mean you can just add a translation and call it done.

Why not? Concretely:

- One English `msgid` can appear in several different places in the interface.
- The same English text may need *different* translations in those different places.
- Some strings aren't standalone phrases at all — they're fragments glued into a composed phrase.
- Some labels don't come from `ui-*.json`; they come from UNO or LibreOffice-core.
- Some English values are better left in English: format names, technical terms, function names, brands.
- A translation can be linguistically perfect and still break button width, RTL layout, a tooltip, a menu, or a dialog.
- A translation can already be sitting in the catalog and *still* not show up on screen, because the string is actually rendered by a different layer.
- And you can't blindly drop in a ready-made third-party translation (a fresh LibreOffice language pack): Collabora differs from stock LibreOffice, and some strings simply won't match.

Now the good news, and it's genuinely good: **almost all of the localization — all the UI element texts, sizes, and design — is reachable without building the LibreOffice core.** It all lives in the Collabora Online layer (data + CSS + a little code). You only need to build the core to render the document itself. So the scary-sounding part is mostly off the table.

Given all that, the correct path is:

1. Collect all English strings.
2. Collect all the places where each string appears.
3. Split strings by source: `ui-json`, `uno-json`, `lo-core-mo`, frontend i18n, generated/composed text, unresolved.
4. Build a map of contexts and possible collisions.
5. Translate the safe cases first.
6. For risky cases, do context splitting or edit the correct PO/MO/UNO source.
7. Verify every edit by *rendering*, not just by grepping over files.

## What exactly is hard

ok so to build up the mental model, start from what a *normal* app looks like. Usually there's a single localization layer: the code calls `t("Save")`, the catalog stores the translation, the UI shows the translation. One pipe, one source of truth. Easy.

Collabora Online has more layers stacked on top of each other:

| Layer | What lives in it | How it is usually fixed |
| --- | --- | --- |
| App frontend | The project's wrapper around Collabora: login, files, profile, modals | `frontend/src/i18n/messages/*.json` |
| Collabora browser UI | Ribbon/notebookbar, part of the menus, tooltips, panels, buttons in web code | `l10n/ui-<locale>.json`, in this project via a patch in `editor/Dockerfile` |
| UNO command labels | Labels of LibreOffice commands that Collabora invokes via `_UNO(...)` | `l10n/uno/<locale>.json` or the source that generates these catalogs |
| LibreOffice-core | Dialogs, server/core UI, `.ui`, gettext, some sidebar and dialog strings | `.po` -> `.mo`, then rebuild or replace resources in the image |
| Composed strings | Phrases assembled from several translatable or non-translatable pieces | Rewrite into a whole phrase with placeholders |
| System elements | Browser menus, OS-native elements, some file picker/clipboard prompts | Usually outside the app's control |

Here's the key consequence, and it's where people shoot themselves in the foot: if a string belongs to `ui-json`, editing `.mo` does nothing. If a string belongs to `lo-core-mo`, adding a key to `ui-ru.json` does nothing. You have to determine the source *first*, or you're just rearranging files that nobody reads.

And — this is the subtle part — you can't infer the source from the mere fact that the string is sitting in some catalog. My favorite example: the string `Clipboard` is present in `ui-ru.json` *with* a Russian translation, and yet in the ribbon it still shows up in English. Why? Because that label is drawn by the core, and the client catalog isn't used there at all. So "the string is in the catalog" and "the string is actually taken from this catalog" are two completely different claims. The real source is confirmed only by experiment: change the string in the candidate catalog, rebuild, bust the cache, and look — did the screen change or not?

One more wrinkle to hold in your head: the same English string can live in *several* layers at once — both in the client catalog and in the core `.mo`. So "the source of a string" isn't necessarily one value off the list; it's the *set* of layers it occurs in. Which layer actually paints the pixels is decided by the render path (more on this below), not by which catalogs happen to contain the string.

And when this got measured on a real project, the empirical result was: most of the gaps were in the client JSON, not in the core — and some strings that were formally present in the catalog were *still* rendered in English. So the "what fixes what" mapping is not something to take on faith. You check it on screen.

## Why adding a translation directly is dangerous

Let me make the danger concrete with one example, because abstractly it sounds harmless. Imagine the key `Illustrations`.

If it's only ever used as a ribbon group name, then translating it to `Иллюстрации` is fine.

But suppose somewhere there's a composed message like:

```text
No + Illustrations
```

A naive dictionary translation gives you:

```text
Нет Иллюстрации
```

while the actually-correct Russian is:

```text
Нет иллюстраций
```

In English this string-slicing usually looks fine, because English happily tolerates short dictionary pieces glued together. The grammar barely changes. But for Russian, Ukrainian, Arabic, Hebrew, Farsi, Japanese, Korean, Thai, and many others, slicing a phrase into independently-translated words is often just wrong — the pieces have to agree with each other.

Here are more words that look innocent and aren't:

| English string | Why it is risky |
| --- | --- |
| `Line` | A line as a shape, a line of text, a border, a chart line, a menu command |
| `Table` | A table as an object, an insert command, a style, a tab, a group |
| `Set` | The verb "to set", the noun "a set", the technical "set" |
| `Field` | A form field, a data field, a pivot table field |
| `Function` | A Calc function, the insert-function command, the function library section |
| `Range` | A cell range, an area, a named range |
| `General` | The General number format, the general settings section, the normal mode |
| `Delete` | Delete an object, delete a row, delete a sheet, delete a comment |

So the takeaway is: a translation has to be bound not just to the English text, but to the *place* where that text is used. The string alone is not enough information.

## Basic terms

Let me pin down the vocabulary, because we'll lean on it constantly:

| Term | Meaning |
| --- | --- |
| `msgid` | The English source string, or the key by which a translation is looked up |
| occurrence | A specific place where the string is used in code or in the render |
| context | The string's surroundings: app, tab, group, command, tooltip, neighboring words |
| collision | A situation where one `msgid` is used with different meanings |
| composed fragment | The string is part of a phrase, not a standalone phrase |
| source class | The localization layer (or layers) a string lives in: `ui-json`, `uno-json`, `lo-core-mo`, frontend i18n, and so on. May be several at once; which one actually draws the text is decided by the render path |
| baseline | The state fixed before an edit: image version, catalogs, screenshots, string lists |
| target locale | A language that has to be checked or completed |
| rendered proof | Proof via the browser: a screenshot, a DOM/text inventory, the UI state |
| render path | What actually draws the string on screen: client `_()`, a server-side JSDialog from the core, or UNO. Determined by experiment, not by presence in a catalog |
| plural form | A word form that depends on a number (1 file / 2 files / 5 files). Russian has 3 forms, Arabic has 6 |

## General workflow

The work splits cleanly into stages, and the order matters. The cardinal sin here is to open with a mass translation edit — don't. We build up the picture first, then we touch anything.

## Principle of provability

ok this is the philosophical core, so let me slow down. The most reliable evidence in this whole domain is *what is actually drawn on screen*. A screenshot is the only ground truth. A JSON catalog, a grep, the contents of a `.mo`, even the literal presence of a `_("...")` call in the code — those are all just *hypotheses*. They tell you a translation *could* apply; they do not prove it applied *in this exact place*. That's a categorical difference, and most false confidence comes from collapsing it.

So the source and translation of each string get confirmed by a separate pass **over every object** of the interface — not over a sample. You open the element and you look at it with your eyes. Ideally you snap a screenshot for every block: tab, group, button, menu, context menu, dialog, tooltip. And then — this is the nice trick — a *second*, separate pass (preferably by a different, stronger model) reviews those screenshots and hunts for mistakes. First pass collects, second pass verifies. Collector and critic are not the same role.

Every stage ends not with the word "done," but with a set of artifacts that another person — or another agent — can use to recompute the result from scratch.

Here's a bad result:

```text
I checked all the strings and found 20 problems.
```

And here's *why* it's bad — go through it and you'll feel the holes:

- it's unclear which files were checked;
- it's unclear which languages were in scope;
- it's unclear where the rest of the strings are;
- you can't tell a full pass from a sample;
- you can't reproduce the result after an image update.

Here's a good result — notice it's basically a receipt:

```text
Input files:
- bundle.js sha256=...
- ui-ru.json sha256=...
- uno/ru.json sha256=...

Scope:
- apps: Writer, Calc, Impress, shared builder
- locales: 22, list attached
- excluded: browser-native dialogs, OS file picker

Artifacts:
- localization_occurrences.json: 1842 occurrences
- localization_coverage.csv: 22 locales x 436 direct keys
- localization_unresolved.csv: 54 commands
- screenshots/: 22 locales x 3 apps x 12 states

Check numbers:
- direct _() matches in extracted segments: 436 unique msgid
- _UNO commands: 264 unique command id
- global UNO labels: 813 unique msgid
```

And the reason a good result is good is that you can *re-verify* it independently:

- open the input file by hash and confirm the right version was analyzed;
- recompute the number of strings with another script;
- check that the count in the report matches the count of rows in JSON/CSV;
- pick any `msgid` and find all its occurrences;
- pick any screenshot and match it to a DOM/text dump;
- see which places are not covered.

### What cannot count as proof

Conversely, here's the list of things people *try* to pass off as proof, and which you should reject on sight:

- a general text answer without raw tables;
- screenshots for one language only, if "all languages" was claimed;
- grep output without the list of files and extraction rules;
- a "found everything" report with no total count of found entities;
- a "top missing strings" table when a full table is needed;
- manual conclusions without a machine-readable artifact;
- a translation for which not all occurrences are listed;
- a patch for which it is not stated why this particular source class was chosen;
- a Playwright check without a scenario manifest;
- the absence of errors as proof of completeness;
- the presence of a string/translation in a catalog (`ui/uno/locore-*.json` or `.mo`) as proof that the translation is actually visible on screen (remember, the opposite was *proven*: `Clipboard` is in `ui-ru.json` but renders in English);
- a render check without cache-bust/hard-reload (the cache trap: assets get cached under an unchanged hash, and an old screen gets mistaken for the result of a fix — in *either* direction);
- a single cache bust as a guarantee of freshness: some assets (the branding script, runtime `ui-<loc>.json` catalogs) bypass the ordinary cache-bust, so verify the render in a clean browser profile and additionally cross-check with a request that bypasses the cache.

### Minimal set of verifiable artifacts

Concretely, here's the minimum each stage owes you, plus how you'd check it. Think of the right column as your independent re-derivation:

| Stage | What the agent must leave | How to verify it |
| --- | --- | --- |
| Baseline | `baseline_manifest.json` with languages, apps, files, hashes, container versions | Recompute hashes, compare languages with the project code, check that files exist |
| Static extraction | `occurrences.json`, `coverage.csv`, `unresolved.csv`, the extractor run command | Re-run the extractor, recompute regex/AST matches, check random strings by hand |
| Rendered inventory | `scenario_manifest.json`, screenshots, DOM/text dumps, trace/log | Check that all locale/app/state pairs are present, open sample screenshots |
| Collision map | `collisions.csv` with all `msgid`, risk class, and occurrence ids | Check that each `msgid` from the occurrence map is classified exactly once |
| Translation candidates | `translation_candidates.csv` with source, context, confidence, reason | Check that no hard cases or unresolved got in |
| Patch | diff, list of approved candidate ids, list of changed keys | Check that the diff changes only allowed source classes |
| Verification | before/after inventory, screenshots, failures, false positives | Compare changes with the patch list and check there are no new collisions |

### Completeness invariants

Here's a technique I really like, borrowed from how you sanity-check any pipeline: for each stage, write down numbers that *must* add up. If they don't add up, something is missing, full stop — no amount of nice prose overrides arithmetic.

Example invariants:

- the number of languages in the report equals the number of languages in `backend/app/services/locales.py`;
- for each language there is a row in the coverage table;
- every `msgid` from the occurrence map has at least one occurrence;
- every occurrence references an existing file, offset, selector, or screen state;
- every rendered English leftover is linked to the occurrence map or marked `unresolved`;
- every `unresolved` has a reason and a next step;
- every safe candidate has risk class `single-use` or `same-context multi-use`;
- every changed translation has an approved candidate id;
- every patch key, after the build, is actually present in the active container;
- every changed UI state has a before/after screenshot or text dump;
- every hard case either has a human decision or is explicitly left unresolved.

And to say it plainly: if the invariants don't add up, the work isn't finished — even if the agent handed you a beautifully coherent report. Coherence is not completeness.

### Stage 1. Fix the baseline

Before you can localize anything, you have to nail down *what exactly* you're localizing. No moving target.

Minimal baseline:

- project version;
- Collabora Docker image version;
- list of supported languages;
- for each language — the chain of codes: the language code in the app -> the code the app passes to the editor in the `lang` parameter -> the catalog file that actually loads;
- list of apps: Writer, Calc, Impress, and Draw if needed;
- list of interface modes, if there are several designs;
- the active `bundle.js`, `l10n/ui-*.json`, `l10n/uno/*.json`, `l10n/locore/*.json`;
- LibreOffice resources: `.po`, `.mo`, `.ui`, if available;
- a set of test documents for Writer, Calc, Impress;
- a list of UI states: ribbon tabs, in-app system menus, context menu, sidebar, dialogs, tooltips, formulas, tables, charts, pivot tables, images, shapes.

I want to single out one of these because it's a classic silent killer: write down explicitly how a language code turns into a loaded catalog. The chain is: the user picks a language in the app (say `ru`) -> the app hands the editor a code in the `lang` parameter (in this project the mapping lives in `co_lang`, `ru` -> `ru-RU`) -> the editor normalizes the region and loads a concrete file (`ru-RU` -> `ui-ru.json`). If the code is wrong or carries an extra region, the editor may *silently* load no catalog, or the wrong one — and then the whole language looks untranslated even though the catalog is sitting right there on disk. A wrong code can also flip individual strings, like the language label in the status bar or a raw placeholder such as `{ru}`. This is a common and basically invisible cause of zero coverage, so check the chain for each language separately. Don't assume; trace it.

Command to the agent:

```text
You are a localization auditor. Work read-only.

Task: fix the localization baseline of the Collabora Online project.

Context:
- The project is already running locally.
- All supported languages of the project must be covered.
- Writer, Calc, Impress and shared UI elements must be covered.
- Change nothing.

Result:
1. List of found languages and where they are defined.
2. List of found localization sources.
3. List of apps and UI states that will need to be checked.
4. List of files/images/containers the baseline was taken from.
5. Risks and unknown areas.

Completeness control:
- All languages must match the project's list.
- It must be stated explicitly what is not covered.
- No edits to project files, except the report, if I separately allow creating it.
```

Now, control that doesn't rely on trusting the agent — because remember, we trust artifacts, not vibes:

- Ask for `baseline_manifest.json`, where each row is a concrete input: path, source, size, hash, extraction date, container or commit.
- Separately recompute the list of languages from the project code and compare with the manifest. If the project has 22 languages, the manifest must have 22 languages — not "the main ones."
- Check that for each language it states which catalogs actually exist: `ui`, `uno`, `locore`, `.mo`. A *missing* catalog is also a row in the table, not a silent skip.
- Check that the app scope is listed explicitly. "editor UI" doesn't cut it: it has to be Writer, Calc, Impress, shared, and Draw/out-of-scope if relevant.
- Check that container files are taken from the *active image*, not from local assumptions. The proof is the extraction command plus the hash of the extracted file.
- For each language, check the chain code -> `lang` -> loaded catalog: which catalog file the browser *actually* requested (visible in the network tab), not which one you expected. If no catalog is requested for a language, that's your hidden cause of zero coverage.

Signs the agent only did part of the job:

- The agent listed only `ru`, `uk`, `ar`, `zh-CN`, although the task is about all languages.
- The agent did not give hashes of input files.
- The agent did not distinguish `ui`, `uno`, `locore`, `.mo`.
- The agent wrote "LibreOffice resources present" but did not say for which languages.
- The agent did not say which UI scenarios will be checked later.

And here's the move I want you to internalize — don't say "check more carefully." Give it a tight *delta* task that's hard to fake:

```text
You did the baseline partially. Do not rewrite the whole report.

Do only the delta:
1. Build a machine-readable baseline_manifest.json.
2. Add to it all 22 languages from backend/app/services/locales.py.
3. For each language note the presence of ui-json, uno-json, locore-json, LO .mo and the hash/size if the file exists.
4. Separately output a table of missing catalog files.
5. Change nothing in the code.

Done criterion: the manifest has exactly 22 locale rows, and each row has the same set of columns.
```

### Stage 2. Static string inventory

At this stage the agent reads the code and catalogs — but it does *not* yet prove anything about the render. We're building the map of what *could* be used; whether it's actually drawn comes later. Keeping those two questions separate is half the discipline.

What you need to collect:

- all direct `_()` strings;
- all `_UNO(...)` commands;
- all frontend i18n strings;
- all strings from `ui-*.json`;
- all strings from `uno/*.json`;
- all strings from `locore/*.json`;
- all available LibreOffice PO/MO/UI resources;
- all places where a string appears in the code.

The key output is the occurrence map. Everything downstream references it, so it's worth getting right.

Minimal occurrence map fields:

| Field | Why it is needed |
| --- | --- |
| `msgid` | The English string |
| `source_class` | `ui-json`, `uno-json`, `lo-core-mo`, frontend i18n, unresolved. May be several values at once; which layer actually draws the string is indicated by `render_path` |
| `app` | Writer, Calc, Impress, shared |
| `file` | File or bundled segment |
| `line_or_offset` | Where it was found |
| `call_type` | `_()`, `_UNO(...)`, frontend `t()`, generated |
| `control_type` | tab, group, button, tooltip, menu, dialog, message |
| `neighbor_text` | Neighboring words or phrase |
| `command_id` | UNO command id or control id, if any |
| `is_fragment` | Whether it looks like a piece of a phrase (detected by call-site analysis: `_("x")+var`, templates) |
| `render_path` | What actually draws the string: `client-_()`, `server-jsdialog-core`, `uno`. Confirmed by experiment (edit the source -> rebuild/cache-bust -> did the render change), not by assumption |
| `notes` | What has to be checked manually |

I want to hammer on the `render_path` field, because this is exactly where intuition leads people astray. Do *not* fill it by guessing from which catalog the string lives in. You confirm it by experiment: change the string in the assumed source, rebuild the image, bust the browser cache, and watch the screen. Changed → source is correct. Didn't change (like `Clipboard`, which lives in `ui-ru.json` but is drawn by the core) → the source is something else, and editing that catalog is a no-op.

Another footgun: when you match a string off the screen against a string in the catalog, you can't compare them literally. Both have to be normalized to one canonical form first:

- strip mnemonic markers (`~`, `_`): `~Save` and `Save` are the same string;
- strip a trailing ellipsis (`…` or `...`);
- strip a trailing shortcut hint like `(Ctrl+S)`;
- strip a trailing colon;
- strings with placeholders (`{1}`, `%1`) must be matched as a template via a regular expression, not as exact text.

Skip the normalization and the same string masquerades as several different ones — and you end up with a giant pile of fake "untranslated" entries that sends you chasing ghosts. For core strings in `.mo`, you first have to unpack the catalog into text (`msgunfmt`, which needs the gettext package), otherwise there's literally nothing to compare against.

One more honesty check on this stage: the coverage table you produce here is *not a fact*. It's built purely from presence-in-catalog: if a translation is in the catalog, the string is counted as translated. But presence ≠ rendering (same `Clipboard` again: it's in `ui-ru.json`, yet the screen shows English because the core draws it). So treat the coverage percentage as an *upper bound* — a hypothesis — not the truth. The truth only arrives with the render pass in Stage 3. Required habit: take a sample of strings that coverage calls "translated" and check them against the real screen, so you can measure how far the catalog drifts from reality.

Command to the agent:

```text
You are a static localization analyzer. Change nothing.

Task: build a full occurrence map for all English strings of the Collabora UI.

Context:
- Writer, Calc, Impress and shared elements must be covered.
- Sources must be split: frontend i18n, ui-json, uno-json, locore-json, lo-core-mo, unresolved.
- Not only count the gaps, but list every place each msgid is used.

Result:
1. A Markdown report with brief statistics.
2. An occurrence map table.
3. A coverage table for all languages.
4. A table of strings that could not be mapped to a source.
5. A list of commands/places to confirm with Playwright.

Format:
- Do not use unclear abbreviations in the tables without expansion.
- For each msgid state the occurrence count.
- For each source_class state how to fix it correctly.

Completeness control:
- The number of unique msgid must add up with the sum per source.
- For each target language there must be counts: translated, missing, same-as-English.
- For each unresolved there must be an explanation of what exactly could not be determined.
```

Control that doesn't rely on trusting the agent:

- The main artifact is *not* Markdown, it's `occurrences.json` or `occurrences.csv`. Markdown can be a nice summary, but it does not replace the full table.
- Each occurrence row needs a stable id, e.g. `occ_000123`. Later the patch, collision map, and verification all reference these ids — they're the join keys.
- Each `msgid` needs an `occurrence_count`. If the agent declares a string "safe" but won't show all occurrences, you can't accept the conclusion.
- The extractor must save raw counts: how many `_()`, how many `_UNO(...)`, how many frontend i18n keys, how many catalog keys it found.
- Each source class gets a separate count, and the sum per source class must either explain the total or explicitly show the overlap.
- For each `msgid`, save not just the file but enough context: neighboring lines, command id, tab/group/control, when extractable.
- For `unresolved` you can't just write "unknown." You need a `why_unresolved` field: command map not found, minified dynamic call, generated text, runtime-only, source outside bundle. "I don't know" with a reason is fine; "I don't know" without one is not.

Independent checks (this is you, recomputing, not taking the agent's word):

- Recompute unique `_()` strings with another command and compare with `direct_key_count`.
- Recompute `_UNO(...)` command ids with another command and compare with `uno_command_count`.
- Pick 20 random occurrence ids and open the source location by hand.
- Pick 20 random `msgid` with occurrence_count greater than 1 and check that *all* the places are listed, not just the first few.
- Check that `coverage.csv` has a row for each language and a column for each key status: missing, same, translated.

Signs of partial completion:

- The agent shows only "top 20 missing".
- The agent counts only `ui-*.json`, but not `uno` and `locore`.
- The agent says "found all strings", but there is no extractor command.
- The agent does not distinguish `msgid` from visible text.
- The report has counts but no raw rows.
- For strings with multiple occurrences only one file is shown.

How to push to completion:

```text
You did the static inventory as a summary, but I need a full verifiable artifact.

Do not change code. Improve only the artifacts:
1. Create occurrences.json with all occurrences, not a sample.
2. Add a stable occurrence_id for each row.
3. Add source_class, app, file, offset/line, call_type, command_id, neighbor_text.
4. Create coverage.csv for all 22 languages.
5. Create extraction_stats.json with raw counts.
6. In Markdown add only a summary and a link to these artifacts.

Done criterion: every msgid from the summary can be found in occurrences.json, and the sum of occurrences per source_class matches extraction_stats.json.
```

### Stage 3. Rendered inventory via the browser

ok so statics told us what *can* be used. It did not prove that any of it is *actually visible to the user*. This stage closes that gap — it's where hypotheses turn into ground truth. We walk every target language across every UI state and look at the actual pixels.

What to check:

- the editor start screen;
- all ribbon tabs;
- dropdown menus;
- context menus;
- sidebar;
- dialogs;
- tooltips;
- the status bar;
- sheet tabs in Calc;
- functions and formulas in Calc;
- tables and pivot tables;
- images, shapes, charts;
- Impress presentation modes;
- in-Collabora system menus, if they are part of the web UI.

One scoping rule: browser-native or OS-native menus that the app doesn't control get marked *out of scope*, not translated through Collabora. Don't try to fix what you don't own.

Now, the practical reality — pulling text off the page is harder than reading `textContent`, and each of these is a place where a naive script silently under-counts:

- tooltips are only visible on hover — you catch them with a separate hover pass; they're not in the static DOM;
- dialogs aren't normal HTML, they're a widget tree (JSDialog) — the text comes from there;
- some dialogs live in nested same-origin iframes — you have to go *inside*;
- the table grid and the slide are a `<canvas>` — there's no text there at all; that text is outside the DOM and out of scope.

And here's a subtle one that trips up automation constantly: to actually *open* a surface, clicking programmatically isn't enough. The editor's menus and dialogs are drawn by the server and only react to *real* input events (real Playwright mouse and keyboard), not to events dispatched from JavaScript — a synthetic right-click or hover will open nothing. On top of that, many dialogs only open from a *prepared state*: an inserted image, chart, or table; a text cursor placed in the body; a selected cell. No prepared state → the button opens nothing → you wrongly record "no dialog here."

The easiest things to miss (keep a separate checklist for these):

- context menus on the canvas: column header, row header, sheet tab, a shape;
- submenus that have to be expanded as a separate step;
- dialogs available only when there is an active selection.

Two more things I want to flag hard: the cache trap and honest accounting of misses. Editor assets are cached for a long time under a name that *doesn't change* when we edit — so "old text on screen" might not be a missing translation, it might just be the cache lying to you. And an ordinary cache-bust doesn't fully save you either: some files are injected by the server bypassing our cache-bust query (the branding script, for one), and `ui-<loc>.json` catalogs load at runtime and also dodge HTML-level busting. So the most reliable render check is a *clean browser profile per run* (no stale cache), plus a cross-check of the served file with a request that bypasses the cache (`curl`, or `fetch(url, {cache: 'reload'})`) — two independent signals beat one. And separately, *honestly record what you couldn't open* (`notReached`): if you didn't reach a menu or dialog, write it down explicitly with a per-item reason, and treat the measured coverage percentage as an upper bound, not a fact. The stuff you didn't reach doesn't vanish; it gets logged.

Command to the agent:

```text
You are a localization QA auditor. Work through the browser/Playwright.

Task: collect a rendered text inventory for all target languages.

Context:
- There is a static report and an occurrence map.
- Writer, Calc, Impress must be checked.
- All main UI states must be walked, including ribbon, menus, context menus, sidebar, dialogs and tooltips.
- No edits allowed.

Result:
1. A rendered strings table: language, app, screen, control, visible text, coordinates or selector.
2. Screenshots of key screens.
3. A list of English leftovers.
4. A list of strings not in the static map.
5. A list of false positives: English values that probably should stay English.

Completeness control:
- For each language there must be the same set of scenarios.
- For each app the same tabs and menus must be walked.
- Each found English leftover must be linked to the occurrence map or marked unresolved.
- Screenshots must have clear names: locale, app, screen, state.
```

Control that doesn't rely on trusting the agent:

- *Before* the run there's a `scenario_manifest.json`: the full list of `locale x app x state x action` tuples. You decide what "complete" means before the agent gets a chance to define it down.
- *After* the run there's a `run_manifest.json`: for each scenario id a status `passed`, `failed`, `skipped`, the time, the screenshot path, the DOM/text dump path.
- You can't accept "skipped" without a reason, and the reason must be machine-readable: missing fixture, feature unavailable, selector timeout, known out of scope.
- Each screenshot has a paired text dump. Screenshot is for humans; the text dump is what you diff automatically.
- Each state has a stable name. `calc.formulas.function-library-open`, not `screen5`.
- For a dropdown or a tooltip, the start screen isn't enough — you need an action log proving the menu was actually opened.
- For RTL languages, check not just the text but the direction/layout: `dir`, menu position, overflow. RTL breakage is invisible if you only read strings.

Independent checks:

- The number of rows in `run_manifest.json` must equal the number of rows in `scenario_manifest.json`.
- For each `passed` row, a screenshot and a text dump must exist.
- For each locale there must be the same number of `passed + failed + skipped`.
- If a language didn't pass a scenario, it doesn't disappear from the report — it stays failed/skipped.
- From the text dumps you can auto-build a list of English leftovers and compare it against the manual report. Two paths to the same number; they should agree.
- Randomly open a few screenshots and confirm they're actually the right language, not a reused image.

Signs of partial completion:

- There are screenshots only for one language or one app.
- There is no list of scenarios before the run.
- There are no failed/skipped scenarios, although real browser runs almost always have at least a timeout or out-of-scope notes. (Zero failures is itself a red flag.)
- Tooltip/context menu are claimed as checked, but there is no action log.
- The agent checked only the visible ribbon tab.
- The agent did not save text dumps and left only images.

How to push to completion:

```text
You did the browser check partially. Do not restate the conclusions.

Do a delta run:
1. First create scenario_manifest.json for all 22 languages, Writer/Calc/Impress and all declared states.
2. Compare existing screenshots/text dumps with the manifest.
3. Build missing_scenarios.csv.
4. Run only missing_scenarios.
5. Update run_manifest.json without deleting failed/skipped.

Done criterion: run_manifest covers 100% of scenario_manifest, and every English leftover is linked to an occurrence_id or unresolved_id.
```

### Stage 4. Collision map

Now that we have both the static and the rendered inventory, we can finally answer the question that determines everything downstream: *which strings are safe to touch?* This is where we sort the easy wins from the landmines.

Risk classes:

| Class | What it means | Can it be translated automatically |
| --- | --- | --- |
| `single-use` | One `msgid`, one context | Usually yes, after checking |
| `same-context multi-use` | Several places, but one meaning | Usually yes, if the translation fits equally |
| `mixed-context` | Several places with different meanings | No, needs splitting or a manual decision |
| `composed-fragment` | A piece of a composed phrase | No, must be rewritten into a whole phrase |
| `source-mismatch` | Visible in UI, but the source is not the expected one | No, determine the source first |
| `core-only` | The string comes from LibreOffice-core | Via PO/MO/UI, not via `ui-json` |
| `technical-name` | Format, function, brand, command name | Often keep English or check terminology |
| `layout-risk` | The translation may not fit or may break RTL/bidi | Only with a visual check |
| `render-path-mismatch` | The string is in the expected catalog but is drawn by another layer (like `Clipboard`) | No, editing the catalog does not help; fix the layer that actually renders |
| `plural-form` | Number-dependent forms (1/2/5 in ru, 6 forms in ar) | Via gettext plural in the core; flat client JSON cannot really express them |

Command to the agent:

```text
You are a localization collision analyst.

Task: based on the occurrence map and rendered inventory, split all English msgid into risk groups.

Context:
- You cannot propose a translation without accounting for all occurrences.
- You must account for languages with different grammar and RTL.
- You must separately mark composed phrases.

Result:
1. A collision map table.
2. For each msgid: risk_class, occurrence count, list of contexts, affected locales.
3. A list of safe candidates for automatic completion.
4. A list of hard cases for a human.
5. For hard cases, state why a simple JSON edit is dangerous.

Completeness control:
- Every msgid from the occurrence map must fall into exactly one risk_class.
- For each mixed-context there must be a reference to the different contexts.
- For each composed-fragment the original phrase assembly must be shown.
```

Control that doesn't rely on trusting the agent:

- The collision map must cover *all* `msgid` from the occurrence map — not just the problematic ones. Every string gets a verdict.
- Each row references a list of `occurrence_id`. No ids → the risk class is unproven, period.
- `single-use` → exactly one occurrence id.
- `same-context multi-use` → several occurrence ids *and* an explanation of why the context is the same.
- `mixed-context` → the different context groups listed out.
- `composed-fragment` → the fragment pattern: which pieces are joined and where it shows up.
- `technical-name` → why English is acceptable: file format, API name, function, brand, common term.

Independent checks:

- Compare set(`msgid`) from `occurrences.json` against set(`msgid`) from `collisions.csv`. The difference must be empty. This is the cleanest invariant in the whole pipeline — use it.
- Compare the sum of `occurrence_id` across the collision map with the occurrence map. Every occurrence must be classified.
- Pick all rows with `occurrence_count > 1` and verify they did *not* get auto-dumped into `single-use`.
- Pick all rows where `neighbor_text` differs and check the agent explained why it called them same-context vs mixed-context.
- Check that rendered leftovers also got a risk class, instead of quietly staying behind in the QA report.

Signs of partial completion:

- The collision map contains only suspicious strings, the rest disappeared.
- There is a risk class but occurrence ids are missing.
- All strings with multiple occurrences are automatically marked safe.
- The agent did not mark composed fragments.
- The agent does not show different context groups for mixed-context.

How to push to completion:

```text
The collision map is incomplete. Improve only the classification.

1. Take the full set of msgid from occurrences.json.
2. Take the current collisions.csv.
3. Build missing_collision_rows.csv.
4. For each missing row add risk_class.
5. For each row with occurrence_count > 1 add context_groups.
6. Do not propose translations at this step.

Done criterion: set(msgid) in occurrences.json is fully equal to set(msgid) in collisions.csv.
```

### Stage 5. Preparing translations

Translations get prepared as a *controlled table*, not as free-flowing text. The distinction matters because a table has cells you can check and statuses you can audit; a paragraph of "here are the translations" has neither.

For each candidate:

- the English `msgid`;
- the context;
- the source class;
- the current translation per language;
- the proposed translation;
- the proposal source: existing LO translation, current catalog, terminology base, manual translation, AI;
- status: safe, needs human, rejected, accepted;
- notes on grammar, length, RTL.

And here's the framing that keeps you out of trouble: you never ask the agent to "translate everything." You ask it to "propose candidates, but do not apply them." Proposal and application are different verbs, and we keep them in different stages.

Command to the agent:

```text
You are a translation assistant for UI localization.

Task: prepare translation candidates, but do not change files.

Context:
- Use only strings with risk_class single-use and same-context multi-use.
- Do not touch mixed-context, composed-fragment, core-only and unresolved.
- For each language give a translation with the UI context in mind.
- If unsure, set needs human, do not guess.

Result:
1. A translation candidates table.
2. For each msgid: context, source class, affected locales, proposed translation, confidence, reason.
3. A list of strings that must not be translated automatically.
4. A list of terms that need a single glossary.

Completeness control:
- Hard cases must not get into the table.
- Each translation must have a reason.
- For each language there must be a status: proposed, existing, needs human, keep English.
```

Control that doesn't rely on trusting the agent:

- `translation_candidates.csv` references `msgid`, `risk_class`, `occurrence_id`, `source_class` and `locale`. Everything joins back to the maps.
- Each row has a status. An empty status means the work isn't finished — treat blanks as "not done," not "fine."
- A translation with no `reason` and no `source` is rejected. Source can be `existing-locore`, `existing-uno`, `LibreOffice-po`, `glossary`, `human`, `ai-proposed`.
- `ai-proposed` gets a *lower* trust level until a human approves it. Be explicit that the model's own translations are the least-trusted input, not the most.
- Don't mix "proposed" with "applied." The candidate table must not itself change any files.
- If a translation is long, attach a layout note: possible overflow, screenshot needed, shorter variant needed.
- For RTL, attach a note: placeholder order, punctuation, directionality.

Independent checks:

- Confirm every candidate row has risk class `single-use` or `same-context multi-use`, if the batch was supposed to be safe-only.
- Confirm no `lo-core-mo` rows snuck into a `ui-json` batch.
- Confirm each target locale has a status for each candidate.
- Confirm glossary terms are used consistently across the table.
- Pick 20 random translations and check, against the occurrence context, that the translation actually fits *there* — not just that it's a valid translation of the word in isolation.

Signs of partial completion:

- The agent translated only Russian, although the task is about all target languages.
- The agent filled only missing, but did not mark existing/keep English.
- There is no translation provenance.
- There is no `needs human` status; the agent pretended to be sure of everything. (Suspiciously total confidence is itself a tell.)
- mixed-context or unresolved strings got into the safe table.

How to push to completion:

```text
The translation table is incomplete. Do not apply a patch.

1. Take the approved safe candidates from collisions.csv.
2. Build a msgid x locale matrix.
3. For each cell state the status: existing, proposed, needs human, keep English.
4. For proposed state translation_source and reason.
5. For needs human state a concrete question for the human.
6. Do not change localization files.

Done criterion: there are no empty cells in the matrix, and no hard-case row got into proposed without human approval.
```

### Stage 6. Handling hard cases

For the hard cases, the agent's job is not to *solve* them — it's to assemble a clean *decision package* so a human can choose fast. Think of the agent as the analyst preparing the brief, not the one signing off.

The package must contain:

- where the string is visible;
- all occurrences;
- why there is a collision;
- which languages suffer;
- solution options;
- pros and cons of each option;
- what has to change in code or catalogs;
- how to verify.

You can allow many options, but it's better to keep them bounded. If there's no clean solution, ask for up to 20 — but require ranking, so the realistic ones float to the top.

Command to the agent:

```text
You are a localization architect. Change nothing.

Task: prepare a decision package for hard cases.

Context:
- We have msgid with collisions or composed phrases.
- A simple translation added to JSON may break other places.
- Targeted solution options must be proposed.

For each hard case give:
1. The English msgid.
2. All places of use.
3. Why the translation conflicts.
4. Which languages are affected.
5. Up to 20 solution options, but the most realistic ones first.
6. Pros and cons of each option.
7. Which option you recommend and why.
8. Which tests and screenshots are needed after the choice.

Completeness control:
- You cannot propose an option without a list of affected places.
- You cannot change files without a human's choice.
- If a new context key/helper is needed, explain the English fallback.
```

Control that doesn't rely on trusting the agent:

- Each hard case gets a `decision_id`, so the eventual patch references an *approved decision*, not free-floating prose.
- Each option lists the affected occurrence ids it covers.
- If an option proposes a split key, it must show the new map: old occurrence ids → new key ids. No hand-waving about "splitting."
- If an option proposes a PO/MO/UNO edit, it must explain why the browser `ui-json` is *not* the right source. (Otherwise you'll fix the wrong layer — the recurring theme.)
- If an option keeps English, it must justify it: term, brand, technical name, no safe context.
- Each option lists its *new* risks: new collisions, fallback, layout, RTL, migration, rollback. Every fix introduces something; name it.

Independent checks:

- Every occurrence of the hard case is covered by at least one option.
- The recommended option doesn't quietly cover only the "easy" subset of occurrences.
- Split keys don't create technical fallback strings leaking into the English UI.
- Each option has a verification plan.
- The human explicitly chose an option *before* any edits happened.

Signs of partial completion:

- The agent proposes one option with no alternatives.
- The agent does not show affected occurrence ids.
- The agent says "better to split the key" but does not show which keys and which places.
- The agent proposes editing `ui-json` for a core/UNO string.
- The agent does not describe rollback.

How to push to completion:

```text
The decision package is incomplete. Do not change files.

For each hard case add:
1. decision_id.
2. The full list of occurrence_id.
3. At least 3 solution options, if there is more than one reasonable path.
4. For each option: affected occurrence ids, new keys/resources, pros, cons, new risks, rollback.
5. The recommended option separately, but without implementation.

Done criterion: a human can choose an option without asking clarifying questions about where the string appears and what will break.
```

## How to make targeted edits

### Safe direct `ui-json`

Let's start with the easy, low-risk path — the safe direct `ui-json` edit. You're allowed to edit when *all* of these hold (and the "all" matters — drop one and you're back in footgun territory):

- the string belongs to `ui-json`;
- it is `single-use` or `same-context multi-use`;
- the translation fits all occurrences equally;
- there are no signs of a composed phrase;
- the translation does not break width/RTL;
- there is a render-check plan.

In this project, do these edits via the existing patch in `editor/Dockerfile` rather than hand-editing an already-built file inside the container. Reason: the Dockerfile patch is reproducible on rebuild, whereas the in-container edit evaporates the moment the container is recreated. Always prefer the reproducible knob.

Command to the agent:

```text
You are an executor of a targeted localization edit.

Task: apply only safe direct ui-json translations.

Context:
- Only msgid from the approved safe-candidates list are allowed.
- Do not touch mixed-context, composed-fragment, uno-json, lo-core-mo.
- Follow the existing patch style in editor/Dockerfile.

Result:
1. A minimal edit.
2. A list of added keys per language.
3. Updated WAL/update-log.
4. Verification commands.

Completeness control:
- Each added key must be from the approved list.
- There must be no mass catalog replacement.
- After the build it must be proven that the key actually appeared in the active ui-*.json.
```

Control that doesn't rely on trusting the agent:

- Before the edit there's an approved list: `approved_ui_json_candidates.csv`. The patch is scoped to *that*, nothing more.
- The diff changes only allowed files and only allowed keys.
- After the build, extract the active `ui-<locale>.json` from the container and confirm the key is *actually there* — not just in the source patch. The patch existing and the patch landing are two different facts (sound familiar?).
- Confirm the value didn't clobber an existing, newer translation.
- Confirm the key wasn't added to a language where it was already translated differently.
- For each added key, there's a rendered scenario — or a stated reason why render is impossible in this batch.

Independent checks:

- Compare set(keys changed in diff) with set(approved candidates). Difference must be empty.
- Compare the active container catalog before vs after.
- Confirm `same-as-English` wasn't miscounted as translated, when the translation matches English on purpose.
- Confirm the UI isn't showing technical keys.

If the agent made too wide a patch — and they love to "helpfully" do more than asked — yank it back hard:

```text
The patch is wider than the approved scope. Revert only your changes of this batch and rebuild the patch from scratch.

Only keys from approved_ui_json_candidates.csv may be changed.
Output a table:
- approved key
- changed file
- old value
- new value
- rendered scenario id

Done criterion: the git diff contains only allowed keys and the update-log describes only this batch.
```

### Context splitting in code

When one `msgid` genuinely means different things in different places, you cannot paper over it with a single translation. You have to *split* it. ok so let's build up the options from how the underlying mechanism works:

1. Programmatic context (`msgctxt`/`pgettext`) exists *only* in the core (`.po`/`.mo`). The client catalogs (`ui/uno/locore-*.json`) don't have it — they're flat dictionaries, "English string -> translation," one value per string. The *semantic* (de-facto) context of a string is real, but on the client there's no technical context separator. So on the client you can only split a homonym by using *different keys* (which means editing the call site in code); true `msgctxt` is a core-level luxury.
2. If context isn't supported, add a context helper that looks up a hidden context key but, when there's no translation, falls back to a normal English string.
3. If the string is composed, replace the pieces with one whole phrase that has placeholders.
4. If the string comes from UNO/core, don't try to split it in the browser JSON — fix the UNO/LibreOffice source.

Here's the bad option, and it's tempting precisely because it looks like it "adds context":

```text
_("Line|shape-tool")
```

The problem: if there's no translation, the user literally sees `Line|shape-tool` on screen. You leaked your internal context machinery into the UI. That's worse than the original homonym.

Better is a real fallback:

```text
translateContext("shape-tool", "Line")
```

where the English fallback stays a clean `Line`, and the translation is free to key off the context. The invariant to protect: *no translation should ever degrade the English UI into showing technical keys.*

Command to the agent:

```text
You are a context-localization developer.

Task: propose a minimal way to split a conflicting msgid without breaking the English fallback.

Context:
- One English text is used with several different meanings.
- A simple entry in ui-json is unsafe.
- A normal English interface must be preserved if there is no translation.

Result:
1. A proposed API/helper or use of an existing context mechanism.
2. A list of places where calls must be replaced.
3. New context keys.
4. Fallback behavior.
5. A translation migration plan.
6. Tests and render checks.

Completeness control:
- All old occurrences must be distributed over the new contexts.
- The English fallback must not show technical keys.
- No new collisions must appear between the new keys.
```

Control that doesn't rely on trusting the agent:

- Before the code edit there's a `split_plan.csv`: old msgid, old occurrence ids, new key, new context, fallback. Plan before patch.
- After the edit, rebuild the occurrence map and *prove* the old occurrences either disappeared or got distributed across the new keys.
- Check the English UI: with no translation, the user must see clean English, not `Line.shapeTool` or `shape-tool|Line`.
- Check the new keys didn't collide with existing keys of a different meaning. (You can introduce new collisions while fixing old ones — watch for it.)
- Check placeholder order works for languages with a different word order.

Independent checks:

- Compare old occurrence ids from the decision package against new occurrence ids after the edit.
- Confirm each new key has exactly the context it was created for.
- Confirm the old msgid is no longer used in the conflicting place.
- Run the rendered scenarios for *all* old places, not just one. The whole point was that there were several.

If the agent did an incomplete split:

```text
The context split is incomplete. Do not add new translations.

1. Take split_plan.csv.
2. For each old occurrence id show where it went after the edit.
3. Build missing_or_unsplit_occurrences.csv.
4. Fix only these places.
5. Rebuild the occurrence map.

Done criterion: all old occurrence ids from split_plan have a new key or an explicitly documented keep-old reason.
```

### UNO and LibreOffice-core

When a string belongs to `_UNO(...)` or LibreOffice-core, you turn the caution up. This is the deepest layer, the build is heavier, and a sloppy edit here can quietly change a string in a place you never looked.

The correct path:

- find the source UNO command or LO resource;
- check whether there is PO context;
- edit the PO, not the binary `.mo`, if that is possible;
- build the `.mo` via the gettext toolchain;
- rebuild the image or carefully replace the resource in the image build;
- check that Collabora actually uses the new resource;
- check all commands that could have used the same English text.

Practical note that bites people: `gettext` (`msgfmt`/`msgunfmt`) usually isn't in the image, so you have to install it. Do that in the *build* Dockerfile, not by hand in a running container — anything you do in a running container is gone on recreate. Same reproducibility lesson as before.

Command to the agent:

```text
You are a LibreOffice/UNO localization specialist.

Task: prepare a plan to fix a string from uno-json or lo-core-mo.

Context:
- A simple ui-json edit is forbidden.
- You must find the correct source: UNO map, PO, MO, UI resource or generator.
- You must not break other commands with the same English text.

Result:
1. Where the string is defined.
2. Which commands or dialogs use it.
3. Whether there is context in the PO/LO source.
4. Which file to change.
5. How to rebuild the resource.
6. How to verify it in the active image.
7. Which neighboring strings may suffer.

Completeness control:
- Do not propose editing .mo by hand as the main path.
- Do not propose a ui-json edit if the UI takes the string from the core.
- State a rollback plan.
```

Control that doesn't rely on trusting the agent:

- The plan shows the full source chain: visible text -> UNO command/dialog -> source catalog -> built artifact -> active container file. If the agent can't draw that chain end to end, you don't make the edit.
- For `.po`/`.mo`, check `msgctxt` or its equivalent. If one `msgid` shows up in several contexts, you cannot blast all of them in one place without analysis — that's the exact mistake this whole document is fighting.
- After the build, check not just the `.mo` file but the *visible UI*, because Collabora may pull the string from a generated UNO JSON or another cache.
- Check every command where the same English text appears in UNO/core, not just the one screen you happened to open.

Independent checks:

- `msgunfmt` (or another gettext tool) must show the expected `msgid`/`msgstr` in the resulting `.mo`.
- The hash of the resulting `.mo` differs from the baseline *only where expected* — no surprise diffs.
- The active container contains the new `.mo` or the regenerated `uno/*.json`.
- The rendered inventory confirms the change in the right place.
- The collision map is updated if the PO context split the meaning.

If the agent proposed a dubious core patch:

```text
The UNO/core plan is incomplete. Do not change files.

Give the source chain for the string:
1. visible text and screen state;
2. command/dialog id;
3. source PO/UI file or generator;
4. build command for .mo/uno json;
5. active container path;
6. all other occurrences of this msgid in UNO/core;
7. rollback.

Done criterion: you can explain why the edit will not affect another meaning of the same English string.
```

## How to control the agent

ok let's zoom out and talk about the agent as a system you're operating, because the failure modes are pretty universal across tools. The agent is genuinely useful, but it has to be *constrained* — left unconstrained it optimizes for "produce something that looks complete," which is not the same as "is complete."

Good rules:

- First read-only analysis, *then* edits. Never interleave.
- Any edit references a concrete artifact: occurrence map, collision map, approved candidates.
- No mass import of fresh PO without comparing versions and contexts.
- No "translate everything" without risk classification.
- Require a report where the numbers add up.
- Require a list of what is *not* covered.
- Require rendered proof for every changed UI scenario.
- Require a separate list of false positives.
- Require an explanation of why a particular source class is fixed in this particular way.
- Keep edits in small batches. Small batches are easy to verify and easy to roll back.

A bad command to the agent:

```text
Translate all English strings into Russian.
```

A good command to the agent — notice it's specific, scoped, and tells it what to do when it gets stuck:

```text
Take only the approved safe candidates from translation_candidates.md.
Apply translations only for source_class=ui-json.
Do not touch strings with risk_class mixed-context, composed-fragment, core-only or unresolved.
After the edit, rebuild the image, check the active l10n files, open Writer/Calc/Impress in ru/uk/ar/zh-CN and attach rendered evidence.
If any step fails, stop and give a report, do not guess.
```

That last line — "if any step fails, stop and give a report, do not guess" — is doing a lot of work. Guessing-instead-of-stopping is the single most expensive agent behavior.

### Strict protocol for working with the agent

To stop the agent from doing 30% of the task and presenting it as 100%, hand it the task as a *contract*, not a wish. The structure:

1. Scope is fixed before the work.
2. The agent must create a manifest.
3. The agent must fill the raw table.
4. The agent must output check counts.
5. The agent must list skipped/failed.
6. The agent must explicitly write what is not covered.
7. A human or an independent check compares counts and artifacts.
8. Only after that is the result considered accepted.

The formula of a good task — basically a template you can reuse:

```text
Role:
You are not a translator, but a localization auditor. Your goal is to provably collect a full artifact.

Scope:
List the included languages, apps, files, UI states. Do not widen or narrow the scope without a separate list of changes.

Forbidden:
Do not give summary-only output. Do not sample. Do not skip failed/skipped. Do not make edits.

Required artifacts:
1. machine-readable manifest;
2. full CSV/JSON table;
3. Markdown summary;
4. counts/invariants;
5. list of gaps/skips/unresolved;
6. reproduction commands.

Acceptance:
The work is accepted only if the counts add up and all expected rows are present.
If you cannot finish or cannot cover everything, stop and output missing_work.csv.
```

### How to catch partial completion

Let me give you the tells. These are the phrases and shapes that mean "the agent sampled and is hoping you won't notice":

- "The main languages" instead of the full language list.
- "Key screens" instead of a manifest of all screens.
- "For example" in a table where a full list is needed.
- "Top N" without a full export.
- No row for failed/skipped.
- No raw JSON/CSV.
- No hashes of input files.
- No way to repeat the extraction.
- No link between the summary and the raw rows.
- No links from the patch to an approved decision/candidate.
- No before/after evidence.

And here's the key behavioral insight: when you spot this, do *not* say "check more carefully." That almost always returns another nice summary — you've asked for prose and you'll get prose. Instead, give a *delta task* with a machine-checkable done criterion:

```text
You produced an incomplete result. Do not repeat the summary.

Build only the missing artifact:
- file: missing_work.csv
- input: current artifact X
- check: invariant Y
- done criterion: set(A) == set(B)

No new conclusions until the artifact is built.
```

### How to force completion to a full result

This is the workflow that actually drives an agent to 100%, and it works because it removes the agent's freedom to redefine "complete" on each pass. The trick is to compute the gap *explicitly* and then run only the gap:

1. First ask the agent to build the *expected* set. For example: all languages, all apps, all scenarios, all `msgid`.

2. Then ask it to build the *actual* set. For example: what was actually checked, what's actually in the table, which screenshots got saved.

3. Then ask it to build the *gap* set. For example: `expected - actual`.

4. Then run *only* the gap set. This is what stops the agent from doing yet another selective "full" pass — there's nothing left to sample, only the named gap.

5. After completion, recompute the invariant again.

Example command:

```text
Do not do another full audit.

1. Read expected_scenarios.csv.
2. Read run_manifest.json.
3. Build missing_scenarios.csv as expected - actual.
4. Run only missing_scenarios.csv.
5. Update run_manifest.json.
6. Output counts: expected, before_actual, missing_before, added, missing_after.

Done criterion: missing_after = 0 or each remaining row has status blocked with a reason.
```

### When you can trust the agent's output

The mental shift I want to leave you with here: you don't trust "the agent," you trust the *artifacts*. The agent is a fallible string-generator; the artifacts are checkable. So you accept the output when:

- there is a full expected set;
- there is a full actual set;
- there is a gap set;
- there are machine-readable rows;
- there is a reproducible command;
- the counts add up;
- skipped/failed are not hidden;
- raw rows can be checked selectively;
- the patch references approved ids;
- the rendered proof covers the changed states.

If even one of these is missing, treat the result as *preliminary*. Not wrong, necessarily — just not yet trustworthy.

## How to verify completeness

One screenshot is not enough. I know, I keep saying screenshots are ground truth — they are, but *one* screenshot proves one pixel-state in one language. Completeness needs breadth.

So you want several independent cross-checks, coming at the problem from different angles:

1. Static extraction: how many strings are found in the code.
2. Catalog coverage: how many strings exist in the catalogs per language.
3. Occurrence map: where each string is used.
4. Rendered inventory: what is actually visible in the browser.
5. Collision map: where one English text has different meanings.
6. Patch coverage: which strings were actually changed.
7. Rendered regression: what changed after the patch.
8. Visual proof: before/after screenshots.
9. False positives: English strings that should stay.

Control questions — read these as a checklist you literally walk down:

- Did all 22 languages go through the same set of scenarios?
- Are there strings visible in the browser but absent from statics?
- Are there strings present in statics but not appearing in the render?
- Do all changed keys have an occurrence map?
- Is there a single translation applied to different meanings?
- Are there composed phrases made of separate words?
- Did RTL languages break?
- Did labels overflow buttons?
- Did technical keys appear instead of the English fallback?
- Did icons/tooltips/menus disappear after the edit?

And now the important distinction that's easy to blur: **completeness and quality are different things.** Everything above answers "is there a translation and is it visible." None of it answers "is the translation actually *good*." The invariants adding up prove that nothing was missed and that the result is reproducible — they prove *coverage*, not *correctness*. Quality is a separate pass, ideally by a strong model that genuinely knows the target language, working directly over the render/screenshots with context in mind. And the final polish is best done by a native speaker — more precisely, a native *subject-matter expert* who knows the domain terminology. The machine gets you to "complete"; a human gets you to "correct."

### Checks by type of work

Here's the cheat-sheet version — for each kind of work, what the agent typically leaves undone, how you catch it independently, and how you force it to the finish line:

| Work | What the agent usually leaves undone | How to check independently | How to push to completion |
| --- | --- | --- | --- |
| Baseline | Takes part of the languages or the wrong container | Compare the locale set with the code, recompute hashes of extracted files | Require `baseline_manifest.json` and `missing_catalogs.csv` |
| Static extraction | Gives a summary instead of a full occurrence map | Recompute `_()`, `_UNO(...)`, i18n keys with another script | Require `occurrences.json`, `extraction_stats.json`, `unresolved.csv` |
| Catalog coverage | Checks only `ui-*.json` | Compare `ui`, `uno`, `locore`, `.mo` separately | Require a coverage matrix per source class |
| Rendered inventory | Checks one language or one tab | Compare `scenario_manifest` and `run_manifest` | Require `missing_scenarios.csv` and a delta run |
| Collision map | Classifies only the obvious problems | Compare set(msgid) of occurrence map and collision map | Require full coverage of all `msgid` |
| Translation candidates | Translates everything indiscriminately | Check risk_class and source_class for each candidate row | Remove hard cases from the batch and require statuses per locale |
| Direct ui-json patch | Changes more keys than approved | Compare diff keys with approved candidates | Narrow the patch to the approved set |
| Context split | Splits part of the occurrences, leaves conflicting places | Compare old occurrence ids with new occurrence ids | Require `missing_or_unsplit_occurrences.csv` |
| UNO/core patch | Proposes the wrong fix layer | Check the source chain down to `.po/.mo/uno json` and rendered UI | Require a source-chain report before the edit |
| Verification | Shows only successful screenshots | Check failed/skipped and before/after text dump | Require a full verification manifest |
| Upgrade maintenance | Carries old patches over blindly | Compare old/new occurrence map and changed contexts | Require a release diff matrix |

### Example of independent invariants

Let me make the invariant idea totally concrete. Suppose the static report claims:

```text
locales = 22
direct_ui_msgid = 436
referenced_uno_labels = 300
global_uno_labels = 813
```

Then independent checks must exist that *recompute* each of those numbers a different way:

```text
count(locales_from_project) == 22
count(unique direct _() msgid in selected code segments) == 436
count(unique resolved UNO labels from referenced commands) == 300
count(unique labels in global UNO map) == 813
```

And here's the line I want you to keep: if the agent can't show *how* these numbers were recomputed, it isn't an audit — it's a retelling. An audit is reproducible; a retelling is just confident.

### How to accept partially blocked work

Sometimes a full pass is genuinely impossible, and that's fine — you just have to make the impossibility *explicit* rather than silent. Real cases: Playwright is busy, a fixture won't open, the source is minified, a `.po` is missing, the command is created dynamically.

This is normal. But "blocked" has to be a documented state, not a quiet gap.

For each blocked item, you want these fields:

| Field | What to write |
| --- | --- |
| `blocked_id` | Stable id |
| `scope_item` | What exactly is not covered |
| `reason` | Why it is not covered |
| `attempted` | What has already been tried |
| `needed` | What is needed to close it |
| `risk` | What may be wrong because of the block |
| `owner` | Agent, human, external tool |
| `next_check` | How to come back to verify |

The bar: "could not verify," with none of these fields, does not count as a report. It counts as a shrug.

## How to maintain final artifacts

For this to be *sustainable* — i.e., survivable across people and across time — you need more than a pile of edits. You need a small set of living documents that capture state.

Recommended files:

| File | Purpose |
| --- | --- |
| `localization_baseline.md` | Image version, language list, covered apps |
| `localization_occurrences.json` | Machine-readable map of all occurrences |
| `localization_coverage.md` | Summary of translated/missing/same per language |
| `localization_collisions.md` | All context risks |
| `translation_candidates.md` | Translation candidates and their statuses |
| `translation_decisions.md` | Human decisions on hard cases |
| `translation_verification.md` | Final checks and screenshots |
| `translation_glossary.md` | Terms that must be translated consistently |

The project already has a static report:

```text
docs/COLLABORA_LOCALIZATION_STATIC_INVENTORY.md
```

Treat it as the *first* baseline artifact — but not as the final proof. (Static, remember, is hypotheses.) The next steps up the ladder are an occurrence map with contexts and then a rendered inventory.

After a pass, you'll also have a coverage report — e.g. `.qa/l10n/REPORT.md` (how many visible strings, how many translated per language, and the gaps split into "fixable in client JSON" vs "core `.mo` only") plus a machine-readable matrix `.qa/l10n/visible-coverage.csv` (one row per UI string, status per language). *This* is the verifiable basis for deciding what to fix and in which layer — coverage tied to render, not coverage guessed from catalogs.

## Strategy for working with Collabora sources

ok this is the architectural section, and there's one decision that drives everything, so let me state it cleanly. The project's goal is to **build Collabora Online from source** (the coolwsd server + the browser bundle) — *not* to patch a ready-made image. But — and this is the part people get wrong — the **LibreOffice/Collabora Office core is NOT built from source**: we take it as a pinned prebuilt binary (engine-assets) and patch its strings as *data* (`.po`→`.mo`).

Why this exact split? Because deep localization keeps surfacing things that can only be fixed in the *Online* source — string concatenation in JavaScript, a contextual translation API, client catalogs. And everything we change in the UI (texts, sizes, design) lives in the Online layer, not in the core. So we build the layer we keep editing, and we pin-and-patch the layer we don't. Here reliability and control beat "fast to prod."

The quick path we're moving away from usually looks like:

```text
FROM collabora/code:latest
```

…and then the Dockerfile patches already-built `bundle.js`, `bundle.css`, `cool.html`, `l10n/ui-*.json`, and image resources with `sed` and `cp`. This is acceptable as a **temporary stopgap** (a small branding tweak, an urgent hotfix), but it is not a foundation for localization.

Why you can't live on it long-term — go through these and you'll feel why each one compounds:

- `latest` changes without your control. Today's bytes and tomorrow's bytes differ.
- A minified `bundle.js` is a terrible place to do contextual string splitting.
- A `sed` patch against built output breaks on any upstream change.
- You can't cleanly add a new contextual localization API.
- It's hard to know which source file produced a string, or to carry a fix across updates.
- It's hard to *prove* a patch fixes the correct layer instead of masking the problem.

So we move in stages — but the destination is fixed: **building Online from pinned source** (with the core staying a pinned prebuilt binary).

And pin the version *hard*. Translations are made for a **specific** version: the set of strings and their `msgid`/`msgctxt` are version-dependent. Pin **a matching pair** — the Collabora Online commit/tag AND the prebuilt core/engine-assets version (both in `upstream.json`). A version update is a separate, controlled event with acceptance testing of all translations, not a casual "pull latest."

Let me be honest about the cost, because people fear the wrong thing. Building **Online** from source is manageable — officially it's `./configure && make` on top of prebuilt engine-assets, somewhere from minutes to about half an hour, and it runs locally. Building the **core** from source, on the other hand, is heavy (tens of gigabytes, hours) — so we don't do it. (See "When you would build the LO core from source" below.) The scary one is the one we avoid.

### Stage 1 (temporary): remove nondeterminism of the ready-made image

Until the source build is in place, you still can't sit on `latest` — at minimum, kill the nondeterminism of the ready-made image.

You need to:

1. Stop using `collabora/code:latest`.
2. Pin the image by version or digest.
3. Record the pinned image in the baseline.
4. Store hashes of the active `bundle.js`, `ui-*`, `uno/*`, `locore/*`, `.mo`.
5. Build every report only against that pinned baseline.

Example:

```text
collabora/code@sha256:<digest>
```

or a concrete tag if a digest genuinely can't be used.

Command to the agent:

```text
You are a localization release engineer. Do not change anything.

Task: check whether the Collabora version is pinned reproducibly.

Result:
1. Find which image/tag/digest is used for the editor.
2. Say whether latest is used.
3. Report the digest of the active image.
4. Propose the minimal pinning edit.
5. Say which baseline artifacts must be rebuilt after pinning.

Completeness control:
- The current Dockerfile/compose path must be listed.
- The current image id/digest must be listed.
- If latest is used, mark it explicitly as risk=high.
- Do not change the Dockerfile without separate approval.
```

### Stage 2 (interim): patches as units, not long `sed` chains

While the image is still prebuilt, stop keeping changes as long `sed` chains. This is the intermediate rung on the way to source — structured enough to reason about, not yet the final form.

Prefer a structure like:

```text
editor/
  Dockerfile
  patches/
    collabora-online/
      0001-contextualize-line-label.patch
      0002-fix-composed-open-list-label.patch
    libreoffice-core/
      0001-ru-pivot-field-translation.patch
  scripts/
    extract-active-collabora-assets.sh
    build-l10n-occurrence-map.py
    verify-active-catalogs.py
  manifests/
    upstream.json
    patchset.json
```

Even if a patch is still applied to a built image, describe it as a *patch unit* with a known identity:

- what it changes;
- why this is the correct source class;
- which upstream digest it applies to;
- which occurrence ids it closes;
- which rendered scenarios verify it;
- how to roll it back.

This keeps the repo manageable: the application stays here, and every editor-integration patch has explicit boundaries instead of being smeared across a shell one-liner.

### Target level: build from pinned source

This is the working base — the destination. From source we build **Collabora Online** (the coolwsd server + the browser bundle): keep a fork or submodule pinned to a commit, not a loose copy. The **LibreOffice/Collabora Office core is NOT built from source** — it's a pinned prebuilt binary (engine-assets), and we patch its `.mo` strings as data (our `.po`). Net effect: full control over the interface, *cheaply*, because everything we change in the UI lives in the Online layer.

What each layer lets you change — this table is the whole justification for the split, so read it as "what do I actually pay for the core build, and the answer is: almost nothing":

- **Texts** (menus, ribbon, tooltips, dialogs) — all of them: data (client `ui/uno/locore-<lang>.json` + core `.mo` from our `.po`) plus a little Online code to split concatenated phrases and disambiguate homonyms. No core build needed.
- **Element sizes** — CSS (and some JS). No core build.
- **Element design** (colors, shapes, spacing, icons) — CSS + SVG icon replacement (deeper changes — JS). No core build; this is exactly how the glass theme is already done.

The *only* thing that requires building the core is rendering the document itself on the canvas (the Calc grid, the slide, in-cell text). That's document content, not UI elements. (See "When you would build the LO core from source.")

```text
third_party/
  collabora-online/      # git submodule or pinned fork, pinned commit (BUILT from source)
editor/
  engine/                # pinned LO core engine-assets (prebuilt binary, NOT source)
  l10n/
    overrides/
      core/<lang>.po      # our translations of core strings, with msgctxt → compiled to .mo
      client/<lang>.json  # our overlays for client strings
  patches/                # Online CODE changes ONLY (context API, splitting concatenation)
  build/                  # deterministic Online build from source + applying the data
  manifests/
    upstream.json
    patchset.json
```

The key split — and internalize this one, it prevents a lot of mess — is **translations separate from code**:

- **Translations are DATA.** They live as files: `.po` with `msgctxt` for core strings, JSON overlays for client strings. During the source build they're deterministically compiled and merged into `.mo` and the catalogs. Data files are easy to review, easy to hand to native speakers, and easy to scale to 30–40 languages.
- **Patches are CODE only** (a new contextual localization API, rewriting concatenated phrases into whole strings with placeholders). Translation data and code patches never get mixed into one change.

Why a fork/submodule beats a plain copy:

- upstream history is preserved; you can rebase/merge;
- it's clear which files differ from upstream;
- it's easier to check that a fix applies to a new version;
- there's less risk of editing generated output instead of source.

Where to send things upstream — and don't cross the channels:

- **translations go to Weblate** (the LibreOffice/Collabora translation platform), not via GitHub PR;
- **code changes** (context API, concatenation fixes) go as a normal PR to Collabora Online or LibreOffice.

One more cost to name out loud: building from source means you **backport upstream security fixes yourself**. That's yet another reason a version update is a controlled, accepted event — not "pull the latest and ship it."

### Which layer to fix (core or client)

Collabora Online doesn't own every string. Part of the interface comes straight from LibreOffice-core: `.ui`, gettext `.po/.mo`, UNO command metadata, dialogs, sidebar. That's exactly why the LO core is pinned as a prebuilt binary (engine-assets) and its strings are patched as data (`.mo` from our `.po`) — without building the core.

But before *every* fix you still have to prove which layer the string lives in — otherwise the fix lands in the wrong place. (Yes, this is the render-path attribution again; it shows up everywhere because it *is* everywhere.)

- the string really comes from LO-core, not from a client `ui-json`/`uno-json`;
- there's a concrete PO/UI/source file;
- there's a build path to `.mo` or a generated resource;
- there's a rendered scenario that proves the result on screen.

So: client strings → edit our JSON overlays; core strings → our `.po` with `msgctxt`. The layer is chosen by *proof*, not by guesswork. (If you remember one sentence from this section, that's it.)

### When you would build the LO core from source

Almost never. You build the core from source *only* to change **how the document itself is rendered** (how the core draws the Calc grid, the slide, in-cell text) or **core C++ behavior**. That's document content, not UI elements — for texts, sizes, and UI design you do not need it.

This is the heaviest path: "a few hours even on the fastest computer," the image balloons to ~30 GB, and normally only Collabora's own CI bothers. Tellingly, even the official "build CODE for Web" does *not* rebuild the core — it drops in prebuilt engine-assets. So treat a full core build as an optional escalation, never the default. If you find yourself reaching for it during localization, stop and re-check the layer — you're almost certainly in the wrong one.

### What not to do

A short list of anti-patterns. Each of these felt reasonable to *someone* at some point, which is exactly why they're worth naming:

- copy the whole Collabora source into the app repo without an upstream link;
- keep using `latest`;
- edit minified `bundle.js` as the primary long-term mechanism;
- mass-import fresh PO/JSON without an occurrence/collision map;
- mix app frontend translations, Collabora browser UI, and LibreOffice-core in one patch batch;
- keep translations as code patches instead of data files (`.po`/JSON overlays);
- update the editor version in prod without full acceptance of the translations ("quick hack to prod");
- accept a patch that can't be tied to a concrete upstream commit or image digest.

### Completeness control for the source strategy

This strategy earns its own artifacts — the documents that make the architecture checkable rather than aspirational:

| Artifact | What it proves |
| --- | --- |
| `upstream.json` | Which Collabora and LibreOffice versions are used |
| `patchset.json` | Which patches apply, what they belong to, which occurrences they close |
| `source-build.md` | How to build the editor image from source or patch series |
| `source-diff-report.md` | How the fork differs from upstream |
| `generated-vs-source-map.json` | How bundled/generated strings map to source files |
| `release-diff-matrix.csv` | What changed on an upstream update |

Invariants:

- the editor image must not be `latest`;
- Online is built from pinned source; the LO core is a pinned prebuilt binary/engine-assets; both versions are fixed in `upstream.json` and **match**;
- translations are stored as data (`.po`/JSON overlays), not as code patches;
- every patch (code only) has an upstream base commit, an owner, and a reason;
- every translation entry and every code patch links to occurrence ids;
- every source-level split updates the occurrence map;
- every version update passes full acceptance before promotion to prod and recomputes the release diff matrix;
- generated output is not edited when a source-level path is available.

Command to the agent:

```text
You are the architect for a source-level Collabora localization strategy.

Task: propose how the current project should move from patches against a ready-made image to a reproducible source-level scheme.

Context:
- The editor may currently be built from a ready-made Collabora image.
- Careful localization fixes are needed, including context splits and PO/MO.
- You cannot simply vendor a huge source tree without a maintenance plan.

Result:
1. The current editor build method.
2. Risks of the current method.
3. Minimal pinning plan.
4. Patch-series plan for the current repo.
5. Fork/submodule plan for Collabora Online.
6. Separate decision on whether LibreOffice-core source is needed.
7. List of new artifacts.
8. Step-by-step migration plan.

Completeness control:
- The current image/tag/digest must be listed.
- It must explicitly say which edits remain image-level and which should become source-level.
- There must be a rollback plan.
- There must be an upstream update strategy.
- There must be a way to verify that patches apply to the correct version.
```

## How to maintain after Collabora updates

Here's a place people get burned: on a Collabora update you cannot just carry the old patch over. The ground shifted underneath the patch.

The same caution applies to third-party translations — Collabora is *not* stock LibreOffice. Collabora has its own strings and its own notebookbar, so "grab a fresh LibreOffice language pack and drop it in" blindly is dangerous: some strings won't match by id or context, and some will overlay wrong. *Any* import of third-party translations gets checked against version and contexts first.

So a version update is a controlled event with full acceptance — not a single-patch transplant. The order:

1. Bring up the new pinned version **in a non-prod environment first**, leaving prod untouched: the new Collabora Online commit + a **matching** prebuilt core/engine-assets version.
2. **Rebuild Online from source** for the new version (the core is taken as a prebuilt binary/engine-assets, not rebuilt).
3. Run **full acceptance, not a smoke test**:
   - rebuild the occurrence map and coverage;
   - run the render ground-truth (a screenshot per object) across **all** target languages;
   - produce a drift-diff of all UI strings against the previous version.
4. Triage what the update broke: moved or renamed `msgid`, changed `msgctxt`, new English strings, removed strings, re-introduced phrase concatenation.
5. Re-apply (rebase) our translation data and code patches onto the new version and fix the breakage.
6. **Only after full acceptance passes** — promote to prod. Reliability over speed, every time.

This acceptance is the *gate*: the same coverage invariants and render drift-diff run in CI on every version bump and must pass **before** promotion. A screenshot per object, plus a second verification pass (see "The proof principle"), is the only basis for calling an update accepted. No green gate, no prod.

Command to the agent:

```text
You are a localization release auditor after a Collabora update.

Task: compare the old and new baseline and say which localization patches are safe to carry over.

Context:
- Old patches may have been tied to old source strings.
- New PO/JSON may have different contexts.
- You cannot mass-carry-over without checking.

Result:
1. A table of unchanged keys.
2. A table of removed keys.
3. A table of new keys.
4. A table of changed occurrences.
5. A list of patches and translation entries that can be kept.
6. A list of patches and translation entries that must be reviewed.
7. A full acceptance plan (not smoke): render ground-truth across all languages + a drift-diff against the previous version.

Completeness control:
- Each old patch key must be classified.
- Each new English leftover must be linked to a source class.
- If the context changed, the patch/translation must be marked needs review.
- Promotion to prod only after full acceptance passes.
```

## Scaling to many languages

When you go from 4 languages to 30–40, the naive instinct is to redo all the work per language. Don't — that scales linearly into a wall. The trick is to notice which work is language-independent and only pay per-language for the part that genuinely is.

The work splits into two levels:

- **The surface is captured once.** The list of all places where each string appears (the occurrence map) does *not* depend on the language — build it once, reuse it for everyone.
- **Coverage per language is computed from data.** For a given language it's enough to check the strings against its catalogs and `.mo` — a pure file computation, no browser, scales to any number of languages basically for free.

But there's one thing you *cannot* compute from data: how the translation actually *looks* on screen — line wrapping, overflowing a button, RTL layout, context collisions. That's only visible in the render, and it has to be checked per language. And the browser is usually one per instance, so it's the bottleneck. The fix is to parallelize: spin up several VMs, one language per machine, each with its own editor and browser; then the screenshot passes run in parallel. Throw machines at the part that doesn't compress, keep the rest as data.

## Practical rollout order

ok here's a realistic order to actually do all this, end to end. Notice it front-loads the *maps* and only touches files well after we understand the terrain:

1. Finish the occurrence map.
2. Do the rendered inventory via Playwright.
3. Build the collision map.
4. Pick the safe candidates.
5. Agree the glossary for frequent terms.
6. Apply a small batch of safe `ui-json` translations.
7. Rebuild the image.
8. Check the active catalogs.
9. Run a Playwright smoke over all languages.
10. Run a full Playwright over the key languages: ru, uk, ar, zh-CN, plus several European and RTL ones.
11. Fix width, RTL, composed-phrase problems.
12. Move on to hard cases.
13. For hard cases, let a human choose the solution.
14. Apply context split or PO/MO/UNO edits in small batches.
15. After each batch, update the maps and the verification report.

## Minimal definition of done

A localization batch is *done* — actually done, not "looks done" — when all of these hold:

- all changed strings are in the occurrence map;
- all changed strings have a risk classification;
- there are no changed strings from forbidden classes without a separate decision;
- translations are applied to the correct source class;
- the active container actually contains the new values;
- the rendered inventory after the edit shows no new English leftovers in the affected places;
- screenshots confirm the result;
- RTL and UI width are checked for the affected languages;
- there is a false-positives report;
- there is a rollback plan;
- the update-log describes what was changed and why.

## The main rule

Let me end where the intuition points. An AI agent is a *great* fit for collecting the map, finding gaps, preparing candidates, and checking regressions — the high-volume, mechanical, "go look at 1842 things" work. What it must *not* do is "catch up on all the translations" by itself, without context. That's the one move that quietly wrecks everything, because translation-without-context is exactly the problem this whole document exists to prevent.

So, the correct role of the agent:

- collect the facts;
- show all places of use;
- separate the safe from the dangerous;
- propose options;
- apply only approved targeted edits;
- prove the result by rendering.

And the correct role of the human:

- approve terminology;
- decide mixed-context cases;
- choose the architectural option for splitting keys;
- accept the risk of leaving an English term;
- finally accept the visual result;
- check translation quality as a native subject-matter expert, not only its presence.

That division of labor — machine for *coverage*, human for *correctness* — is the whole thing. Get that right and the rest is just running the loop.
