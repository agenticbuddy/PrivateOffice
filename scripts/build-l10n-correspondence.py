#!/usr/bin/env python3
"""Build ONE localization correspondence table from the rendered inventory.

For every English UI term seen in the rendered browser walk, record:
  - where it appears (contexts = app/state),
  - its source class (from .qa/l10n/visible-coverage.csv, if known),
  - the CURRENT on-screen value in every captured language.

Values are aligned across locales by control `id` in the per-scenario DOM dumps
(.qa/l10n-rendered/json/<locale>__<app>__<state>.json -> data.controls[]). The rendered value
is ground truth (what the user actually sees), not just the catalog. If one English term renders
as >1 distinct translation in a language (different contexts), that is flagged `mixed_context`.

Output: .qa/l10n/correspondence.json  (regenerable; .qa is gitignored).
Run: python3 scripts/build-l10n-correspondence.py
"""
import json, csv, os, glob, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_DIR = os.path.join(ROOT, ".qa/l10n-rendered/json")
COVERAGE = os.path.join(ROOT, ".qa/l10n/visible-coverage.csv")
OUT = os.path.join(ROOT, ".qa/l10n/correspondence.json")


def best_text(c):
    return (c.get("text") or c.get("aria") or c.get("title") or "").strip()


# 1. index every scenario dump: (app,state) -> locale -> {control_id: text}
scenarios = collections.defaultdict(dict)
locales = set()
files = glob.glob(os.path.join(JSON_DIR, "*.json"))
for path in files:
    parts = os.path.basename(path)[:-5].split("__")
    if len(parts) != 3:
        continue
    locale, app, state = parts
    try:
        ctrls = (json.load(open(path)).get("data") or {}).get("controls") or []
    except Exception:
        continue
    idmap = {}
    for c in ctrls:
        i, t = c.get("id"), best_text(c)
        if i and t:
            idmap.setdefault(i, t)
    scenarios[(app, state)][locale] = idmap
    locales.add(locale)

langs = sorted(l for l in locales if l != "en")

# 2. source class per English string (from the coverage matrix)
source = {}
if os.path.exists(COVERAGE):
    for row in csv.DictReader(open(COVERAGE)):
        source[row["string"]] = row.get("source")

# 3. aggregate: english term -> contexts + per-lang value counters
terms = {}
for (app, state), byloc in scenarios.items():
    en = byloc.get("en")
    if not en:
        continue
    ctx = f"{app}/{state}"
    for cid, en_text in en.items():
        rec = terms.setdefault(en_text, {"contexts": set(), "lang": collections.defaultdict(collections.Counter), "occ": 0})
        rec["contexts"].add(ctx)
        rec["occ"] += 1
        for lang in langs:
            lt = byloc.get(lang, {}).get(cid)
            if lt is not None:
                rec["lang"][lang][lt] += 1

# 4. emit one JSON
out = []
for en_text, rec in sorted(terms.items()):
    langs_out = {}
    mixed = False
    for lang in langs:
        ctr = rec["lang"].get(lang)
        if not ctr:
            continue
        variants = [v for v, _ in ctr.most_common()]
        val = variants[0]
        entry = {"value": val, "translated": bool(val) and val != en_text}
        if len(variants) > 1:
            entry["variants"] = variants
            mixed = True
        langs_out[lang] = entry
    out.append({
        "en": en_text,
        "source": source.get(en_text),
        "occurrences": rec["occ"],
        "contexts": sorted(rec["contexts"]),
        "mixed_context": mixed,
        "langs": langs_out,
    })

os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump({"meta": {"terms": len(out), "langs": langs, "scenario_files": len(files)}, "terms": out},
          open(OUT, "w"), ensure_ascii=False, indent=1)

# stats
fully = sum(1 for t in out if t["langs"] and all(e["translated"] for e in t["langs"].values()))
mixed = sum(1 for t in out if t["mixed_context"])
print(f"wrote {OUT}")
print(f"  english terms: {len(out)}  x  langs: {len(langs)} ({','.join(langs)})")
print(f"  fully translated in ALL captured langs: {fully}/{len(out)}")
print(f"  mixed-context (>1 translation in some lang): {mixed}")
