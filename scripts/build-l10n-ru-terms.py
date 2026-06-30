#!/usr/bin/env python3
"""Reconcile the deep rendered walk with the catalog universe into ONE RU term map.

Joins, per (app, state) scenario, the English baseline dump against the Russian
dump (by control id, then by position) to learn, for every English term:
  - its CURRENT Russian rendering (ground truth, what the user sees),
  - WHERE and under WHAT CIRCUMSTANCES it appears (app, surface, path, precondition),
  - its catalog value + source_class (from scripts/build-l10n-catalog.py),
  - a classification: simple | complex | composite (Этап 4 risk classes).

simple    = one place, one rendering, matches catalog, no mismatch, not a fragment.
complex   = homograph (>1 distinct RU on screen) / render-path mismatch (catalog
            translated but English on screen) / >1 distinct catalog value.
composite = glued at runtime (leading/trailing-space msgid or known concat) -
            must be rewritten as a whole phrase, never translated in place.

Output: .qa/l10n/ru-terms.json (regenerable; .qa is gitignored).
Run: python3 scripts/build-l10n-ru-terms.py
"""
import argparse
import collections
import glob
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SHORTCUT = re.compile(r"\s*\((?:Ctrl|Alt|Shift|⌘|⌥|⇧|⌃)[^)]*\)\s*$")
TEMPLATE = re.compile(r"\{\d+\}|%\d*\$?[sdifolu]|%[sdifolu]")


def looks_english(s):
    return bool(re.search(r"[A-Za-z]{2,}", s)) and not s.startswith("http")


def norm_key(s):
    """Normalize a label for catalog matching: drop accelerator marks, a trailing
    shortcut hint, trailing ellipsis/colon, and collapse whitespace."""
    s = (s or "").replace("~", "").replace("_", "")
    s = SHORTCUT.sub("", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"[…:]+$", "", s).strip()  # trailing … or :
    s = re.sub(r"\.\.\.$", "", s).strip()
    return s


def best(c):
    """Pick the most representative text of a control + which field it came from."""
    for field in ("text", "aria", "cooltip", "title"):
        v = (c.get(field) or "").strip()
        if v:
            return v, field
    return "", None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rendered", default=os.path.join(ROOT, ".qa/ru-term-inventory/rendered/json"))
    ap.add_argument("--catalog", default=os.path.join(ROOT, ".qa/ru-term-inventory/ru-catalog.json"))
    ap.add_argument("--ref", default="ru", help="reference language")
    ap.add_argument("--out", default=os.path.join(ROOT, ".qa/ru-term-inventory/ru-terms.json"))
    args = ap.parse_args()
    ref = args.ref

    # --- catalog universe: normalized english -> list of {ru, source_class, ...} ---
    cat = json.load(open(args.catalog, encoding="utf-8"))
    cat_index = collections.defaultdict(list)
    for e in cat["entries"]:
        cat_index[norm_key(e["en"])].append({
            "ru": e.get(ref), "source_class": e["source_class"],
            "module": e.get("module"), "msgctxt": e.get("msgctxt"),
        })

    # Character-map surfaces (Special Character dialog + the charmap ribbon button) list
    # ~5000 Unicode glyph names - not localizable UI, pure noise. Exclude them.
    exclude = re.compile(r"insertsymbol|charmap|insert-char", re.I)

    # --- load rendered dumps: (app,state) -> locale -> controls + scenario meta ---
    scenarios = collections.defaultdict(dict)
    for path in glob.glob(os.path.join(args.rendered, "*.json")):
        try:
            d = json.load(open(path, encoding="utf-8"))
        except Exception:
            continue
        s = d.get("scenario") or {}
        loc, app, state = s.get("locale"), s.get("app"), s.get("state")
        if not (loc and app and state):
            continue
        if exclude.search(state):
            continue
        scenarios[(app, state)][loc] = {"controls": (d.get("data") or {}).get("controls") or [], "meta": s}

    # --- join en vs ref per scenario; aggregate by english term ---
    terms = {}

    def occ(en, ru_val, field, meta, cid):
        rec = terms.setdefault(en, {
            "ru_rendered": collections.Counter(),
            "occurrences": [], "surfaces": set(), "apps": set(), "paths": set(), "fields": set(),
        })
        if ru_val:
            rec["ru_rendered"][ru_val] += 1
        rec["surfaces"].add(meta.get("surface") or "")
        rec["apps"].add(meta.get("app") or "")
        rec["paths"].add(meta.get("path") or "")
        rec["fields"].add(field or "")
        rec["occurrences"].append({
            "app": meta.get("app"), "surface": meta.get("surface"),
            "path": meta.get("path"), "precondition": meta.get("precondition"),
            "scenario_id": meta.get("scenario_id"), "state": meta.get("state"),
            "control_id": cid, "field": field, "ru": ru_val,
        })

    for (app, state), byloc in scenarios.items():
        en_dump = byloc.get("en")
        ref_dump = byloc.get(ref)
        if not en_dump:
            continue
        en_ctrls = en_dump["controls"]
        ref_ctrls = ref_dump["controls"] if ref_dump else []
        ref_by_id = {}
        for c in ref_ctrls:
            if c.get("id"):
                ref_by_id.setdefault(c["id"], best(c)[0])
        positional = ref_dump and len(en_ctrls) == len(ref_ctrls)
        meta = en_dump["meta"]
        for i, c in enumerate(en_ctrls):
            en_text, field = best(c)
            if not en_text or not looks_english(en_text):
                continue
            cid = c.get("id") or ""
            ru_val = None
            if cid and cid in ref_by_id:
                ru_val = ref_by_id[cid]
            elif positional:
                ru_val = best(ref_ctrls[i])[0]
            occ(en_text, ru_val, field, meta, cid)

    # --- classify + reconcile with catalog ---
    out = []
    for en, rec in sorted(terms.items()):
        nk = norm_key(en)
        cat_hits = cat_index.get(nk, [])
        cat_ru = [h["ru"] for h in cat_hits if h.get("ru")]
        cat_ru_distinct = sorted(set(cat_ru))
        source_classes = sorted(set(h["source_class"] for h in cat_hits))
        ru_variants = [v for v, _ in rec["ru_rendered"].most_common()]
        # render-path mismatch: catalog has a real translation but screen shows English
        catalog_translated = any(r and r != en and norm_key(r) != nk for r in cat_ru)
        # screen shows the English term verbatim (a leftover) although the catalog has RU.
        # Require a REAL ru rendering equal to english - absence of ru data is "unknown",
        # not a mismatch (else every en-only/notReached term is a false positive).
        rendered_as_english = bool(ru_variants) and any(norm_key(v) == nk for v in ru_variants)
        render_mismatch = catalog_translated and rendered_as_english

        is_fragment = en != en.strip()
        is_template = bool(TEMPLATE.search(en))
        if is_fragment:
            cls, reason = "composite", "space-fragment"
        elif is_template:
            cls, reason = "composite", "template"
        elif len(ru_variants) > 1:
            cls, reason = "complex", "mixed-render"
        elif render_mismatch:
            cls, reason = "complex", "render-path-mismatch"
        elif len(cat_ru_distinct) > 1:
            cls, reason = "complex", "catalog-homograph"
        elif len(source_classes) > 1:
            cls, reason = "complex", "multi-source"
        else:
            cls, reason = "simple", None

        # distinct on-screen locations (app + surface + path)
        loc_keys = set((o["app"], o["surface"], o["path"]) for o in rec["occurrences"])

        term_id = f"term_{len(out) + 1:05d}"
        out.append({
            "term_id": term_id,
            "en": en,
            "ru_rendered": ru_variants[0] if ru_variants else None,
            "ru_rendered_variants": ru_variants if len(ru_variants) > 1 else None,
            "ru_catalog": cat_ru_distinct[0] if cat_ru_distinct else None,
            "ru_catalog_variants": cat_ru_distinct if len(cat_ru_distinct) > 1 else None,
            "source_class": source_classes[0] if len(source_classes) == 1 else (source_classes or None),
            "classification": cls,
            "reason": reason,
            "render_mismatch": render_mismatch,
            "is_template": is_template,
            "occurrence_count": len(rec["occurrences"]),
            "location_count": len(loc_keys),
            "apps": sorted(x for x in rec["apps"] if x),
            "surfaces": sorted(x for x in rec["surfaces"] if x),
            "contexts": sorted(x for x in rec["paths"] if x)[:12],
            "occurrences": rec["occurrences"][:40],
        })

    # --- catalog-side composites ---
    # Runtime-glued client fragments (leading/trailing space in the msgid) never surface
    # as standalone rendered terms - the screen shows the glued result. Surface them from
    # the catalog so they are not missed; each must be rewritten as a whole phrase.
    rendered_keys = {norm_key(t["en"]) for t in out}
    for e in cat["entries"]:
        if not (e["source_class"] or "").startswith("client"):
            continue
        en = e["en"]
        if en == en.strip() or norm_key(en) in rendered_keys:
            continue
        out.append({
            "term_id": f"term_{len(out) + 1:05d}",
            "en": en,
            "ru_rendered": None, "ru_rendered_variants": None,
            "ru_catalog": e.get(ref), "ru_catalog_variants": None,
            "source_class": e["source_class"],
            "classification": "composite", "reason": "space-fragment",
            "render_mismatch": False, "is_template": bool(TEMPLATE.search(en)),
            "occurrence_count": 0, "location_count": 0,
            "apps": [], "surfaces": [], "contexts": [], "occurrences": [],
        })

    # --- stats ---
    by_cls = collections.Counter(t["classification"] for t in out)
    need_work = [t for t in out if (t["render_mismatch"] or t["classification"] == "composite"
                                    or not t["ru_rendered"] or norm_key(t["ru_rendered"] or "") == norm_key(t["en"]))]
    out_dir = os.path.dirname(args.out)
    os.makedirs(out_dir, exist_ok=True)
    payload = {
        "meta": {
            "ref": ref, "rendered_terms": len(out),
            "by_classification": dict(by_cls),
            "needs_attention": len(need_work),
            "scenarios": len(scenarios),
            "catalog_entries": cat["meta"]["entries"],
        },
        "terms": out,
    }
    json.dump(payload, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    write_csv(os.path.join(out_dir, "terms.csv"), term_rows(out))
    write_csv(os.path.join(out_dir, "occurrences.csv"), occurrence_rows(out))
    write_csv(os.path.join(out_dir, "collisions.csv"), term_rows([t for t in out if t["classification"] == "complex"]))
    write_csv(os.path.join(out_dir, "composites.csv"), term_rows([t for t in out if t["classification"] == "composite"]))
    write_csv(os.path.join(out_dir, "unresolved.csv"), term_rows([t for t in out if not t.get("source_class") or t.get("render_mismatch")]))

    print(f"wrote {args.out}")
    print(f"  csv dir: {out_dir}")
    print(f"  scenarios joined: {len(scenarios)}   rendered english terms: {len(out)}")
    print(f"  by classification: {dict(by_cls)}")
    print(f"  needs attention (mismatch/composite/leftover): {len(need_work)}")


def term_rows(terms):
    rows = []
    for t in terms:
        rows.append({
            "term_id": t["term_id"],
            "text_en": t["en"],
            "ru_rendered": t.get("ru_rendered") or "",
            "ru_catalog": t.get("ru_catalog") or "",
            "source_class": scalar(t.get("source_class")),
            "classification": t["classification"],
            "reason": t.get("reason") or "",
            "render_mismatch": str(bool(t.get("render_mismatch"))).lower(),
            "is_template": str(bool(t.get("is_template"))).lower(),
            "occurrence_count": t["occurrence_count"],
            "location_count": t["location_count"],
            "apps": "|".join(t.get("apps") or []),
            "surfaces": "|".join(t.get("surfaces") or []),
            "contexts": "|".join(t.get("contexts") or []),
        })
    return rows


def occurrence_rows(terms):
    rows = []
    for t in terms:
        for i, o in enumerate(t["occurrences"], 1):
            rows.append({
                "term_id": t["term_id"],
                "text_en": t["en"],
                "ru": o.get("ru") or "",
                "occurrence_index": i,
                "app": o.get("app") or "",
                "surface": o.get("surface") or "",
                "path": o.get("path") or "",
                "precondition": o.get("precondition") or "",
                "scenario_id": o.get("scenario_id") or "",
                "state": o.get("state") or "",
                "control_id": o.get("control_id") or "",
                "field": o.get("field") or "",
                "classification": t["classification"],
                "reason": t.get("reason") or "",
                "source_class": scalar(t.get("source_class")),
            })
    return rows


def write_csv(path, rows):
    headers = list(rows[0].keys()) if rows else ["term_id", "text_en"]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(",".join(headers) + "\n")
        for row in rows:
            fh.write(",".join(csv_cell(row.get(h, "")) for h in headers) + "\n")


def csv_cell(value):
    text = str(value)
    if any(ch in text for ch in [",", '"', "\n"]):
        return '"' + text.replace('"', '""') + '"'
    return text


def scalar(value):
    if isinstance(value, list):
        return "|".join(value)
    return value or ""


if __name__ == "__main__":
    main()
