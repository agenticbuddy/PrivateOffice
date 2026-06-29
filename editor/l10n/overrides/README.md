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

At the target source build these files are merged into the client catalogs and compiled into
`.mo` deterministically. Until then see the transitional note below.

## Important caveat: catalog presence is not proof

A string can be present in a client catalog and still render in English, because the same UI
element may be drawn from LibreOffice-core instead of the client catalog (the `Clipboard` case:
it exists in `ui-ru.json` yet the ribbon shows English). So a value added under `client/` is a
**hypothesis** until the render is verified. Confirm the render path per string (add the value,
rebuild/clear cache, check the screen) before trusting it. See `assisted_translate.md`.

## Transitional note

These files are the **canonical source** for the client-catalog translations. The editor
`Dockerfile` currently still injects the same values directly via `sed` (patch `PO-L10N-006` in
`editor/manifests/patchset.json`). Switching the Dockerfile to consume these files (and dropping
the inline `sed`) is a build-verified migration step that has **not** been done yet — it needs a
rebuild to confirm the result is identical.
