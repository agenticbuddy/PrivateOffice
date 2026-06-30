#!/usr/bin/env python3
"""Check PrivateOffice client l10n overrides against upstream Collabora catalogs.

This is an analysis guardrail, not a translation validator. It answers:
  - does an override key exist in upstream ui-<lang>.json?
  - does it duplicate upstream exactly?
  - does it intentionally change an upstream value?
  - did the active built catalog receive the override value?

The upstream baseline MUST be the catalog the build actually merges INTO: the source-built,
UNMERGED ui-<lang>.json. The editor image ships that exact snapshot at
/usr/share/coolwsd/upstream-l10n (taken before the merge in editor/Dockerfile.online).
`--upstream-from-active` reads it from the running editor, alongside the merged active catalog,
so both come from the SAME container — that is the authoritative comparison.

The pinned base image (editor/manifests/upstream.json) is only an OFFLINE APPROXIMATION: it is a
different build (its prebuilt browser dist, not our from-source build) and can drift, so it must
not be trusted for accept/reject. Use it only via `--upstream-image`/default when offline.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = "/usr/share/coolwsd/browser/dist/l10n"
UPSTREAM_DIST = "/usr/share/coolwsd/upstream-l10n"  # unmerged source-built snapshot (Dockerfile.online)
DEFAULT_OVERRIDES = os.path.join(ROOT, "editor/l10n/overrides/client")
DEFAULT_MANIFEST = os.path.join(ROOT, "editor/manifests/upstream.json")
DEFAULT_OUT_DIR = os.path.join(ROOT, ".qa/l10n-overrides")


class CheckError(Exception):
    pass


def run(cmd, *, cwd=ROOT, check=True):
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and result.returncode:
        raise CheckError(
            f"command failed ({result.returncode}): {' '.join(cmd)}\n"
            f"stdout: {result.stdout.strip()}\n"
            f"stderr: {result.stderr.strip()}"
        )
    return result


def pinned_image_ref(manifest_path):
    with open(manifest_path, encoding="utf-8") as fh:
        manifest = json.load(fh)
    base = manifest["base_image"]
    repository = base["repository"]
    digest = base["digest"]
    return f"{repository}@{digest}"


def strict_json_object(path):
    duplicates = []

    def hook(pairs):
        seen = {}
        for key, value in pairs:
            if key in seen:
                duplicates.append(key)
            seen[key] = value
        return seen

    with open(path, encoding="utf-8") as fh:
        data = json.load(fh, object_pairs_hook=hook)
    if not isinstance(data, dict):
        raise CheckError(f"{path}: expected a JSON object")
    if duplicates:
        dupes = ", ".join(sorted(set(duplicates))[:20])
        raise CheckError(f"{path}: duplicate JSON keys: {dupes}")
    bad = [(k, type(v).__name__) for k, v in data.items() if not isinstance(k, str) or not isinstance(v, str)]
    if bad:
        sample = ", ".join(f"{k!r}:{t}" for k, t in bad[:10])
        raise CheckError(f"{path}: expected flat string->string JSON, got {sample}")
    return data


def load_overrides(override_dir):
    if not os.path.isdir(override_dir):
        raise CheckError(f"override dir not found: {override_dir}")
    out = {}
    for name in sorted(os.listdir(override_dir)):
        if not name.endswith(".json"):
            continue
        lang = name[:-5]
        out[lang] = strict_json_object(os.path.join(override_dir, name))
    if not out:
        raise CheckError(f"no override JSON files found in {override_dir}")
    return out


def copy_ui_catalogs_from_image(image_ref, langs, dst_dir):
    cid = run(["docker", "create", image_ref]).stdout.strip()
    try:
        copied = set()
        for lang in langs:
            dst = os.path.join(dst_dir, f"ui-{lang}.json")
            res = run(["docker", "cp", f"{cid}:{DIST}/ui-{lang}.json", dst], check=False)
            if res.returncode == 0:
                copied.add(lang)
        return copied
    finally:
        run(["docker", "rm", "-f", cid], check=False)


def copy_ui_catalogs_from_container(cid, langs, dst_dir, src_dir=DIST):
    copied = set()
    for lang in langs:
        dst = os.path.join(dst_dir, f"ui-{lang}.json")
        res = run(["docker", "cp", f"{cid}:{src_dir}/ui-{lang}.json", dst], check=False)
        if res.returncode == 0:
            copied.add(lang)
    return copied


def active_container(service, optional):
    result = run(["docker", "compose", "ps", "-q", service], check=False)
    cid = result.stdout.strip()
    if cid:
        return cid
    if optional:
        return None
    raise CheckError(f"active service is not running: {service}")


def load_catalog_map(catalog_dir, lang):
    path = os.path.join(catalog_dir, f"ui-{lang}.json")
    if not os.path.exists(path):
        return None
    return strict_json_object(path)


def build_rows(overrides, upstream_dir, active_dir=None):
    rows = []
    hard_failures = []
    for lang, override_map in overrides.items():
        upstream = load_catalog_map(upstream_dir, lang)
        active = load_catalog_map(active_dir, lang) if active_dir else None
        if upstream is None:
            hard_failures.append(f"missing upstream ui-{lang}.json")
            upstream = {}
        for key, override_value in override_map.items():
            upstream_exists = key in upstream
            upstream_value = upstream.get(key, "")
            if not upstream_exists:
                upstream_status = "missing_upstream"
                recommendation = "review key: custom Online code, stale key, or wrong catalog"
            elif upstream_value == override_value:
                upstream_status = "same_as_upstream"
                recommendation = "remove override unless it is intentionally pinned"
            else:
                upstream_status = "changes_upstream"
                recommendation = "keep only with rendered proof or product-specific rationale"

            active_value = ""
            if active is None:
                active_status = "not_checked"
            elif key not in active:
                active_status = "missing_active"
                hard_failures.append(f"{lang}:{key}: missing from active catalog")
            else:
                active_value = active[key]
                if active_value == override_value:
                    active_status = "matches_override"
                else:
                    active_status = "active_mismatch"
                    hard_failures.append(f"{lang}:{key}: active value does not match override")

            rows.append({
                "lang": lang,
                "key": key,
                "override_value": override_value,
                "upstream_status": upstream_status,
                "upstream_value": upstream_value,
                "active_status": active_status,
                "active_value": active_value,
                "recommendation": recommendation,
            })
    return rows, hard_failures


def write_outputs(rows, out_dir, meta):
    os.makedirs(out_dir, exist_ok=True)
    csv_path = os.path.join(out_dir, "overlap-report.csv")
    json_path = os.path.join(out_dir, "overlap-report.json")
    fields = [
        "lang", "key", "override_value", "upstream_status", "upstream_value",
        "active_status", "active_value", "recommendation",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump({"meta": meta, "rows": rows}, fh, ensure_ascii=False, indent=1)
    return csv_path, json_path


def summarize(rows):
    by_upstream = Counter(row["upstream_status"] for row in rows)
    by_active = Counter(row["active_status"] for row in rows)
    by_lang = defaultdict(Counter)
    for row in rows:
        by_lang[row["lang"]][row["upstream_status"]] += 1
    return by_upstream, by_active, by_lang


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--override-dir", default=DEFAULT_OVERRIDES)
    parser.add_argument("--upstream-from-active", action="store_true",
                        help="authoritative: read the unmerged source-built snapshot from the running editor "
                             "(/usr/share/coolwsd/upstream-l10n); requires the active container")
    parser.add_argument("--upstream-dir", help="directory containing unmerged ui-<lang>.json files")
    parser.add_argument("--upstream-image", help="OFFLINE approximation: image with prebuilt ui-<lang>.json (can drift)")
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--active-service", default="editor", help="docker compose service to verify merged active catalogs")
    parser.add_argument("--no-active-check", action="store_true")
    parser.add_argument("--active-optional", action="store_true", help="skip active check when the service is not running")
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    overrides = load_overrides(args.override_dir)
    langs = sorted(overrides)
    hard_failures = []

    with tempfile.TemporaryDirectory() as tmp:
        # One active editor container serves both the merged (active) catalog and, with
        # --upstream-from-active, the unmerged upstream snapshot baked by editor/Dockerfile.online.
        active_cid = None
        if args.upstream_from_active or not args.no_active_check:
            # --upstream-from-active needs the container, so it overrides --active-optional
            optional = args.active_optional and not args.upstream_from_active
            active_cid = active_container(args.active_service, optional)

        # --- upstream baseline ---
        if args.upstream_from_active:
            upstream_source = f"active:{args.active_service}:{(active_cid or '')[:12]}:{UPSTREAM_DIST}"
            upstream_dir = os.path.join(tmp, "upstream")
            os.makedirs(upstream_dir, exist_ok=True)
            copied = copy_ui_catalogs_from_container(active_cid, langs, upstream_dir, src_dir=UPSTREAM_DIST)
            missing = sorted(set(langs) - copied)
            if missing:
                hard_failures.append("missing upstream snapshot (rebuild editor for PO-SRC upstream-l10n): " + ", ".join(missing))
        elif args.upstream_dir:
            upstream_dir = args.upstream_dir
            upstream_source = upstream_dir
            missing = [lang for lang in langs if not os.path.exists(os.path.join(upstream_dir, f"ui-{lang}.json"))]
            if missing:
                hard_failures.append("missing upstream catalogs: " + ", ".join(missing))
        else:
            image = args.upstream_image or pinned_image_ref(args.manifest)
            upstream_source = f"OFFLINE-approx-image:{image}"
            upstream_dir = os.path.join(tmp, "upstream")
            os.makedirs(upstream_dir, exist_ok=True)
            copied = copy_ui_catalogs_from_image(image, langs, upstream_dir)
            missing = sorted(set(langs) - copied)
            if missing:
                hard_failures.append("missing upstream catalogs: " + ", ".join(missing))

        # --- active (merged) catalog ---
        active_dir = None
        active_source = None
        if not args.no_active_check:
            if active_cid:
                active_source = f"docker-compose:{args.active_service}:{active_cid[:12]}"
                active_dir = os.path.join(tmp, "active")
                os.makedirs(active_dir, exist_ok=True)
                copied = copy_ui_catalogs_from_container(active_cid, langs, active_dir)
                missing = sorted(set(langs) - copied)
                if missing:
                    hard_failures.append("missing active catalogs: " + ", ".join(missing))
            else:
                active_source = f"docker-compose:{args.active_service}:not-running"

        rows, row_failures = build_rows(overrides, upstream_dir, active_dir)
        hard_failures.extend(row_failures)

    by_upstream, by_active, by_lang = summarize(rows)
    meta = {
        "override_dir": os.path.relpath(args.override_dir, ROOT),
        "upstream_source": upstream_source,
        "active_source": active_source,
        "total_overrides": len(rows),
        "by_upstream_status": dict(by_upstream),
        "by_active_status": dict(by_active),
        "by_lang": {lang: dict(counts) for lang, counts in sorted(by_lang.items())},
        "hard_failures": hard_failures,
    }
    csv_path, json_path = write_outputs(rows, args.out_dir, meta)

    print(f"l10n override overlap check")
    print(f"  overrides: {len(rows)}")
    print(f"  upstream: {upstream_source}")
    if active_source:
        print(f"  active: {active_source}")
    print(f"  upstream status: {dict(by_upstream)}")
    print(f"  active status: {dict(by_active)}")
    print(f"  csv: {os.path.relpath(csv_path, ROOT)}")
    print(f"  json: {os.path.relpath(json_path, ROOT)}")
    if hard_failures:
        print("  hard failures:")
        for item in hard_failures[:20]:
            print(f"    - {item}")
        if len(hard_failures) > 20:
            print(f"    ... {len(hard_failures) - 20} more")
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except CheckError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
