# Editor localization overrides

Our translations for the embedded editor live here as **data**, separate from code changes.
This is the model described in `assisted_translate.md` (translations are data; code fixes are
patches).

## Layout

- `client/<lang>.json` — overlays for the editor's browser catalogs
  (`/usr/share/coolwsd/browser/dist/l10n/ui-<lang>.json`). Plain `key -> translation` JSON,
  UTF-8, sorted keys. `<lang>` is the catalog token (e.g. `ru`, `ar`, `pt_BR`).
- `core/<lang>.po` — overlays for LibreOffice-core gettext catalogs
  (`/opt/collaboraoffice/program/resource/<lang>/LC_MESSAGES/*.mo`). Use `.po` because core
  strings can carry `msgctxt` (context), which the flat client JSON cannot express.

The deployed source build (`editor/Dockerfile.online`) merges `client/<lang>.json` into the built
client catalogs at image-build time. Compiling `core/<lang>.po` into `.mo` is the next step (not
done yet). See "How these are consumed" below.

## Important caveat: catalog presence is not proof

A string can be present in a client catalog and still render in English, because the same UI
element may be drawn from LibreOffice-core instead of the client catalog (the `Clipboard` case:
it exists in `ui-ru.json` yet the ribbon shows English). So a value added under `client/` is a
**hypothesis** until the render is verified. Confirm the render path per string (add the value,
rebuild/clear cache, check the screen) before trusting it. See `assisted_translate.md`.

## How these are consumed

These files are the **canonical source** for the client-catalog translations. The deployed build,
`editor/Dockerfile.online` (Collabora Online from source, wired in `docker-compose.yml`), **merges**
every `client/<lang>.json` into the built `ui-<lang>.json` at image-build time (build-verified). The
prebuilt-base stopgap `editor/Dockerfile` still injects the same values via inline `sed` (patch
`PO-L10N-006`) and is not the deployed build.

`core/<lang>.po` (LibreOffice-core overrides) are **not consumed yet** — compiling them into `.mo`
is the next localization step.

## Overlap check

Run this before accepting a client override batch (the editor must be built + running):

```bash
make l10n              # authoritative
```

It compares `client/<lang>.json` against the **unmerged, source-built** `ui-<lang>.json` — the
exact catalog the build merges into — read from the running editor's snapshot at
`/usr/share/coolwsd/upstream-l10n` (baked by `editor/Dockerfile.online` before the merge), and
also verifies the merged active catalog from the SAME container. Both are MANDATORY: if the editor
service is not running/reachable the check FAILS (non-zero), so a green result really means checked.

Offline approximation (no running editor): `make l10n-overlap-offline` uses the pinned base-image
catalog as upstream and skips the active check. Its report is tagged `OFFLINE-approx` — a different
build that can drift, so treat it as a hint, not a verdict.

Both write:

- `.qa/l10n-overrides/overlap-report.csv`
- `.qa/l10n-overrides/overlap-report.json`

Interpretation:

- `same_as_upstream` - redundant local override; usually delete it.
- `changes_upstream` - local value differs from upstream; keep only with rendered proof or
  product-specific rationale.
- `missing_upstream` - key is absent upstream; review whether it is custom Online code, a stale
  key, or the wrong catalog.
- `active_mismatch` / `missing_active` - build/merge problem; the check fails.
