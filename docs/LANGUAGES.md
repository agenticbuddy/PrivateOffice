# Languages

Two distinct language layers (do not conflate):

- **UI language** — set per viewer via the `lang` URL param to CO and via `vue-i18n`
  in the SPA. CO (CODE image) ships UI packs for ~89 languages.
- **Spellcheck dictionaries** — separate, configured via CO `allowed_languages`
  (default: `de_DE en_GB en_US es_ES fr_FR it pt_BR pt_PT ru`). Not required for UI.

## Locale catalog used by the app

`frontend/src/i18n/locales.ts` defines the selectable locales with native names and
text direction. The SPA ships full message catalogs for the **primary set** and falls
back to `en` for the rest (CO editor still renders fully localized for all).

### Primary set (full SPA catalogs + tested)

| Code   | Native name        | Dir |
|--------|--------------------|-----|
| en     | English            | ltr |
| es     | Español            | ltr |
| de     | Deutsch            | ltr |
| fr     | Français           | ltr |
| pt-BR  | Português (Brasil) | ltr |
| ru     | Русский            | ltr |
| it     | Italiano           | ltr |
| nl     | Nederlands         | ltr |
| pl     | Polski             | ltr |
| uk     | Українська         | ltr |
| tr     | Türkçe             | ltr |
| cs     | Čeština            | ltr |
| zh-CN  | 简体中文            | ltr |
| ja     | 日本語              | ltr |
| ko     | 한국어              | ltr |
| hi     | हिन्दी               | ltr |
| vi     | Tiếng Việt         | ltr |
| id     | Bahasa Indonesia   | ltr |
| th     | ไทย                 | ltr |
| ar     | العربية             | rtl |
| he     | עברית               | rtl |
| fa     | فارسی               | rtl |

22 locales, including 3 RTL (ar, he, fa) to verify mirroring. This is the set used by
the Block 9 language sweep (`docs/LANGUAGE_REPORT.md`).

## Mapping to CO `lang`

The SPA locale maps 1:1 to the CO `lang` param, normalizing to CO's expected form
(e.g. `pt-BR` → `pt-BR`, `zh-CN` → `zh-CN`, `uk` → `uk-UA`). See
`backend/app/services/locales.py`.
