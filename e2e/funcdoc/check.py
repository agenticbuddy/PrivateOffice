#!/usr/bin/env python3
"""Verify a 3-sheet functions-check workbook: for each sheet, report how many formula cells compute
vs error. Usage: funcdoc_smoke_check.py <node_id>"""
import sys, json, subprocess, zipfile
from xml.etree import ElementTree as ET

NODE = sys.argv[1]
subprocess.run(["curl", "-s", "-u", "admin:123",
                f"http://localhost:8088/admin/api/nodes/{NODE}/download", "-o", "/tmp/smoke.xlsx"], check=True)
info = json.load(open("/tmp/funcdoc.json", encoding="utf-8"))["info"]  # f_cell -> {name, formula}
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
RNS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
z = zipfile.ZipFile("/tmp/smoke.xlsx")

# map sheet display name -> worksheet part
rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
name2file = {}
for s in ET.fromstring(z.read("xl/workbook.xml")).iter(NS + "sheet"):
    tgt = rels[s.get(RNS + "id")]
    name2file[s.get("name")] = "xl/" + tgt.lstrip("/") if not tgt.startswith("xl/") else tgt

ss = []
if "xl/sharedStrings.xml" in z.namelist():
    for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(NS + "si"):
        ss.append("".join(t.text or "" for t in si.iter(NS + "t")))

print(f"node {NODE}")
allerr = {}
for name, part in name2file.items():
    sheet = ET.fromstring(z.read(part))
    cells = {}
    for c in sheet.iter(NS + "c"):
        v = c.find(NS + "v"); val = v.text if v is not None else None
        if c.get("t") == "s" and val is not None:
            val = ss[int(val)]
        cells[c.get("r")] = {"t": c.get("t"), "v": val}
    ok = err = filled = 0
    errs = []
    for ref, meta in info.items():
        c = cells.get(ref)
        if c is None or c["v"] is None:
            continue  # not filled (SUBSET) — skip
        filled += 1
        if c["t"] == "e":
            err += 1; errs.append((meta["name"], c["v"]))
        else:
            ok += 1
    print(f"  «{name}»: filled {filled} | ok {ok} | errors {err}")
    allerr[name] = errs

# show the union of erroring functions (same formulas across sheets)
u = {}
for name, errs in allerr.items():
    for n, e in errs:
        u.setdefault((n, e), set()).add(name)
if u:
    print("\n--- erroring functions (error : sheets) ---")
    for (n, e), sheets in sorted(u.items()):
        print(f"  {n}\t{e}\t{sorted(sheets)}")
