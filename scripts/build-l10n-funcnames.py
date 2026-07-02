#!/usr/bin/env python3
"""Generate editor/po-funcnames.js — a per-locale {EnglishFuncName: LocalizedName} map.

WHY: the Collabora browser builds the notebookbar function dropdowns (Formulas tab →
Date & Time / Financial / Logical / Math & Trig / … ) from a STATIC table that only
localizes de/fr/es (`getLocalizedFuncName` in browser/src/control/jsdialog/Definitions.Menu.ts).
For every other locale it emits the ENGLISH name both as the visible label AND inside
`.uno:InsertFunction?FunctionName=<name>`. A localized LO core only accepts the LOCALIZED name
(СЕГОДНЯ, not TODAY) — so in RU (and every other localized locale) the dropdown shows English
AND fails to insert. This map, extracted straight from the LO core, feeds getLocalizedFuncName
(via window.PO_FN_NAMES from po-funcnames.js) so the dropdowns are localized and insert correctly.

COVERAGE: every locale the app supports (backend/app/services/locales.py SUPPORTED) that also ships
an LO function-name catalog. The supported list is read from that file at generation time, so the
coverage tracks the app automatically instead of a hand-maintained list. Locales without an LO
catalog (e.g. hi/th/fa — LO does not localize function names for them) correctly stay English.

Source modules (per LO resource dir /opt/collaboraoffice/program/resource/<dir>/LC_MESSAGES/):
  for.mo  — builtin Calc functions, msgctxt=RID_STRLIST_FUNCTION_NAMES  (msgid=EN, msgstr=localized)
  sca.mo  — add-in functions,       msgctxt=*_FUNCNAME_*

Output: editor/po-funcnames.js  ->  window.PO_FN_NAMES = { "<locale>": { "TODAY": "СЕГОДНЯ", … }, … }
Keys are lowercased with '-'->'_'; a base-language alias is added too (e.g. "pt" -> pt_BR map) so a
normalized String.locale hits whether it carries a region (pt-BR, ru-RU) or not. Only entries whose
localized name DIFFERS from English are kept, which keeps the file small. Regenerate on every re-pin.

Run: python3 scripts/build-l10n-funcnames.py            # all supported locales, from the running editor
"""
import gettext
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE = "/opt/collaboraoffice/program/resource"
OUT = os.path.join(ROOT, "editor", "po-funcnames.js")
LOCALES_PY = os.path.join(ROOT, "backend", "app", "services", "locales.py")

# App locale code -> LO resource-dir name where they differ (region uppercased). Everything else
# maps 1:1 (nl, pl, ru, it, …); locales with no LO dir are skipped gracefully.
LO_DIR = {"pt-BR": "pt_BR", "zh-CN": "zh_CN", "zh-TW": "zh_TW"}


def supported_locales():
    """Read SUPPORTED codes from backend/app/services/locales.py (source of truth), minus 'en'."""
    text = open(LOCALES_PY, encoding="utf-8").read()
    block = re.search(r"SUPPORTED[^{]*\{(.*?)\n\}", text, re.S)
    codes = re.findall(r'"([A-Za-z-]+)"\s*:', block.group(1)) if block else []
    return [c for c in codes if c != "en"]


def editor_container():
    cid = subprocess.run(["docker", "compose", "ps", "-q", "editor"],
                         cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if not cid:
        sys.exit("editor container is not running (./scripts/up.sh editor)")
    return cid


def docker_cp(cid, src, dst):
    return subprocess.run(["docker", "cp", f"{cid}:{src}", dst],
                          capture_output=True, text=True).returncode == 0


def funcnames_from_mo(path, ctxt_pred):
    """Return {english_msgid: localized_msgstr} for entries whose msgctxt passes ctxt_pred."""
    out = {}
    with open(path, "rb") as fh:
        tr = gettext.GNUTranslations(fh)
    for key, val in tr._catalog.items():
        if not key or isinstance(key, tuple):
            continue
        msgctxt, msgid = (key.split("\x04", 1) if "\x04" in key else (None, key))
        if not msgid or not val or not msgctxt or not ctxt_pred(msgctxt):
            continue
        out[msgid] = val
    return out


def main():
    cid = editor_container()
    codes = supported_locales()
    all_maps = {}
    stats = {}
    with tempfile.TemporaryDirectory() as tmp:
        for code in codes:
            lo = LO_DIR.get(code, code)
            m = {}
            for mod, pred in (("for", lambda c: c == "RID_STRLIST_FUNCTION_NAMES"),
                              ("sca", lambda c: "_FUNCNAME_" in c)):
                dst = os.path.join(tmp, f"{lo}-{mod}.mo")
                if docker_cp(cid, f"{CORE}/{lo}/LC_MESSAGES/{mod}.mo", dst):
                    m.update(funcnames_from_mo(dst, pred))
            # keep only real translations (localized != english); browser falls back to EN otherwise
            m = {en: loc_name for en, loc_name in m.items() if loc_name and loc_name != en}
            if not m:
                continue  # no LO catalog / nothing localized (e.g. hi/th/fa, or cs/ja that stay EN)
            key = code.lower().replace("-", "_")
            all_maps[key] = m
            all_maps.setdefault(key.split("_")[0], m)  # base-language alias (pt->pt_BR, zh->zh_CN)
            stats[key] = len(m)

    payload = json.dumps(all_maps, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    header = ("/* GENERATED by scripts/build-l10n-funcnames.py — do not edit by hand.\n"
              "   Localized Calc function names extracted from the LO core (for.mo + sca.mo) for\n"
              "   every app-supported locale that has an LO catalog. Consumed by the getLocalizedFuncName\n"
              "   source patch so notebookbar function dropdowns show localized names AND insert\n"
              "   correctly in every locale. Regenerate after re-pinning the engine. */\n")
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(header)
        fh.write("window.PO_FN_NAMES=" + payload + ";\n")

    print(f"wrote {OUT}")
    print(f"supported (from locales.py): {codes}")
    print("entries per locale:", json.dumps(stats, ensure_ascii=False))
    for loc in ("ru", "nl", "pl", "zh_cn"):
        mp = all_maps.get(loc, {})
        print(f"  {loc} TODAY -> {mp.get('TODAY', '<none>')!r} | SUM -> {mp.get('SUM', '<none>')!r} | count={len(mp)}")


if __name__ == "__main__":
    main()
