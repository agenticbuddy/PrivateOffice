# Localization baseline

The fixed starting point we localize against (Stage 1 / baseline in `assisted_translate.md`).
Translations are authored against this exact version; on upgrade, re-pin deliberately and re-run
the full acceptance pass before promoting.

## Pinned version

- Base image: `collabora/code@sha256:75859dc9f9084d1877ce36cf96ec86600f495bade33289c9cbc27e0a0ee23b81` (tag at pin: `latest`, pinned 2026-06-28)
- Collabora Online (`coolwsd`): `26.04.1.4-1`
- Collabora Office core (`collaboraoffice`): `26.04.1-4`; `code-brand` `26.04.1-3`; LibreOffice buildid `6040(Build:4)`
- Machine-readable: `editor/manifests/upstream.json`. Patches on top: `editor/manifests/patchset.json`.

## Scope

Three editors in one engine: **Writer** (.docx), **Calc** (.xlsx), **Impress** (.pptx).

22 UI locales (the `SUPPORTED` dict in `backend/app/services/locales.py`):

`en`, `es`, `de`, `fr`, `pt-BR`, `ru`, `it`, `nl`, `pl`, `uk`, `tr`, `cs`, `zh-CN`, `ja`, `ko`,
`hi`, `vi`, `id`, `th`, `ar`, `he`, `fa`. (`ar`, `he`, `fa` are RTL.)

Note the language-code chain: the app locale is mapped to the editor `lang` parameter by
`co_lang` (e.g. `ru` -> `ru-RU`), and the editor then normalizes the region and loads a specific
catalog file (`ru-RU` -> `ui-ru.json`). A wrong code silently loads no/the wrong catalog.

## Localization layers and where they live

- Frontend SPA (our app): `frontend/src/i18n/messages/*.json` (vue-i18n).
- Editor browser UI (client `_()`): `/usr/share/coolwsd/browser/dist/l10n/ui-<lang>.json`,
  `uno/<lang>.json`, `locore/<lang>.json`. Our overlays: `editor/l10n/overrides/client/`.
- LibreOffice-core (gettext, supports `msgctxt`):
  `/opt/collaboraoffice/program/resource/<lang>/LC_MESSAGES/*.mo`. Our overlays:
  `editor/l10n/overrides/core/`.

## Current measured state

The visible-surface coverage pass (Calc/Writer/Impress, ru/uk/ar/zh-CN) is recorded in
`.qa/l10n/REPORT.md` with the per-string matrix in `.qa/l10n/visible-coverage.csv`. Headline:
gaps are mostly in the client JSON, not core; Russian is client-side; Arabic needs both layers.
Treat those numbers as an upper bound — they count catalog presence, not what actually renders.

## Next baseline artifacts (not done yet)

- Hashes of the active catalogs / `.mo` / `bundle.js` from the pinned image.
- The full occurrence map (every string -> all the places it appears + its render path).
- A render ground-truth pass with a screenshot per object, per language.
