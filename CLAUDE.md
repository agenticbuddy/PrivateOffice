# Project: PrivateOffice (self-hosted document workspace)

FastAPI+Vue SPA + an embedded self-hosted editor engine (CODE), behind nginx, with Postgres/MinIO.
Run on http://localhost:8088 — build/start with `./scripts/up.sh` (NOT a bare
`docker compose up --build`). The WAL lives in `.claude/update-log.md` — document every change.

## CONVENTIONS

### Fix at the source — never override as a substitute for fixing
When something renders/behaves wrong, **fix the actual element in its own source code**
so the correct result loads on the first paint. It is FORBIDDEN to mask a problem with an
override layer *instead of* fixing it, i.e.:
- no bolt-on override stylesheets / extra `!important` rules piled on top to beat a default,
- no runtime DOM patching / `setInterval` scrubbers,
- no wrapper or post-load hacks.

For the embedded editor specifically: its CSS, branding and HTML in the image ARE editable
at build time (`editor/Dockerfile.online`). Theme it through the editor's **own** files and native
CSS variables (`branding.css`, the `--color-*` / `--co-primary-element` tokens, the real
class rules) so menus, hovers, submenus, dialogs are correct natively — do not bolt a separate
override sheet on top to patch individual elements. Overriding is acceptable ONLY when the
source genuinely cannot be edited.

### Git: commit self-contained tasks automatically
Initialize/maintain the repo and commit each self-contained, completed+verified task on your
own (no need to ask each time). One logical task = one commit, clear message. Don't commit
debugging artifacts (root-level screenshots, zips, `.playwright-mcp/`).

## BUILD & RUN
- Stack: `./scripts/up.sh`. Builds + starts; stamps `BUILD_ID=<git sha>` (a bare `docker compose up --build` leaves it `dev` → editor cache-bust is a no-op). One service: `./scripts/up.sh editor|app|nginx`.
- Editor = built FROM SOURCE (`editor/Dockerfile.online`: Collabora Online @ pinned `online.mirror cp-26.04.1-4` against the base image's engine). `editor/Dockerfile` = prebuilt-base stopgap/fallback.
- Versions PINNED in `editor/manifests/upstream.json`. Never `:latest`. Re-pin only deliberately, then a FULL Playwright acceptance pass.

## REBUILD AFTER A CHANGE
- `editor/**` (Dockerfile.online, branding-privateoffice.css, l10n/overrides/*, po-logo.svg, po-toggle.js) → `./scripts/up.sh editor`
- `frontend/**` (SPA) → `./scripts/up.sh app`
- `nginx/**` → `docker compose up -d nginx`
- `backend/**` → bind-mount hot-reload; tests: `docker compose exec -w /app/backend app pytest -q`

## VERIFY — Playwright, ALWAYS
- EVERY change is verified with Playwright (`e2e/`). Never "looks fine" without a Playwright check + screenshot.
- Editor: verify in a CLEAN browser profile; `?b=<token>` in served assets must == HEAD.
- Localization: the RENDER is the only ground truth. Catalog presence ≠ what renders (render-path) — verify the actual screen per element, screenshot every block.

## WORK: LOCALIZATION + REDESIGN — zones (fix at source, per zone)
| Zone | Edit here | Verify |
|---|---|---|
| Client UI text (ribbon, menus, tooltips, client dialogs) | `editor/l10n/overrides/client/<lang>.json` (data, merged at build) | Playwright render |
| Core text (LO dialogs, `.ui`, some ribbon) | `editor/l10n/overrides/core/<lang>.po` (compile — not wired yet) | Playwright render |
| Theme / sizes / design of UI chrome | `editor/branding-privateoffice.css` (folded into bundle.css) | Playwright screenshots |
| Icons / logo | `editor/po-logo.svg` + image swap in `Dockerfile.online` | Playwright |
| Rebrand / URLs / code fixes / cache-bust | `editor/Dockerfile.online` (each unit catalogued in `editor/manifests/patchset.json`) | Playwright |
| SPA text (login, files, profile, modals) | `frontend/src/i18n/messages/<locale>.json` (vue-i18n) | Playwright |
| SPA design | `frontend/src/**` (Vue + CSS) | Playwright |

Method + per-string rigor: `assisted_translate.md`.

## WAL — record EVERY change
Append to `.claude/update-log.md` in the format from the global CLAUDE.md (why / before / what / after / tests).
