#!/usr/bin/env python3
"""Compare two rendered-walk runs for coverage parity.

The deep walk is mildly non-deterministic (a dialog/menu may open in one run and be
notReached in another). To confirm a run did not silently lose surface, diff two
`rendered/json` dirs by:
  - scenario_id set (what each run reached),
  - distinct visible English term set (from the en dumps),
  - dialog titles per run (catches the stuck-dialog contamination: many dialog
    scenarios collapsing to one repeated title).

Run: python3 scripts/compare-l10n-runs.py <runA/json> <runB/json>
"""
import collections
import glob
import json
import os
import re
import sys


def looks_english(s):
    return bool(re.search(r"[A-Za-z]{2,}", s)) and not s.startswith("http")


def best(c):
    for f in ("text", "aria", "cooltip", "title"):
        v = (c.get(f) or "").strip()
        if v:
            return v
    return ""


def load(run_dir):
    scenarios, en_terms, dialog_titles = set(), set(), collections.Counter()
    for path in glob.glob(os.path.join(run_dir, "*.json")):
        try:
            d = json.load(open(path, encoding="utf-8"))
        except Exception:
            continue
        s = d.get("scenario") or {}
        sid = s.get("scenario_id") or os.path.basename(path)[:-5]
        scenarios.add(re.sub(r"^(en|ru)__", "", sid))  # locale-independent key
        ctrls = (d.get("data") or {}).get("controls") or []
        if s.get("locale") == "en":
            for c in ctrls:
                t = best(c)
                if t and looks_english(t):
                    en_terms.add(t)
        if s.get("surface") == "dialog" and (d.get("lines") or []):
            dialog_titles[d["lines"][0]] += 1
    return scenarios, en_terms, dialog_titles


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: compare-l10n-runs.py <runA/json> <runB/json>")
    a_dir, b_dir = sys.argv[1], sys.argv[2]
    sa, ea, da = load(a_dir)
    sb, eb, db = load(b_dir)

    def section(name, A, B):
        only_a, only_b = sorted(A - B), sorted(B - A)
        print(f"\n== {name} ==")
        print(f"  A={len(A)}  B={len(B)}  common={len(A & B)}")
        print(f"  only in A ({len(only_a)}): {only_a[:25]}")
        print(f"  only in B ({len(only_b)}): {only_b[:25]}")

    print(f"A = {a_dir}")
    print(f"B = {b_dir}")
    section("scenarios (locale-independent)", sa, sb)
    section("distinct english terms (en dumps)", ea, eb)
    print("\n== dialog titles (repeats >2 ⇒ stuck-dialog contamination) ==")
    print(f"  A distinct titles={len(da)}: {da.most_common(8)}")
    print(f"  B distinct titles={len(db)}: {db.most_common(8)}")


if __name__ == "__main__":
    main()
