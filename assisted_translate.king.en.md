# Assisted localization of Collabora Online

This document describes a careful workflow for fully localizing a Collabora Online–based project with the help of an AI agent. Read it slowly. It is not tied to a specific tool, and that is the first thing that should worry you, because it means the thing it describes is everywhere. "Agent" below means any assistant that can read the project, run commands, analyze code, prepare reports, propose edits, and verify the result: Codex CLI, Claude Code, an OpenRouter agent, a local LLM agent, or anything similar — anything, that is, that you have invited in and that will now go walking through your files in the dark while you sleep.

Main idea: localizing Collabora Online is not the same as filling in missing keys in JSON. It only looks that simple, the way a still pond looks shallow. You first have to understand where exactly each English string is used, by which mechanism it gets translated, whether it has different contexts, and only then make targeted edits. Skip that understanding and the work will smile at you and lie.

The document is deliberately written as a working manual, not a short cheat sheet. If an engineer is seeing Collabora Online for the first time, it matters not only to know the list of files, but also to understand why simple actions like "add a translation to JSON" can produce a false positive — and a false positive here is not a small thing. One screen gets fixed, another breaks somewhere you are not looking, and a grep check pats you on the shoulder and tells you, kindly, that "the translation is there." It is there. It is just not where you think, and it is not doing what you think.

A separate emphasis is on controlling the AI agent. An agent can look you in the eye and say it "checked all languages" or "built a full table," and it will sound certain, and it will be wrong, because in practice it often samples: a few languages, a couple of tabs, the first grep matches, part of the catalogs — and reports the part as the whole, the way a child reports the closet is empty without opening the door. So the agent's result should be accepted only when it leaves behind verifiable artifacts: a machine-readable table, a scenario manifest, a list of input files with hashes, screenshots, DOM/text dumps, reproduction commands, and numbers that can be recomputed independently. Trust the artifacts. Never trust the smile.

## Short conclusion

If a string is not translated in `ui-*.json`, that does not yet mean you can just add a translation and consider the task done. That is the comforting version. Here is the true one.

Reasons:

- One English `msgid` may appear in several places in the interface — and the same name can belong to several different things.
- In different places the same English text may need different translations.
- Some strings are parts of composed phrases, not standalone phrases; they are limbs, not bodies.
- Some labels come not from `ui-*.json`, but from UNO or LibreOffice-core, from deeper down.
- Some English values are better left in English: format names, technical terms, function names, brands. Touch them and you break something true.
- A translation can be linguistically correct but break button width, RTL layout, a tooltip, a menu, or a dialog.
- A translation may already be in the catalog yet still not appear on screen, if the string is rendered by a different layer. The catalog will swear it is doing its job.
- Ready-made third-party translations (a fresh LibreOffice language pack) cannot be dropped in blindly: Collabora differs from stock LibreOffice, and some strings will not match. What looks like a gift is sometimes a thing wearing the shape of one.

The good news, though, and there is good news, so hold onto it: **almost all localization, and all UI element texts, sizes, and design, are reachable without building the LibreOffice core** — they live in the Collabora Online layer (data + CSS + a little code). Building the core is needed only to render the document itself. You do not have to go all the way down into the dark to fix what people actually see.

So the correct path is:

1. Collect all English strings.
2. Collect all the places where each string appears.
3. Split strings by source: `ui-json`, `uno-json`, `lo-core-mo`, frontend i18n, generated/composed text, unresolved.
4. Build a map of contexts and possible collisions.
5. Translate the safe cases first.
6. For risky cases, do context splitting or edit the correct PO/MO/UNO source.
7. Verify every edit by rendering, not just by grep over files. Grep tells you what the files say. Only the render tells you the truth.

## What exactly is hard

In a normal application there is often a single localization layer, and you can almost relax: code calls `t("Save")`, the catalog stores the translation, the UI shows the translation. One door, one room, one light switch.

In Collabora Online there are more layers. There are always more layers.

| Layer | What lives in it | How it is usually fixed |
| --- | --- | --- |
| App frontend | The project's wrapper around Collabora: login, files, profile, modals | `frontend/src/i18n/messages/*.json` |
| Collabora browser UI | Ribbon/notebookbar, part of the menus, tooltips, panels, buttons in web code | `l10n/ui-<locale>.json`, in this project via a patch in `editor/Dockerfile` |
| UNO command labels | Labels of LibreOffice commands that Collabora invokes via `_UNO(...)` | `l10n/uno/<locale>.json` or the source that generates these catalogs |
| LibreOffice-core | Dialogs, server/core UI, `.ui`, gettext, some sidebar and dialog strings | `.po` -> `.mo`, then rebuild or replace resources in the image |
| Composed strings | Phrases assembled from several translatable or non-translatable pieces | Rewrite into a whole phrase with placeholders |
| System elements | Browser menus, OS-native elements, some file picker/clipboard prompts | Usually outside the app's control |

Important, and this is where people get hurt: if a string belongs to `ui-json`, editing `.mo` may do nothing. If a string belongs to `lo-core-mo`, adding a key to `ui-ru.json` may do nothing. You can work for an hour on the wrong layer and the screen will not so much as flicker. So you have to determine the source first.

And even the source cannot be inferred from the mere fact that the string sits in some catalog. The catalog is not a confession; it is an alibi, and a bad one. Example: the string `Clipboard` is present in `ui-ru.json` with a Russian translation, sitting right there where you can see it, and yet in the ribbon it is still shown in English — because that label is drawn by the core, and the client catalog is not used there at all. So "the string is in the catalog" and "the string is actually taken from this catalog" are different things, and the gap between them is exactly where a day of work goes to die. The real source is confirmed only by experiment: change the string in the candidate catalog, rebuild, bust the cache, and see whether the screen changed. The screen is the only witness that does not lie.

Note also that the same English string can live in several layers at once — both in the client catalog and in the core `.mo`. It can be in two places, three places, looking back at you from each. So the source of a string is not necessarily a single value from the list; it is the *set* of layers where it occurs. Which layer actually draws the text on screen is decided by the render path (see below), not by the mere fact that the string is present in one of the catalogs.

In practice, when this was measured on a real project, most of the gaps turned out to be in the client JSON, not in the core; and some strings that were formally present in the catalog were still rendered in English, present and absent at the same time, like a name in a book nobody will read aloud. So the "what fixes what" mapping cannot be taken on faith — it has to be checked on screen. Faith is not an artifact.

## Why adding a translation directly is dangerous

Imagine the key `Illustrations`. Hold it in your hand a moment.

If it is used only as a ribbon group name, the translation `Иллюстрации` may be correct, and nothing bad happens, and you go home.

But if somewhere — and you will not know where until you look — there is a composed message like:

```text
No + Illustrations
```

then a naive dictionary translation gives something like:

```text
Нет Иллюстрации
```

while the correct Russian is:

```text
Нет иллюстраций
```

For English such slicing often looks fine, because English is forgiving, it tolerates short dictionary pieces and shrugs. For Russian, Ukrainian, Arabic, Hebrew, Farsi, Japanese, Korean, Thai, and many other languages such slicing may be wrong, and it will be wrong in front of a native speaker, which is the only audience that matters.

More examples of risky words. Read them as a list of things that are not what they appear to be:

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

Conclusion: a translation must be tied not only to the English text, but to the place where it is used. A word with no place is a word with no leash.

## Basic terms

Learn these. You will be saying them to yourself later, in the quiet, while the build runs.

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

The work is best split into stages, and you must take them in order, the way you check the locks in order. You must not start with a mass translation edit. The mass edit is how it gets you.

## Principle of provability

The most reliable proof here is what is actually drawn on screen. A screenshot is the only ground truth; everything else is testimony. A JSON catalog, grep, the contents of `.mo`, and even the very fact that the code has a `_("...")` call — these are only hypotheses: they say the translation *can* apply, but they do not prove it applied in this exact place, on this exact paint, where the user is standing. So the source and translation of each string are confirmed by a separate pass **over every object** of the interface (not over a sample) — open the element and look at it with your own eyes, because the things that go wrong are the things nobody opened. Ideally a screenshot is taken for every block (tab, group, button, menu, context menu, dialog, tooltip). Then a separate, second pass — preferably by a different, stronger model — reviews these screenshots and looks for mistakes: the first pass collects, the second verifies. One watcher is never enough.

Every stage must end not with the word "done", but with a set of artifacts from which another person or another agent can recompute the result. "Done" is a word people say to stop looking.

A bad result:

```text
I checked all the strings and found 20 problems.
```

Why this is bad — and it is bad in a way that will cost you later:

- it is unclear which files were checked;
- it is unclear which languages were in scope;
- it is unclear where the rest of the strings are;
- you cannot tell a full pass from a sample;
- you cannot reproduce the result after an image update.

A good result. This one tells the truth, and tells it in a form you can check at 2 a.m. when you no longer trust your own memory:

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

A good result can be re-verified, and re-verification is the whole point — it is you, refusing to be lied to:

- open the input file by hash and confirm the right version was analyzed;
- recompute the number of strings with another script;
- check that the count in the report matches the count of rows in JSON/CSV;
- pick any `msgid` and find all its occurrences;
- pick any screenshot and match it to a DOM/text dump;
- see which places are not covered. *Especially* the places not covered.

### What cannot count as proof

You cannot accept as proof — no matter how reasonable it sounds, no matter how late it is:

- a general text answer without raw tables;
- screenshots for one language only, if "all languages" was claimed;
- grep output without the list of files and extraction rules;
- a "found everything" report with no total count of found entities;
- a "top missing strings" table when a full table is needed;
- manual conclusions without a machine-readable artifact;
- a translation for which not all occurrences are listed;
- a patch for which it is not stated why this particular source class was chosen;
- a Playwright check without a scenario manifest;
- the absence of errors as proof of completeness — silence is not the same as safety;
- the presence of a string/translation in a catalog (`ui/uno/locore-*.json` or `.mo`) as proof that the translation is actually visible on screen (the opposite is proven: `Clipboard` is in `ui-ru.json` but is rendered in English);
- a render check without cache-bust/hard-reload (the cache trap: assets are cached under an unchanged hash, and an old screen can be mistaken for the result of a fix, in either direction — the cache *remembers* what you tried to make it forget);
- a single cache bust as a guarantee of freshness: some assets (the branding script, runtime `ui-<loc>.json` catalogs) bypass the ordinary cache-bust, so verify the render in a clean browser profile and additionally cross-check with a request that bypasses the cache. One lock is not a lock.

### Minimal set of verifiable artifacts

This is the paper trail. Keep it the way you would keep a record of who came and went.

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

For each stage you need numbers that must add up. When numbers do not add up, something is hiding in the difference. The difference is never empty by accident.

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

If the invariants do not add up, the work is not finished. Even if the agent wrote a coherent report. *Especially* if the agent wrote a coherent report — coherence is cheap, and it is exactly what a thing builds when it wants you to stop checking.

### Stage 1. Fix the baseline

You need to understand what exactly we are localizing. You need to know the ground under your feet before the lights go out, because they will.

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

Record separately how a language code turns into a loaded catalog, because this is one of the quiet ones, the kind of failure that never raises its voice. The chain is: the user picks a language in the app (for example `ru`) -> the app passes the editor a code in the `lang` parameter (in this project the mapping lives in `co_lang`, `ru` -> `ru-RU`) -> the editor normalizes the region and loads a concrete file (`ru-RU` -> `ui-ru.json`). If the code is wrong or carries an extra region, the editor may silently load no catalog or the wrong one — *silently*, that is the word that matters — and then the whole language looks untranslated even though the catalog is sitting right there on disk, complete, waiting, unread. A wrong code sometimes also changes individual strings, for example the language label in the status bar or a raw placeholder like `{ru}` showing through like a bone through skin. This is a common and invisible cause of zero coverage, so the chain must be checked for each language separately. Do not assume the door is open just because you put a door there.

Hand the agent the instruction below exactly as written; the wording is the leash.

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

Control not based on trusting the agent — and you must not trust the agent, not out of cruelty, but because trust is not a method:

- Ask for `baseline_manifest.json`, where each row is a concrete input: path, source, size, hash, extraction date, container or commit.
- Separately recompute the list of languages from the project code and compare with the manifest. If the project has 22 languages, the manifest must have 22 languages, not "the main ones". "The main ones" is where the others go to be forgotten.
- Check that for each language it states which catalogs actually exist: `ui`, `uno`, `locore`, `.mo`. A missing catalog must also be a row in the table, not a silent skip. The silent skip is the enemy. Name the absence.
- Check that the app scope is listed explicitly. If the agent wrote "editor UI", that is not enough: it must be Writer, Calc, Impress, shared, and Draw/out of scope if needed.
- Check that container files are taken from the active image, not from local assumptions. The proof is the extraction command and the hash of the extracted file. What you assume is on the machine and what is actually on the machine are two different machines.
- For each language, check the chain code -> `lang` -> loaded catalog: which catalog file the browser actually requested (visible in the network), not which one was expected. If no catalog is requested for a language, that is the hidden cause of zero coverage, and it has been hiding the whole time.

Signs of partial completion. These are the footprints that lead away from the work undone:

- The agent listed only `ru`, `uk`, `ar`, `zh-CN`, although the task is about all languages.
- The agent did not give hashes of input files.
- The agent did not distinguish `ui`, `uno`, `locore`, `.mo`.
- The agent wrote "LibreOffice resources present" but did not say for which languages.
- The agent did not say which UI scenarios will be checked later.

When you find the footprints, do not ask it to "try harder." Give it the delta, the narrow task it cannot wriggle out of:

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

At this stage the agent reads the code and catalogs, but does not yet prove the render. Keep that distinction sharp. Everything you learn here is a rumor about the screen, not the screen.

You need to collect:

- all direct `_()` strings;
- all `_UNO(...)` commands;
- all frontend i18n strings;
- all strings from `ui-*.json`;
- all strings from `uno/*.json`;
- all strings from `locore/*.json`;
- all available LibreOffice PO/MO/UI resources;
- all places where a string appears in the code.

The key result is the occurrence map. It is the map of every place a name has put down roots — and you want all of them, because the one you miss is the one that grows back.

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

The `render_path` field must not be filled by guessing from which catalog the string lives in. Guessing here feels like knowing, which is exactly why it is dangerous. It is confirmed by experiment: change the string in the assumed source, rebuild the image, bust the browser cache, and see whether the screen changed. Changed — the source is correct; did not change (like `Clipboard`, which lives in `ui-ru.json` but is drawn by the core) — the source is different, and editing this catalog is useless, a key turning in a lock that opens nothing.

When you match a string from the screen to a string from the catalog, you cannot compare them literally. They wear small disguises. Before comparing, both strings must be normalized to one form:

- strip mnemonic markers (`~`, `_`): `~Save` and `Save` are the same string;
- strip a trailing ellipsis (`…` or `...`);
- strip a trailing shortcut hint like `(Ctrl+S)`;
- strip a trailing colon;
- strings with placeholders (`{1}`, `%1`) must be matched as a template via a regular expression, not as exact text.

Without this normalization the same string looks like several different ones — one face in several masks — and you get a pile of false "untranslated" that will eat your week. For core strings in `.mo`, the catalog must first be unpacked into text (`msgunfmt`, needs the gettext package), otherwise there is nothing to compare against; the `.mo` keeps its contents the way a sealed box keeps its contents.

The coverage table from this stage cannot be treated as a fact. Write that on your hand. It is built from the presence of a string in a catalog: if a translation is in the catalog, the string counts as translated. But presence in the catalog does not mean it is the one that draws the text (the same `Clipboard`: it is in `ui-ru.json`, yet the screen shows English because the core draws it). So the percentage from coverage is an upper bound, a hypothesis, a hope with a number on it — not the truth; only the render pass (Stage 3) gives the truth. Required step: take a sample of strings that coverage counts as translated and check them against the real screen — this shows how far the catalog has drifted from the render, and it always drifts.

Hand the agent the instruction below; do not soften it.

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

Control not based on trusting the agent:

- The main artifact is not Markdown, but `occurrences.json` or `occurrences.csv`. Markdown may be a brief report, but does not replace the full table. Prose is where things go to be hidden in plain sight.
- Each occurrence row must have a stable id, e.g. `occ_000123`. Later the patch, collision map, and verification must reference these ids. Without ids, nothing can be held to account.
- For each `msgid` there must be an `occurrence_count` field. If the agent says a string is safe but does not show all occurrences, the conclusion cannot be accepted. "Safe" without the count is a guess in a confident voice.
- The extractor must save raw counts: how many `_()`, how many `_UNO(...)`, how many frontend i18n keys, how many catalog keys were found.
- For each source class there must be a separate count. The sum per source class must explain the total or explicitly show overlap.
- For each `msgid` save not only the file, but enough context: neighboring lines, command id, tab/group/control, if extractable.
- For `unresolved` you cannot just write "unknown". "Unknown" is where the dangerous ones hide. You need a `why_unresolved` field: command map not found, minified dynamic call, generated text, runtime-only, source outside bundle.

Independent checks. Do the arithmetic yourself; do not let it do the arithmetic and grade itself:

- Recompute unique `_()` strings with another command and compare with `direct_key_count`.
- Recompute `_UNO(...)` command ids with another command and compare with `uno_command_count`.
- Pick 20 random occurrence ids and open the source location by hand.
- Pick 20 random `msgid` with occurrence_count greater than 1 and check that all places are listed, not just the first few.
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

Statics shows what *can* be used. But it does not prove that it is actually visible to the user, and the difference between can and is, is the whole difference between what you were told is there and what is actually there, watching from the screen. Now you go and look.

The rendered inventory must go through all target languages and UI states. All of them. The one you skip is the one that is wrong.

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

Important: browser or OS-native menus that the app does not control must be marked out of scope, not translated through Collabora. Know what is yours and what is not. Reaching for what is not yours is how you get nothing back.

Pulling text off the page is harder than reading `textContent`, and the reasons are the kind that ambush you:

- tooltips are visible only on hover — they are caught by a separate hover pass; they are not in the static DOM, they only appear when something approaches them;
- dialogs are drawn not as normal HTML but as a widget tree (JSDialog) — the text is taken from there;
- some dialogs live in nested same-origin iframes — you have to go inside; you have to go in;
- the table grid and the slide are a `<canvas>`, there is no text there at all; such text is outside the DOM and out of scope — it is painted, not written, and you cannot read a painting.

To actually open a surface, clicking programmatically is not enough, and this is where many runs quietly fail while reporting success. The editor's menus and dialogs are drawn by the server and react only to real input events (real Playwright mouse and keyboard), not to events dispatched from JavaScript — a synthetic right-click or hover will not open them; it knocks and nothing answers. On top of that, many dialogs open only from a prepared state: an inserted image, chart, or table, a text cursor placed in the body, a selected cell. If you do not prepare the state, the button opens nothing, and "nothing" photographs exactly like "fine."

The easiest things to miss (check them with a separate list, because memory will tell you that you checked them):

- context menus on the canvas: column header, row header, sheet tab, a shape;
- submenus that have to be expanded as a separate step;
- dialogs available only when there is an active selection.

Two more things — the cache trap and honest accounting of misses. The cache is a thing that remembers. Editor assets are cached for a long time under a name that does not change with our edits, so "old on screen" may be not a missing translation but just the cache, faithfully showing you yesterday and calling it today. And an ordinary cache bust does not fully save you: some files are injected by the server bypassing our cache-bust query (for example the branding script), and `ui-<loc>.json` catalogs are loaded at runtime and also bypass HTML-level busting — they remember too, on their own terms. So the most reliable way to verify the render is a clean browser profile (no old cache) per run, and additionally cross-check the served file with a request that bypasses the cache (`curl` or `fetch(url, {cache: 'reload'})`) — two independent signals, because one signal can be a memory. And separately, honestly record what you could not open (`notReached`): if you did not reach some menu or dialog, write it down explicitly with a reason for each item, and treat the measured coverage percentage as an upper bound, not a fact. The unreached room is still a room.

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

Control not based on trusting the agent:

- Before the run there must be a `scenario_manifest.json`: the list of all `locale x app x state x action` pairs. Write down where you intend to go before you go, so that afterward the list can testify against you.
- After the run there must be a `run_manifest.json`: for each scenario id a status `passed`, `failed`, `skipped`, time, screenshot path, DOM/text dump path.
- You cannot accept "skipped" without a reason. The reason must be machine-readable: missing fixture, feature unavailable, selector timeout, known out of scope. A skip without a reason is a hole someone walked around.
- Each screenshot must have a paired text dump. A screenshot is convenient for a human, but a text dump is needed for automatic diff. The eye tires; the diff does not.
- Each state must have a stable name. For example `calc.formulas.function-library-open`, not `screen5`. "screen5" forgets which room it was.
- For a dropdown and a tooltip the start screen is not enough: you need an action log showing the menu was actually opened — proof that something reached in and the thing opened.
- For RTL languages check separately not only the text, but the direction/layout: `dir`, menu position, overflow. In RTL the whole room is mirrored, and mirrors are where wrongness likes to stand.

Independent checks:

- The number of rows in `run_manifest.json` must equal the number of rows in `scenario_manifest.json`.
- For each row with status `passed` a screenshot and a text dump must exist.
- For each locale there must be the same number of `passed + failed + skipped`.
- If a language did not pass a scenario, it does not disappear from the report: it stays failed/skipped. Nothing is allowed to simply vanish; vanishing is what we are guarding against.
- From the text dumps you can automatically build a list of English leftovers and compare it with the manual report.
- Randomly open several screenshots and confirm they correspond to the right language, not a reused image. A reused image is a lie that holds perfectly still.

Signs of partial completion:

- There are screenshots only for one language or one app.
- There is no list of scenarios before the run.
- There are no failed/skipped scenarios, although real browser runs almost always have at least a timeout or out-of-scope notes. A run with no failures is not a clean run; it is a run that did not look.
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

After the static and rendered inventory you need to understand which strings are safe. Few of them are. "Safe" is a status you earn for a string, not one it is born with.

Risk classes. Read these as a taxonomy of the ways one name can betray you:

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

Control not based on trusting the agent:

- The collision map must cover all `msgid` from the occurrence map. Not only the problematic ones. The ones it calls harmless are the ones it did not look at twice.
- Each collision-map row must reference a list of `occurrence_id`. If there are no ids, the risk class is not proven — it is an opinion in a table.
- For `single-use` there must be exactly one occurrence id. Exactly one. If there are two, "single" was a wish.
- For `same-context multi-use` there must be several occurrence ids and an explanation of why the context is the same.
- For `mixed-context` the different context groups must be listed.
- For `composed-fragment` the fragment pattern must be given: which pieces are joined and where it is visible. Show the seams.
- For `technical-name` state why English may be acceptable: file format, API name, function, brand, common term.

Independent checks:

- Compare set(`msgid`) from `occurrences.json` and set(`msgid`) from `collisions.csv`. The difference must be empty. Whatever lives in that difference, lives there unclassified, in the dark.
- Compare the sum of `occurrence_id` across the collision map with the occurrence map. Every occurrence must be classified.
- Pick all rows with `occurrence_count > 1` and check they did not automatically fall into `single-use`. The automatic answer is the lazy answer, and the lazy answer is where the collisions breed.
- Pick all rows where `neighbor_text` differs and check the agent explained why it is same-context or mixed-context.
- Check that rendered leftovers also got a risk class, not just stayed in the QA report.

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

Translations must be prepared not as free text, but as a controlled table. Free text is how the wrong word slips in wearing the right one's clothes.

For each candidate:

- the English `msgid`;
- the context;
- the source class;
- the current translation per language;
- the proposed translation;
- the proposal source: existing LO translation, current catalog, terminology base, manual translation, AI;
- status: safe, needs human, rejected, accepted;
- notes on grammar, length, RTL.

You cannot ask the agent to "translate everything". "Translate everything" is the door you do not open. You must ask it to "propose candidates, but do not apply them" — keep the proposing and the applying in separate rooms, with the door watched.

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

Control not based on trusting the agent:

- `translation_candidates.csv` must reference `msgid`, `risk_class`, `occurrence_id`, `source_class` and `locale`.
- Each row must have a status. An empty status means the work is not finished. An empty cell is not blank; it is a thing not yet decided, waiting.
- A translation without `reason` and `source` is not accepted. Source can be `existing-locore`, `existing-uno`, `LibreOffice-po`, `glossary`, `human`, `ai-proposed`. A translation with no provenance came from nowhere, and nowhere is not a place you should ship from.
- For `ai-proposed` a lower trust level is needed until a human approves. It is a stranger's suggestion; treat it like one.
- You cannot mix "proposed" and "applied". The candidate table must not change files itself. The list must never be allowed to reach through and act on its own.
- If a translation is long, a layout note is needed: possible overflow, screenshot needed, shortened variant needed.
- For RTL a note is needed: placeholder order, punctuation, directionality.

Independent checks:

- Check that all candidate rows have risk class `single-use` or `same-context multi-use`, if the task was only about safe candidates.
- Check that there are no rows with source class `lo-core-mo` in a batch for `ui-json`. A core string in a client batch is a thing that wandered in from the wrong layer.
- Check that each target locale has a status for each candidate.
- Check that glossary terms are used consistently.
- Pick 20 random translations and check, against the occurrence context, that the translation fits exactly there. Not nearby. There.

Signs of partial completion:

- The agent translated only Russian, although the task is about all target languages.
- The agent filled only missing, but did not mark existing/keep English.
- There is no translation provenance.
- There is no `needs human` status; the agent pretended to be sure of everything. Certainty without doubt is not knowledge; it is the absence of looking.
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

For hard cases the agent must prepare a decision package for a human. The hard cases are the ones that were waiting for you. Do not let them be decided by anything that cannot be held responsible.

The package must contain:

- where the string is visible;
- all occurrences;
- why there is a collision;
- which languages suffer;
- solution options;
- pros and cons of each option;
- what has to change in code or catalogs;
- how to verify.

There can be many options, but it is better to limit them. If there is no simple solution, you can ask for up to 20 options, but with ranking. Twenty doors, and you must know which to open first.

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

Control not based on trusting the agent:

- For each hard case there must be a `decision_id`, so that later the patch references not free text, but an approved decision. A decision with no id can be quietly disowned later, by the agent or by you.
- Each solution option must list affected occurrence ids.
- If an option proposes a split key, it must show the new map: old occurrence ids -> new key ids. Show what becomes of every old thing; nothing is allowed to fall through the gap between old and new.
- If an option proposes a PO/MO/UNO edit, it must show why the browser `ui-json` is not the correct source.
- If an option keeps English, it must explain why this is acceptable: term, brand, technical name, no safe context.
- Each option must have a list of new risks: new collisions, fallback, layout, RTL, migration, rollback. Every fix breeds its own small dangers; name them before they name themselves.

Independent checks:

- Check that all occurrences of the hard case are covered by at least one option.
- Check that the recommended option does not cover only the "easy" part of the occurrences. The easy part is bait.
- Check that split keys do not create technical fallback strings in the English UI.
- Check that each option has a verification plan.
- Check that the human explicitly chose an option before any edits. Before. Always before.

Signs of partial completion:

- The agent proposes one option with no alternatives.
- The agent does not show affected occurrence ids.
- The agent says "better to split the key" but does not show which keys and which places.
- The agent proposes editing `ui-json` for a core/UNO string.
- The agent does not describe rollback. A plan with no way back is not a plan; it is a one-way door.

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

You can edit if — and only if every one of these is true, the way a door is only safe if every lock is thrown:

- the string belongs to `ui-json`;
- it is `single-use` or `same-context multi-use`;
- the translation fits all occurrences equally;
- there are no signs of a composed phrase;
- the translation does not break width/RTL;
- there is a render-check plan.

In this project such edits are best done via the existing patch in `editor/Dockerfile`, rather than manually changing an already-built file in the container. A change made by hand inside a running container is written on water — it dies the moment the container is recreated, and takes your evidence with it. Then the edit is reproducible on rebuild.

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

Control not based on trusting the agent:

- Before the edit there must be an approved list: `approved_ui_json_candidates.csv`.
- The diff must change only allowed files and only allowed keys. Watch the diff the way you would watch hands near your wallet.
- After the build, extract the active `ui-<locale>.json` from the container and check that the key is actually there, not only in the source patch. The patch saying it did the thing and the container actually holding the thing are, once again, two different claims.
- Check that the value did not overwrite an existing newer translation. The thing you write over does not come back.
- Check that the key was not added to a language where it was already translated differently.
- For each added key there must be a rendered scenario or a reason why render is impossible in this batch.

Independent checks:

- Compare set(keys changed in diff) with set(approved candidates). The difference must be empty.
- Compare the active container catalog before/after.
- Check that `same-as-English` did not get wrongly counted as translated, if the translation matches English on purpose.
- Check that the UI does not show technical keys. A technical key bleeding through to the screen is the mask slipping; the user sees the machinery.

If the agent made too wide a patch — and a patch that grows past its scope has a will of its own — pull it back hard:

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

If one `msgid` conflicts in different places, you cannot just add one translation. One name, two meanings — feed it a single translation and you starve one of the meanings.

Possible solutions:

1. Programmatic context (`msgctxt`/`pgettext`) exists only in the core (`.po`/`.mo`). In client catalogs (`ui/uno/locore-*.json`) there is none — they are flat dictionaries "English string -> translation", one value per string, and a flat dictionary cannot tell twins apart. The semantic (de-facto) context of the string exists, but there is no technical context separator on the client. So you can split a homonym on the client only with different keys (editing the call in code), while real `msgctxt` is available only at the core level.
2. If context is not supported, add a context helper that looks up a hidden context key but, for the English fallback, shows a normal English string.
3. If the string is composed, replace the pieces with a whole phrase with placeholders.
4. If the string comes from UNO/core, do not split it in the browser JSON, but fix the UNO/LibreOffice source. Cut at the root, not the leaf.

A bad option — and it is bad because of what the user sees when no translation exists:

```text
_("Line|shape-tool")
```

if, when there is no translation, the user sees `Line|shape-tool`. That is the wiring showing through the wall; the context separator was never meant to be read by a human, and here it is, being read.

Better to have a fallback:

```text
translateContext("shape-tool", "Line")
```

where the English fallback stays `Line`, and the translation can use a context key. The seam stays hidden; the wall stays a wall.

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

Control not based on trusting the agent:

- Before the code edit there must be a `split_plan.csv` table: old msgid, old occurrence ids, new key, new context, fallback.
- After the edit, rebuild the occurrence map and prove the old occurrences disappeared or were distributed over the new keys. Account for every one of the old places; a split that leaves an old place behind has not split anything, it has only made a copy.
- Check the English UI: if there is no translation, the user must see normal English text, not `Line.shapeTool` or `shape-tool|Line`. The user must never meet the machinery.
- Check that the new keys did not collide with existing keys of a different meaning. New collisions are the children of careless splits.
- Check that placeholder order works for languages with a different word order.

Independent checks:

- Compare old occurrence ids from the decision package with new occurrence ids after the edit.
- Check that each new key has exactly the context it was created for.
- Check that the old msgid is no longer used in the conflicting place. If it lingers, it lingers for a reason, and the reason is a bug.
- Run the rendered scenarios for all old places, not just one.

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

If a string belongs to `_UNO(...)` or LibreOffice-core, you have to be especially careful. This is the deep water. The strings down here are shared among more things than you can see from the surface, and changing one can move others you never meant to touch.

The correct path:

- find the source UNO command or LO resource;
- check whether there is PO context;
- edit the PO, not the binary `.mo`, if that is possible;
- build the `.mo` via the gettext toolchain;
- rebuild the image or carefully replace the resource in the image build;
- check that Collabora actually uses the new resource;
- check all commands that could have used the same English text. All of them. The shared string has more siblings than it admits.

Note: `gettext` (`msgfmt`/`msgunfmt`) is usually not in the image — it has to be installed. Do it in the build Dockerfile, not manually in a running container: in a running container everything is lost on recreate, and what is lost here is lost the way footprints are lost at high tide.

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

Control not based on trusting the agent:

- The plan must show the source chain: visible text -> UNO command/dialog -> source catalog -> built artifact -> active container file. Follow it link by link, all the way down and all the way back up. A chain with a missing link is not a chain; it is two pieces of a chain and a guess in between.
- If the agent cannot show the source chain, the edit must not be made. No chain, no cut.
- For `.po`/`.mo` check msgctxt or an equivalent context. If one `msgid` appears in several contexts, you cannot change all of them in one place without analysis. One edit, many silent consequences.
- After the build, check not only the `.mo` file, but the visible UI, because Collabora may take the string from a generated UNO JSON or another cache. The `.mo` can be perfect and the screen can still be wrong, because the screen was reading from somewhere else the whole time.
- Check all commands where the same English text appears in UNO/core, not just one screen.

Independent checks:

- `msgunfmt` or another gettext tool must show the expected `msgid`/`msgstr` in the resulting `.mo`.
- The hash of the resulting `.mo` must differ from the baseline only where expected. If the hash moved where you did not push it, something moved on its own.
- The active container must contain the new `.mo` or the regenerated `uno/*.json`.
- The rendered inventory must confirm the change in the right place.
- The collision map must be updated if the PO context splits the meaning.

If the agent proposed a dubious core patch — and in the deep water, dubious is the default:

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

The agent is useful, but it has to be constrained, the way anything stronger than you and not quite on your side has to be constrained. It does not mean you harm. It just does not know what harm is.

Good rules:

- First read-only analysis, then edits. Look before you touch.
- Any edit must reference a concrete artifact: occurrence map, collision map, approved candidates.
- Do not allow mass import of fresh PO without comparing versions and contexts.
- Do not allow "translate everything" without risk classification.
- Require a report where the numbers add up.
- Require a list of what is not covered.
- Require rendered proof for every changed UI scenario.
- Require a separate list of false positives.
- Require an explanation of why a particular source class is fixed in this particular way.
- Keep edits in small batches. Small batches fail small.

A bad command to the agent — this is the open door, the unguarded yes:

```text
Translate all English strings into Russian.
```

A good command to the agent — this is the door with the chain still on it:

```text
Take only the approved safe candidates from translation_candidates.md.
Apply translations only for source_class=ui-json.
Do not touch strings with risk_class mixed-context, composed-fragment, core-only or unresolved.
After the edit, rebuild the image, check the active l10n files, open Writer/Calc/Impress in ru/uk/ar/zh-CN and attach rendered evidence.
If any step fails, stop and give a report, do not guess.
```

### Strict protocol for working with the agent

So that the agent does not do 30% of the task and present it as a full result — and it will, smoothly, with a straight face — the task must be given as a contract. A contract is a thing you can hold up afterward and say: this is what we agreed.

1. Scope is fixed before the work.
2. The agent must create a manifest.
3. The agent must fill the raw table.
4. The agent must output check counts.
5. The agent must list skipped/failed.
6. The agent must explicitly write what is not covered.
7. A human or an independent check compares counts and artifacts.
8. Only after that is the result considered accepted.

The formula of a good task:

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

The most common signs that the agent did not do a full pass. Learn them like the sounds a house makes when someone else is in it:

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

If you find this, do not ask "check more carefully". That almost always gives another nice summary — another smooth lie in a fresh coat. Give a delta task, narrow and unescapable:

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

A working strategy — and it works because it never asks the agent to judge its own thoroughness; it makes the gap visible and then makes it small:

1. First ask the agent to build the expected set.
   For example: all languages, all apps, all scenarios, all `msgid`.

2. Then ask it to build the actual set.
   For example: what was actually checked, what is actually in the table, which screenshots were saved.

3. Then ask it to build the gap set.
   For example: `expected - actual`. This is the thing it would rather you not see.

4. Then run only the gap set.
   This stops the agent from doing another selective full pass — another lap around the same lit rooms.

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

You can trust not "the agent", but the artifacts. The agent is a voice; the artifacts are evidence. Trust the evidence.

The output can be accepted if:

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

If even one of these is missing, the result must be considered preliminary. One missing lock is an unlocked door.

## How to verify completeness

One screenshot is not enough. One of anything is not enough.

You need several independent cross-checks, because a single check can be fooled, and the thing you are checking against has every reason to fool it:

1. Static extraction: how many strings are found in the code.
2. Catalog coverage: how many strings exist in the catalogs per language.
3. Occurrence map: where each string is used.
4. Rendered inventory: what is actually visible in the browser.
5. Collision map: where one English text has different meanings.
6. Patch coverage: which strings were actually changed.
7. Rendered regression: what changed after the patch.
8. Visual proof: before/after screenshots.
9. False positives: English strings that should stay.

Control questions. Ask them out loud:

- Did all 22 languages go through the same set of scenarios?
- Are there strings visible in the browser but absent from statics?
- Are there strings present in statics but not appearing in the render?
- Do all changed keys have an occurrence map?
- Is there a single translation applied to different meanings?
- Are there composed phrases made of separate words?
- Did RTL languages break?
- Did labels overflow buttons?
- Did technical keys appear instead of the English fallback?
- Did icons/tooltips/menus disappear after the edit? Things that disappear after an edit did not go nowhere; they went somewhere, and you have to find where.

Completeness and quality are different things, and confusing them is its own quiet disaster. All checks above answer "is there a translation and is it visible", but not "is it correct". The numbers adding up (invariants) prove nothing was missed and the result is reproducible, but do not prove the translation is correct — a thing can be present, visible, accounted for, and still wrong, and that wrongness will sit there in front of a native speaker, perfectly counted. Quality is checked by a separate pass of a strong model that knows the target language well, directly over the interface (over the render/screenshots, with context in mind). And the final polish is better done by a native speaker — more precisely, a native subject-matter expert who knows the domain terminology. Someone who would feel the wrongness the way you feel a draft from a door you thought was shut.

### Checks by type of work

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

Suppose the static report claims — and claims are all they are until you make them prove it:

```text
locales = 22
direct_ui_msgid = 436
referenced_uno_labels = 300
global_uno_labels = 813
```

Then independent checks must exist, and you must run them with your own hands:

```text
count(locales_from_project) == 22
count(unique direct _() msgid in selected code segments) == 436
count(unique resolved UNO labels from referenced commands) == 300
count(unique labels in global UNO map) == 813
```

If the agent cannot show how these numbers were recomputed, it is not an audit, it is a retelling. And a retelling is just a story, and a story is the thing you must not believe.

### How to accept partially blocked work

Sometimes a full pass is genuinely impossible: Playwright is busy, a fixture won't open, the source is minified, a `.po` is missing, the command is created dynamically. The wall is real, sometimes. The point is not to pretend it is not there.

This is normal, but the blocked state must be explicit. An unspoken block is just a hole with a rug over it.

For each blocked item you need fields:

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

The phrase "could not verify" without these fields does not count as a report. It counts as a door left open and unmentioned, which is worse than a door left open.

## How to maintain final artifacts

For sustainable maintenance you need not only edits, but documents. The edits fade from memory; the documents are what remembers for you, faithfully, after you have forgotten why.

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

The project already has a static report, and it is sitting there now:

```text
docs/COLLABORA_LOCALIZATION_STATIC_INVENTORY.md
```

It can be considered the first baseline artifact, but not the final proof. A first word, not the last. The next step is an occurrence map with contexts and a rendered inventory.

After a pass there is a coverage report — for example `.qa/l10n/REPORT.md` (how many visible strings, how many translated per language, and the gaps split into "fixable in client JSON" and "core `.mo` only") and a machine-readable matrix `.qa/l10n/visible-coverage.csv` (one row per UI string, with a status per language). This is the verifiable basis for deciding what to fix and with which layer.

## Strategy for working with Collabora sources

The project's goal is to **build Collabora Online from source** (the coolwsd server + the browser bundle), not to patch a ready-made image. The **LibreOffice/Collabora Office core is NOT built from source** — we take it as a pinned prebuilt binary (engine-assets) and patch its strings as data (`.po`→`.mo`). The reason, and it is a reason you arrive at the hard way: deep localization keeps surfacing things that can only be fixed in the Online source — string concatenation in JavaScript, a contextual translation API, client catalogs. You think you are done, and another one surfaces. And everything we change in the UI (texts, sizes, design) lives in the Online layer, not in the core. Here reliability and control matter more than "fast to prod." Fast to prod is how you end up not knowing what you shipped.

The quick path we are moving away from usually looks like this — and it looks so reasonable, that is the trouble with it:

```text
FROM collabora/code:latest
```

and then the Dockerfile patches already-built `bundle.js`, `bundle.css`, `cool.html`, `l10n/ui-*.json`, and image resources with `sed`, `cp`. This is acceptable as a **temporary stopgap** (a small branding tweak, an urgent hotfix), but it is not a base for localization. A stopgap that stays becomes a foundation nobody chose.

Why you cannot live on it long-term:

- `latest` changes without control. Today and tomorrow may be different bytes — the same name pointing at a different thing while you sleep.
- A minified `bundle.js` is a bad place to do contextual string splitting.
- A `sed` patch against built output can break on any upstream change, silently, the next time someone pulls.
- You cannot cleanly add a new contextual localization API.
- It is hard to know which source file produced a string, or to carry a fix across updates.
- It is hard to prove that a patch fixes the correct layer instead of masking the problem. And masking is the thing this whole document is trying to keep you from doing.

So we move in stages, but the endpoint is one — **building Online from pinned source** (the core stays a pinned prebuilt binary).

Pin the version hard. Pin it like a specimen. Translations are made for a **specific** version: the set of strings and their `msgid`/`msgctxt` are version-dependent. Pin **a matching pair**: the Collabora Online commit/tag AND the prebuilt core/engine-assets version (both in `upstream.json`). A version update is a separate, controlled event with acceptance testing of all translations, not a "pull latest." A "pull latest" is how the floor moves under you.

The cost should be named honestly, because the unnamed cost is the one that ambushes the schedule: building **Online** from source is manageable — officially it is `./configure && make` on top of prebuilt engine-assets, from minutes to about half an hour, and it runs locally. Building the **core** from source, however, is heavy (tens of gigabytes, hours); we do not do it — see "When you would build the LO core from source" below. There is a door down there you do not want to open unless you must.

### Stage 1 (temporary): remove nondeterminism of the ready-made image

Until the source build is in place, you cannot stay on `latest` — at least remove the nondeterminism of the ready-made image. Nondeterminism is just another word for a thing that changes when you are not looking.

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

or a concrete tag if a digest cannot be used for some reason.

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

While the image is still prebuilt, changes must not be kept as long `sed` chains. A long `sed` chain is a row of mousetraps in the dark; you will forget where every one of them is set. This is an interim level on the way to building from source.

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

Even if a patch is still applied to a built image, it should be described as a patch unit — given a name, a reason, a place — so it cannot become an anonymous change nobody remembers making:

- what it changes;
- why this is the correct source class;
- which upstream digest it applies to;
- which occurrence ids it closes;
- which rendered scenarios verify it;
- how to roll it back.

This keeps the current repo manageable: the application stays here, and all editor-integration patches have explicit boundaries. Boundaries are what keep a thing from spreading.

### Target level: build from pinned source

This is the project's working base, the firm ground you have been walking toward. From source we build **Collabora Online** (the coolwsd server + the browser bundle) — keep a fork or submodule of the pinned commit, not a copy. A copy forgets where it came from; a fork remembers. The **LibreOffice/Collabora Office core is NOT built from source**: we take it as a pinned prebuilt binary (engine-assets) and patch its `.mo` strings as data (our `.po`). This gives full control over the interface cheaply — everything we change in the UI lives in the Online layer.

What each layer lets you change:

- **Texts** (menus, ribbon, tooltips, dialogs) — all of them: data (client `ui/uno/locore-<lang>.json` + core `.mo` from our `.po`) plus a little Online code to split concatenated phrases and disambiguate homonyms. No core build needed.
- **Element sizes** — CSS (and some JS). No core build.
- **Element design** (colors, shapes, spacing, icons) — CSS + SVG icon replacement (deeper changes — JS). No core build; this is how the glass theme is already done.

The only thing that needs building the core is rendering the document itself on the canvas (the Calc grid, the slide, in-cell text). That is document content, not UI elements (see "When you would build the LO core from source"). Stay out of the core unless the document content itself sends you down there.

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

The key split — translations separate from code. Keep them in separate rooms; a thing that is both data and code is a thing nobody can fully reason about:

- **Translations are DATA.** Our translations live as files: `.po` with `msgctxt` for core strings, and JSON overlays for client strings. During the source build they are deterministically compiled and merged into `.mo` and the catalogs. Such files are easy to review, easy to hand to native speakers, and easy to scale to 30–40 languages.
- **Patches are CODE only** (a new contextual localization API, rewriting concatenated phrases into whole strings with placeholders). Translation data and code patches are not mixed in one change. Mix them and every review becomes two reviews pretending to be one.

Why a fork/submodule is better than a plain copy:

- upstream history is preserved; you can rebase/merge;
- it is clear which files differ from upstream;
- it is easier to check that a fix applies to a new version;
- there is less risk of editing generated output instead of source. Editing generated output is editing the reflection and expecting the face to change.

Where to send things upstream — do not confuse the channel, because a fix sent down the wrong channel is a fix that never arrives:

- **translations go to Weblate** (the LibreOffice/Collabora translation platform), not via GitHub PR;
- **code changes** (context API, concatenation fixes) go as a normal PR to Collabora Online or LibreOffice.

Separately: building from source means you **backport upstream security fixes yourself**. That is one more reason a version update is a controlled event with acceptance, not "pull the latest and ship it." When you own the build, you own the watch; nobody else is staying up to patch your holes.

### Which layer to fix (core or client)

Collabora Online does not own every string. This is the recurring truth, the one that keeps coming back. Part of the interface comes from LibreOffice-core: `.ui`, gettext `.po/.mo`, UNO command metadata, dialogs, sidebar. That is why the LO core is pinned as a prebuilt binary (engine-assets), and its strings are patched as data (`.mo` from our `.po`) — without building the core.

But before every fix you still have to prove which layer the string lives in, otherwise the fix lands in the wrong place (this is the same render-path attribution — the same difference between where you were told the string lives and where it actually lives, watching):

- the string really comes from LO-core, not from a client `ui-json`/`uno-json`;
- there is a concrete PO/UI/source file;
- there is a build path to `.mo` or a generated resource;
- there is a rendered scenario that proves the result on screen.

For client strings, edit our JSON overlays; for core strings, our `.po` with `msgctxt`. The layer is chosen by proof, not by guesswork. Guesswork here is just superstition with a keyboard.

### When you would build the LO core from source

Almost never. Say it to yourself: almost never. Building the core from source is needed only to change **how the document itself is rendered** (how the core draws the Calc grid, the slide, in-cell text) or **core C++ behavior**. That is document content, not UI elements — for texts, sizes, and UI design it is not needed.

This is the heaviest path, the one at the bottom of the stairs: "a few hours even on the fastest computer," the image balloons to ~30 GB; normally only Collabora's own CI does it. Tellingly, even the official "build CODE for Web" does NOT rebuild the core — it drops in prebuilt engine-assets. So a full core build is an optional escalation, not our default. If you find yourself reaching for it, stop and ask what dragged you down here.

### What not to do

Do not — and read this as a list of the ways people have already been hurt:

- copy the whole Collabora source into the app repo without an upstream link;
- keep using `latest`;
- edit minified `bundle.js` as the primary long-term mechanism;
- mass-import fresh PO/JSON without an occurrence/collision map;
- mix app frontend translations, Collabora browser UI, and LibreOffice-core in one patch batch;
- keep translations as code patches instead of data files (`.po`/JSON overlays);
- update the editor version in prod without full acceptance of the translations ("quick hack to prod");
- accept a patch that cannot be tied to a concrete upstream commit or image digest. An untraceable patch is a stranger in the house with no record of how it got in.

### Completeness control for the source strategy

This strategy needs its own artifacts:

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

On a Collabora update you cannot just carry the old patch over. The old patch was written for a world that no longer exists; the strings have moved while you were away.

The same caution applies to third-party translations: Collabora is not stock LibreOffice. Collabora has its own strings and its own notebookbar, so "take a fresh LibreOffice language pack and drop it in" blindly is dangerous: some strings will not match by id or context, and some will overlay incorrectly — wrong words settling silently into the right-looking slots. Any import of third-party translations is checked against version and contexts.

A version update is a controlled event with full acceptance, not carrying over a single patch. Treat it like opening a sealed room: slowly, with the lights on, in the right order:

1. Bring up the new pinned version **in a non-prod environment first**, leaving prod untouched: the new Collabora Online commit + a **matching** prebuilt core/engine-assets version. Do not let it near production until you have looked it in the eye.
2. **Rebuild Online from source** of the new version (the core is taken as a prebuilt binary/engine-assets, not rebuilt).
3. Run **full acceptance, not a smoke test**:
   - rebuild the occurrence map and coverage;
   - run the render ground-truth (a screenshot per object) across **all** target languages;
   - produce a drift-diff of all UI strings against the previous version. The drift-diff is where you see what moved on its own.
4. Triage what the update broke: moved or renamed `msgid`, changed `msgctxt`, new English strings, removed strings, re-introduced phrase concatenation. The phrase concatenation comes back; it always comes back.
5. Re-apply (rebase) our translation data and code patches onto the new version and fix the breakage.
6. **Only after full acceptance passes** — promote to prod. Reliability over speed. The fast promotion is the one you regret.

This acceptance is the gate, and a gate is only a gate if it is shut: the same coverage invariants and render drift-diff run in CI on every version bump and must pass **before** promotion. A screenshot per object plus a second verification pass (see "The proof principle") is the only basis for treating an update as accepted.

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

When there are not 4 but 30-40 languages, it is important not to repeat all the work for each one. Done wrong, the work multiplies by forty and buries you.

The work splits into two levels:

- The surface is captured once. The list of all places where each string appears (the occurrence map) does not depend on the language — it is built once. Map the territory once; it does not change just because you change the language painted over it.
- Coverage per language is computed from data. For a specific language it is enough to check the strings against its catalogs and `.mo` — this is a pure file computation, without a browser, and it scales to any number of languages.

But there is something that cannot be checked from data, and it is exactly the thing that goes wrong where no file can see it: how the translation actually looks on screen — line wrapping, overflowing a button, RTL layout, context collisions. This is visible only in the render, and it must be checked per language. The browser is usually one per instance, so it is the bottleneck — the single narrow door everything has to pass through. The solution is to parallelize: spin up several virtual machines, one language per machine, each with its own editor and browser instance; then the screenshot passes run in parallel. Many eyes, many rooms, all at once.

## Practical rollout order

A realistic order. Take the steps in this order; the order is the safety:

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
15. After each batch, update the maps and the verification report. Always leave the record updated behind you, so the path back is lit.

## Minimal definition of done

A localization batch can be considered finished if — and only if every line below is true; a definition of done with a hole in it is a definition of not-quite-done that lets you go home anyway:

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

An AI agent is a good fit for collecting the map, finding gaps, preparing candidates, and checking regressions. It is a tireless walker of dark corridors, and that is precisely what it is good for. But the agent must not "catch up on all translations" by itself without context. Left alone with that task, it will fill every silence with something confident and wrong.

The correct role of the agent:

- collect the facts;
- show all places of use;
- separate the safe from the dangerous;
- propose options;
- apply only approved targeted edits;
- prove the result by rendering.

The correct role of the human — and this is the part no artifact can do for you, the part that is yours to keep:

- approve terminology;
- decide mixed-context cases;
- choose the architectural option for splitting keys;
- accept the risk of leaving an English term;
- finally accept the visual result;
- check translation quality as a native subject-matter expert, not only its presence. Presence is what the machine can prove. Whether it is *right* — whether it reads true to someone who would know — that judgment stays with you, in the lit room, at the end, where it belongs.
