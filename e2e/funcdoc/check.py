#!/usr/bin/env python3
"""Verify a 3-sheet functions-check workbook AS A TEST: exit non-zero on any regression.

Fails (exit 1) if, for a formula the smoke was SUPPOSED to insert (the PLAN, subset-aware — not merely the
ones that happened to fill, so "failed on every sheet" is caught):
  • MISSING   — some sheet did not fill it (dropped insertion / seed),
  • DIVERGE   — sheets disagree: ok on one & error on another, OR all ok but the computed VALUE differs
                (⇒ a method inserted a different formula — a silent build artifact, not a core bug),
  • UNEXPECTED— it errors on ALL sheets but is not in ALLOWLIST (a genuinely new failure).
Errors that are identical across all sheets AND allowlisted (inherently non-computable) are OK; value
comparison is skipped for VOLATILE functions (time/random) whose value legitimately differs per sheet.
Usage: check.py <node_id>   →  prints a PASS/FAIL report, exits 0 (pass) or 1 (fail).
"""
import sys, os, json, subprocess, zipfile
from xml.etree import ElementTree as ET

# Inherently non-computable in a static, offline, single-cell sheet — expected to error identically
# on all three sheets (by-design #N/A, external, dynamic-array, exotic add-ins, strict signatures).
ALLOWLIST = {
    "НД", "ТЕКУЩ", "ТИП.ОШИБКИ", "ТИПОШИБКИ",                       # by-design #N/A
    "ВЕБСЛУЖБА", "DDE", "ДСВТ",                                     # external / pivot
    "ФИЛЬТР", "СОРТПО", "LET",                                      # dynamic array / name-scope
    "ФУРЬЕ",                                                        # complex-array transform
    "ПРЕДСКАЗ.ETS.ADD", "ПРЕДСКАЗ.ETS.MULT", "ПРЕДСКАЗ.ETS.PI.ADD",
    "ПРЕДСКАЗ.ETS.PI.MULT", "ПРЕДСКАЗ.ETS.STAT.ADD", "ПРЕДСКАЗ.ETS.STAT.MULT",
    "ПРЕДСКАЗ.ETS.СЕЗОННОСТЬ",                                      # time-series (need a timeline)
    "OPT_BARRIER", "OPT_PROB_HIT", "OPT_PROB_INMONEY", "OPT_TOUCH", # option-pricing add-ins
    "ЦЕНАПЕРВНЕРЕГ", "ДОХОДПЕРВНЕРЕГ",                              # odd-first-coupon bonds
    "Б", "CONVERT_OOO", "ВЕРОЯТНОСТЬ", "ДСТОТКЛ", "ДДИСП",          # strict-signature (see WAL)
}

NODE = sys.argv[1]
subprocess.run(["curl", "-s", "-u", "admin:123",
                f"http://localhost:8088/admin/api/nodes/{NODE}/download", "-o", "/tmp/smoke.xlsx"], check=True)
info = json.load(open("/tmp/funcdoc.json", encoding="utf-8"))["info"]  # f_cell -> {name, formula}
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
RNS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
z = zipfile.ZipFile("/tmp/smoke.xlsx")
rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
name2file = {s.get("name"): ("xl/" + rels[s.get(RNS + "id")].lstrip("/"))
             for s in ET.fromstring(z.read("xl/workbook.xml")).iter(NS + "sheet")}

# Only the three method sheets are under test — ignore any stray sheet (e.g. a leftover "Лист4") so it
# can't spuriously mark every formula MISSING; fail if a method sheet is absent.
METHOD_SHEETS = ["Через меню", "Через мастер", "Прямой ввод"]
missing_sheets = [s for s in METHOD_SHEETS if s not in name2file]
if missing_sheets:
    print(f"FAIL — method sheet(s) absent: {missing_sheets} (found {list(name2file)})")
    sys.exit(1)

# per-sheet state ("ok"|"err"|"empty") + cached VALUE for every formula cell
sheets = [s for s in name2file if s in METHOD_SHEETS]
state = {name: {} for name in sheets}
value = {name: {} for name in sheets}
for name in sheets:
    part = name2file[name]
    cells = {}
    for c in ET.fromstring(z.read(part)).iter(NS + "c"):
        v = c.find(NS + "v")
        cells[c.get("r")] = {"t": c.get("t"), "v": (v.text if v is not None else None)}
    for ref in info:
        c = cells.get(ref)
        if c is None or c["v"] is None:
            state[name][ref], value[name][ref] = "empty", None
        elif c["t"] == "e":
            state[name][ref], value[name][ref] = "err", None
        else:
            state[name][ref], value[name][ref] = "ok", c["v"]

filled = {name: sum(1 for ref in info if state[name][ref] != "empty") for name in sheets}
# EXPECTED = the cells the smoke ATTEMPTED (the PLAN, subset-aware) — NOT "filled on ≥1 sheet". Otherwise a
# formula that failed to insert on EVERY sheet is silently dropped and the test passes green (reviewer bug 1).
SUBSET = int(os.environ.get("SUBSET", "0"))
plan = json.load(open("/tmp/funcdoc-ui-plan.json", encoding="utf-8"))
expected = [it["f_cell"] for b in plan["blocks"] for it in (b["items"][:SUBSET] if SUBSET else b["items"])]
expected = [ref for ref in expected if ref in info]  # guard against plan/info drift

# Functions whose computed value legitimately differs across sheets (time / randomness) — value-compare skipped.
VOLATILE = {"СЛЧИС", "СЛУЧМЕЖДУ", "СЛЧИСМАССИВ", "ТДАТА", "СЕГОДНЯ"}
missing, diverge, unexpected, allowed = [], [], [], []
for ref in expected:
    st = [state[name][ref] for name in sheets]
    nm = info[ref]["name"]
    if "empty" in st:
        missing.append((nm, ref, dict(zip(sheets, st))))
    elif len(set(st)) > 1:
        diverge.append((nm, ref, dict(zip(sheets, st))))
    elif st[0] == "err":
        (allowed if nm in ALLOWLIST else unexpected).append((nm, ref))
    elif nm not in VOLATILE:
        # all three sheets computed WITHOUT error — the same formula must yield the same value on each.
        # A differing value ⇒ a method inserted a DIFFERENT formula (silent build artifact) → DIVERGE.
        vals = [value[name][ref] for name in sheets]
        if len(set(vals)) > 1:
            diverge.append((nm, ref, dict(zip(sheets, vals))))

print(f"node {NODE}")
for name in sheets:
    print(f"  «{name}»: filled {filled[name]}")
print(f"expected-filled cells: {len(expected)} | allowlisted errors: {len(allowed)}")
ok = not (missing or diverge or unexpected)
if missing:
    print(f"\nFAIL — MISSING (a sheet did not fill these): {len(missing)}")
    for nm, ref, st in missing[:40]: print(f"    {nm} @ {ref}: {st}")
if diverge:
    print(f"\nFAIL — DIVERGE (sheets disagree — build artifact): {len(diverge)}")
    for nm, ref, st in diverge[:40]: print(f"    {nm} @ {ref}: {st}")
if unexpected:
    print(f"\nFAIL — UNEXPECTED errors (not allowlisted): {len(unexpected)}")
    for nm, ref in unexpected[:60]: print(f"    {nm} @ {ref}")
print("\n" + ("PASS ✓" if ok else "FAIL ✗"))
sys.exit(0 if ok else 1)
