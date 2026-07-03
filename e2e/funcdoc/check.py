#!/usr/bin/env python3
"""Verify a 3-sheet functions-check workbook AS A TEST: exit non-zero on any regression.

Fails (exit 1) if, for a formula that is filled on at least one sheet:
  • MISSING   — some sheet did not fill it (dropped insertion / seed),
  • DIVERGE   — sheets disagree (ok on one, error on another → build artifact, not a core bug),
  • UNEXPECTED— it errors on ALL sheets but is not in ALLOWLIST (a genuinely new failure).
Errors that are identical across all sheets AND allowlisted (inherently non-computable) are OK.
Usage: check.py <node_id>   →  prints a PASS/FAIL report, exits 0 (pass) or 1 (fail).
"""
import sys, json, subprocess, zipfile
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

# per-sheet state for every formula cell: "ok" | "err" | "empty"
sheets = list(name2file)
state = {name: {} for name in sheets}
for name, part in name2file.items():
    cells = {}
    for c in ET.fromstring(z.read(part)).iter(NS + "c"):
        v = c.find(NS + "v")
        cells[c.get("r")] = {"t": c.get("t"), "v": (v.text if v is not None else None)}
    for ref in info:
        c = cells.get(ref)
        state[name][ref] = "empty" if (c is None or c["v"] is None) else ("err" if c["t"] == "e" else "ok")

filled = {name: sum(1 for ref in info if state[name][ref] != "empty") for name in sheets}
expected = [ref for ref in info if any(state[name][ref] != "empty" for name in sheets)]

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
