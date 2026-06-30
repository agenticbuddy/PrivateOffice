#!/usr/bin/env python3
"""Extract the COMPLETE translatable-string universe for one reference language.

This is the completeness *denominator* for localization: every string that the
editor CAN translate, with its CURRENT value, regardless of whether we ever saw
it rendered. The rendered browser walk (e2e/scripts/editor-l10n-rendered.mjs)
supplies the other half - WHERE each string is actually seen.

Two source layers (see assisted_translate.md, Этап 2):
  - client catalogs: /usr/share/coolwsd/browser/dist/l10n/{ui-<lang>.json,
    uno/<lang>.json, locore/<lang>.json}  - flat {english: translation}, no msgctxt.
  - LibreOffice core gettext: /opt/collaboraoffice/program/resource/<lang>/
    LC_MESSAGES/*.mo  - supports msgctxt + plural; parsed here with the Python
    stdlib `gettext` (no msgunfmt / no container mutation needed).

Files are pulled fresh from the RUNNING editor container (reproducible), so the
output reflects exactly what the live build ships.

Output: .qa/l10n/ru-catalog.json (regenerable; .qa is gitignored).
Run:    python3 scripts/build-l10n-catalog.py            # ru, from the running editor
        python3 scripts/build-l10n-catalog.py --lang ru  # explicit
"""
import argparse
import gettext
import json
import os
import struct
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = "/usr/share/coolwsd/browser/dist/l10n"
CORE = "/opt/collaboraoffice/program/resource"


def editor_container():
    cid = subprocess.run(
        ["docker", "compose", "ps", "-q", "editor"],
        cwd=ROOT, capture_output=True, text=True,
    ).stdout.strip()
    if not cid:
        sys.exit("editor container is not running (./scripts/up.sh editor)")
    return cid


def docker_cp(cid, src, dst):
    """Copy a path out of the container; return True on success."""
    r = subprocess.run(["docker", "cp", f"{cid}:{src}", dst],
                       capture_output=True, text=True)
    return r.returncode == 0


def load_client(path, source_class, lang):
    """Flat client catalog {english: translation}. english IS the key/msgid."""
    out = []
    if not os.path.exists(path):
        return out
    data = json.load(open(path, encoding="utf-8"))
    for en, tr in data.items():
        out.append({
            "en": en,
            lang: tr,
            "source_class": source_class,
            "module": None,
            "msgctxt": None,
        })
    return out


def load_mo(path, module, lang):
    """Parse a gettext .mo via the stdlib. _catalog keys are either a bare
    msgid, an "ctxt\\x04msgid" string (msgctxt), or a (msgid, n) plural tuple.
    The empty msgid holds metadata and is skipped."""
    out = []
    with open(path, "rb") as fh:
        tr = gettext.GNUTranslations(fh)
    for key, val in tr._catalog.items():
        if key == "":
            continue
        plural = None
        if isinstance(key, tuple):
            key, plural = key  # (msgid, plural_index)
        msgctxt = None
        if "\x04" in key:
            msgctxt, key = key.split("\x04", 1)
        if not key:
            continue
        rec = {
            "en": key,
            lang: val,
            "source_class": "core-mo",
            "module": module,
            "msgctxt": msgctxt,
        }
        if plural is not None:
            rec["plural_index"] = plural
        out.append(rec)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="ru", help="reference language code (LO catalog code)")
    ap.add_argument("--out", default=os.path.join(ROOT, ".qa/ru-term-inventory/ru-catalog.json"))
    args = ap.parse_args()
    lang = args.lang

    cid = editor_container()
    entries = []
    stats = {}

    with tempfile.TemporaryDirectory() as tmp:
        # --- client catalogs ---
        client_map = {
            "client-ui": f"{DIST}/ui-{lang}.json",
            "client-uno": f"{DIST}/uno/{lang}.json",
            "client-locore": f"{DIST}/locore/{lang}.json",
        }
        for source_class, src in client_map.items():
            dst = os.path.join(tmp, source_class + ".json")
            if docker_cp(cid, src, dst):
                rows = load_client(dst, source_class, lang)
                entries += rows
                stats[source_class] = len(rows)
            else:
                stats[source_class] = "MISSING"

        # --- core .mo modules ---
        core_dst = os.path.join(tmp, "core")
        os.makedirs(core_dst, exist_ok=True)
        core_n = 0
        modules = 0
        if docker_cp(cid, f"{CORE}/{lang}/LC_MESSAGES/.", core_dst):
            for fn in sorted(os.listdir(core_dst)):
                if not fn.endswith(".mo"):
                    continue
                rows = load_mo(os.path.join(core_dst, fn), fn[:-3], lang)
                entries += rows
                core_n += len(rows)
                modules += 1
        stats["core-mo"] = core_n
        stats["core-modules"] = modules

    # de-dup identical (source_class, module, msgctxt, en) keeping first value
    seen = set()
    uniq = []
    for e in entries:
        k = (e["source_class"], e["module"], e["msgctxt"], e["en"], e.get("plural_index"))
        if k in seen:
            continue
        seen.add(k)
        uniq.append(e)

    translated = sum(1 for e in uniq if e.get(lang) and e[lang] != e["en"])
    # composed-fragment smell: leading/trailing-space msgids glued at runtime
    fragments = sum(1 for e in uniq if e["en"] != e["en"].strip())

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(
        {
            "meta": {
                "lang": lang,
                "container": cid[:12],
                "entries": len(uniq),
                "translated": translated,
                "space_fragments": fragments,
                "by_source": stats,
            },
            "entries": uniq,
        },
        open(args.out, "w", encoding="utf-8"),
        ensure_ascii=False,
        indent=1,
    )

    print(f"wrote {args.out}")
    print(f"  lang={lang}  entries={len(uniq)}  translated={translated}  space_fragments={fragments}")
    for k, v in stats.items():
        print(f"    {k}: {v}")


if __name__ == "__main__":
    main()
