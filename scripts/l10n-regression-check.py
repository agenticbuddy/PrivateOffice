#!/usr/bin/env python3
"""Localization + layout regression check over a rendered walk.

Compares a fresh deep walk (e2e/scripts/editor-l10n-rendered.mjs) against:
  - a GOLDEN snapshot (a previous rendered/ dir): flags any per-control text change,
  - per-block EXPECTATIONS (expectations.json): asserts terms that SHOULD be translated
    are (and equal the approved RU) and terms that should stay English do,
  - absolute LAYOUT rules on the fresh walk geometry: element overlaps, text
    clipping/overflow, excessive empty space, and viewport-exit / zero-size.

Every deviation is written to a human+AI-readable report (markdown + json), so a person
can eyeball it or ask Claude to investigate a specific spot with Playwright. Intended to
run after translating each block (confirm only the intended change happened, nothing else
broke) and during redesign (confirm everything is present, visible, correctly laid out).

Run:
  python3 scripts/l10n-regression-check.py \
    --candidate .qa/ru-term-inventory/rendered \
    --golden    .qa/ru-term-inventory/rendered-golden \
    --expect    .qa/ru-term-inventory/expectations.json \
    --out       .qa/ru-term-inventory/regression
Golden and expect are optional; with neither, only layout checks run.
"""
import argparse
import collections
import glob
import json
import os
import re

REF = "ru"


def norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def nk(s):
    s = norm(s).replace("~", "").replace("_", "")
    return re.sub(r"[…:]+$|\.\.\.$", "", s).strip()


def looks_english(s):
    return bool(re.search(r"[A-Za-z]{2,}", s)) and not s.startswith("http")


def best(c):
    for f in ("text", "aria", "cooltip", "title"):
        v = (c.get(f) or "").strip()
        if v:
            return v
    return ""


def load_walk(d):
    """scenario_id -> {locale, app, surface, controls:[...], vw, vh}"""
    out = {}
    for p in glob.glob(os.path.join(d, "json", "*.json")):
        try:
            j = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        s = j.get("scenario") or {}
        sid = s.get("scenario_id")
        if not sid:
            continue
        data = j.get("data") or {}
        ha = data.get("htmlAttrs") or {}
        out[sid] = {
            "locale": s.get("locale"), "app": s.get("app"), "surface": s.get("surface"),
            "state": s.get("state"), "path": s.get("path"),
            "controls": data.get("controls") or [], "vw": ha.get("vw"), "vh": ha.get("vh"),
        }
    return out


def rects_overlap(a, b):
    """intersection area of two rects, 0 if none."""
    ix = max(0, min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"]))
    iy = max(0, min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"]))
    return ix * iy


def contains(a, b):
    return a["x"] <= b["x"] + 1 and a["y"] <= b["y"] + 1 and a["x"] + a["w"] >= b["x"] + b["w"] - 1 and a["y"] + a["h"] >= b["y"] + b["h"] - 1


def layout_findings(walk, whitespace=False):
    """Absolute layout checks per scenario (no baseline needed)."""
    findings = []
    for sid, sc in walk.items():
        vw, vh = sc.get("vw") or 100000, sc.get("vh") or 100000
        ctrls = [c for c in sc["controls"] if c.get("rect")]
        # clip / viewport / zero-size
        for c in ctrls:
            r = c["rect"]
            label = best(c) or c.get("id") or c.get("className", "")[:30]
            if r["w"] <= 1 or r["h"] <= 1:
                findings.append((sid, "zero-size", label, f"{r['w']}x{r['h']}", c.get("id")))
            # viewport-exit = element ENTIRELY off the left/top/right edge (strong bug signal).
            # Bottom overflow is excluded: it is normally just scrollable list/dialog content.
            elif r["x"] + r["w"] <= 2 or r["y"] + r["h"] <= 2 or r["x"] >= vw - 1:
                findings.append((sid, "viewport-exit", label, f"@{r['x']},{r['y']} {r['w']}x{r['h']} vw={vw} vh={vh}", c.get("id")))
            # clip = HORIZONTAL overflow on a narrow text control (= label/translation does
            # not fit). Vertical scroll and wide panels are normal containers -> ignored.
            cl = c.get("clip")
            if cl and cl["sw"] > cl["cw"] + 2 and cl["cw"] >= 40 and looks_textual(c) and r["w"] < 600:
                # cw>=40 skips checkbox/radio glyphs whose long label lives in a sibling
                findings.append((sid, "clip", label, f"text {cl['sw']}px > box {cl['cw']}px", c.get("id")))
        # overlaps: clickable leaf controls that partially overlap (not containment)
        clickable = [c for c in ctrls if c.get("clickable") and c["rect"]["w"] > 2 and c["rect"]["h"] > 2]
        if len(clickable) <= 400:
            for i in range(len(clickable)):
                a = clickable[i]["rect"]
                for k in range(i + 1, len(clickable)):
                    b = clickable[k]["rect"]
                    area = rects_overlap(a, b)
                    if area <= 4 or contains(a, b) or contains(b, a):
                        continue
                    # partial overlap of two distinct clickable controls = suspect
                    frac = area / min(a["w"] * a["h"], b["w"] * b["h"])
                    if frac > 0.25:
                        la, lb = best(clickable[i]) or clickable[i].get("id"), best(clickable[k]) or clickable[k].get("id")
                        findings.append((sid, "overlap", f"{la} ⨯ {lb}", f"{int(frac*100)}% of smaller", clickable[i].get("id")))
        # excessive whitespace: a container row with a big horizontal gap between siblings.
        # Heuristic and noisy (normal dialog spacing trips it), so it is a redesign-only
        # opt-in (--whitespace) with a high threshold, off by default.
        if whitespace:
            byrow = collections.defaultdict(list)
            for c in ctrls:
                r = c["rect"]
                byrow[(c.get("path"), r["y"] // 8)].append(r)
            for key, rs in byrow.items():
                if len(rs) < 2:
                    continue
                rs.sort(key=lambda r: r["x"])
                for j in range(1, len(rs)):
                    gap = rs[j]["x"] - (rs[j - 1]["x"] + rs[j - 1]["w"])
                    if gap > 320:
                        findings.append((sid, "whitespace", str(key[0])[:40], f"gap {gap}px", None))
                        break
    return findings


def looks_textual(c):
    return bool(best(c)) and looks_english(best(c) or "") or bool(re.search(r"[А-Яа-я]", best(c) or ""))


def text_diff(golden, candidate):
    """Per (scenario, control_id) rendered-text changes vs the golden snapshot."""
    diffs = []
    for sid, cand in candidate.items():
        g = golden.get(sid)
        if not g:
            continue
        gmap = {c["id"]: best(c) for c in g["controls"] if c.get("id")}
        for c in cand["controls"]:
            cid = c.get("id")
            if not cid or cid not in gmap:
                continue
            before, after = norm(gmap[cid]), norm(best(c))
            if before != after and (before or after):
                diffs.append((sid, cid, before, after))
    return diffs


def check_expectations(candidate, expect):
    """expectations.json: {"terms":[{"en","expect":"translate|keep-english","ru":"...","scope":"..."}]}
    Assert each expected term renders accordingly somewhere in the candidate walk."""
    if not expect:
        return []
    # index candidate english->rendered (ru locale only) via id-join is overkill here;
    # use a flat en->set(rendered) map from ru scenarios joined to en by control id.
    en_by_sid_id, ru_by_sid_id = {}, {}
    for sid, sc in candidate.items():
        base = re.sub(r"^(en|ru)__", "", sid)
        tgt = en_by_sid_id if sc["locale"] == "en" else ru_by_sid_id if sc["locale"] == REF else None
        if tgt is None:
            continue
        for c in sc["controls"]:
            if c.get("id"):
                tgt.setdefault(base, {})[c["id"]] = best(c)
    en2ru = collections.defaultdict(set)
    for base, enmap in en_by_sid_id.items():
        rumap = ru_by_sid_id.get(base, {})
        for cid, en in enmap.items():
            if cid in rumap and en:
                en2ru[norm(en)].add(norm(rumap[cid]))
    fails = []
    for t in (expect.get("terms") or []):
        en = norm(t.get("en"))
        rendered = en2ru.get(en) or set()
        if not rendered:
            fails.append((en, t.get("expect"), "not-seen", ""))
            continue
        if t.get("expect") == "translate":
            want = norm(t.get("ru") or "")
            ok = any(nk(r) != nk(en) and (not want or nk(r) == nk(want)) for r in rendered)
            if not ok:
                fails.append((en, "translate", f"want={want or 'any RU'}", " | ".join(sorted(rendered))))
        elif t.get("expect") == "keep-english":
            if any(nk(r) != nk(en) for r in rendered):
                fails.append((en, "keep-english", "got translation", " | ".join(sorted(rendered))))
    return fails


def main():
    ap = argparse.ArgumentParser()
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--candidate", default=os.path.join(root, ".qa/ru-term-inventory/rendered"))
    ap.add_argument("--golden", default="")
    ap.add_argument("--expect", default="")
    ap.add_argument("--out", default=os.path.join(root, ".qa/ru-term-inventory/regression"))
    ap.add_argument("--whitespace", action="store_true", help="also flag large empty gaps (redesign aid, noisy)")
    args = ap.parse_args()

    candidate = load_walk(args.candidate)
    golden = load_walk(args.golden) if args.golden and os.path.isdir(args.golden) else {}
    expect = json.load(open(args.expect, encoding="utf-8")) if args.expect and os.path.exists(args.expect) else {}

    layout = layout_findings(candidate, whitespace=args.whitespace)
    diffs = text_diff(golden, candidate) if golden else []
    exp_fails = check_expectations(candidate, expect) if expect else []

    by_kind = collections.Counter(f[1] for f in layout)
    report = {
        "candidate": args.candidate, "golden": args.golden or None, "expect": args.expect or None,
        "scenarios": len(candidate),
        "summary": {
            "layout_findings": len(layout), "by_kind": dict(by_kind),
            "text_changes_vs_golden": len(diffs), "expectation_failures": len(exp_fails),
        },
        "layout": [{"scenario": s, "kind": k, "what": w, "detail": d, "id": i} for (s, k, w, d, i) in layout],
        "text_changes": [{"scenario": s, "id": i, "before": b, "after": a} for (s, i, b, a) in diffs],
        "expectation_failures": [{"en": e, "expect": x, "why": y, "rendered": r} for (e, x, y, r) in exp_fails],
    }
    os.makedirs(args.out, exist_ok=True)
    json.dump(report, open(os.path.join(args.out, "report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    write_md(os.path.join(args.out, "report.md"), report)

    total = len(layout) + len(diffs) + len(exp_fails)
    print(f"wrote {args.out}/report.md  (+ report.json)")
    print(f"  scenarios checked: {len(candidate)}")
    print(f"  layout findings: {len(layout)} {dict(by_kind)}")
    print(f"  text changes vs golden: {len(diffs)}   expectation failures: {len(exp_fails)}")
    print(f"  TOTAL deviations: {total}")
    return total


def write_md(path, r):
    L = ["# Localization + layout regression report", ""]
    s = r["summary"]
    L += [
        f"- candidate: `{r['candidate']}`  ·  golden: `{r['golden']}`  ·  expectations: `{r['expect']}`",
        f"- scenarios checked: **{r['scenarios']}**",
        f"- layout findings: **{s['layout_findings']}** {s['by_kind']}",
        f"- text changes vs golden: **{s['text_changes_vs_golden']}**  ·  expectation failures: **{s['expectation_failures']}**",
        "",
    ]
    if r["expectation_failures"]:
        L += ["## Expectation failures (block not translated as predicted)", ""]
        for f in r["expectation_failures"][:200]:
            L.append(f"- `{f['en']}` expected **{f['expect']}** — {f['why']} — rendered: {f['rendered']}")
        L.append("")
    if r["text_changes"]:
        L += ["## Text changes vs golden (did anything beyond the block change?)", ""]
        for d in r["text_changes"][:300]:
            L.append(f"- `{d['scenario']}` `#{d['id']}`: `{d['before']}` → `{d['after']}`")
        L.append("")
    if r["layout"]:
        L += ["## Layout findings", ""]
        order = ["overlap", "clip", "viewport-exit", "zero-size", "whitespace"]
        bykind = collections.defaultdict(list)
        for f in r["layout"]:
            bykind[f["kind"]].append(f)
        for k in order:
            items = bykind.get(k) or []
            if not items:
                continue
            L.append(f"### {k} ({len(items)})")
            for f in items[:120]:
                L.append(f"- `{f['scenario']}`: {f['what']} — {f['detail']}")
            L.append("")
    if not (r["expectation_failures"] or r["text_changes"] or r["layout"]):
        L.append("_No deviations._")
    open(path, "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
