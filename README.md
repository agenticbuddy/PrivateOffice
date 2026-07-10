# PrivateOffice Workspace

Self-hosted, internal document workspace built around **PrivateOffice** (a customized, self-hosted
build of the Collabora Online editor). Admin-provisioned users, a shared folder/file tree with
`owner`/`editor`/`reader` sharing, in-browser editing, per-viewer localized UI.

## Documentation
- **Deploy & run** — this file (below).
- Architecture & contracts: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- Design system: [`DESIGN.md`](DESIGN.md)
- **Editor (Collabora Online) customizations** — every change vs upstream, the localization/theme/build
  layers, and how to add a language: [`docs/CO-CHANGES.md`](docs/CO-CHANGES.md)
- Localization method (how the editor is translated to 100%): [`assisted_translate.md`](assisted_translate.md)
- Supported UI languages: [`docs/LANGUAGES.md`](docs/LANGUAGES.md)

## Stack
nginx · FastAPI (Python) + Vue 3 (TypeScript) · PostgreSQL · a self-hosted editor (Collabora Online / CODE) · MinIO —
all in Docker Compose behind a single `http://localhost:8088` origin.

## Deploy from scratch

**Prerequisites:** Docker + Docker Compose v2, `git`, and a free port **8088**.
The editor's first build compiles Collabora Online from source — **slow (~15–25 min once)**, then fast from cache.

```bash
git clone <repo-url> privateoffice && cd privateoffice
cp deploy/.env.example .env      # compose reads .env from the repo root; edit secrets/passwords
./scripts/up.sh                  # build + start the whole stack (editor from source, postgres, minio, app, nginx)
# app:   http://localhost:8088
# admin: http://localhost:8088/admin   (BasicAuth  admin / 123)
```

> **Use `./scripts/up.sh`, not a bare `docker compose up -d --build`.** The script stamps
> `BUILD_ID=<git sha>` so the editor's per-build cache-bust works; a bare compose build leaves
> `BUILD_ID=dev` → stale editor assets can be served after a redeploy.

**First login.** A default admin (`admin@example.com`) is bootstrapped on first boot. Create end-user
accounts from the admin area, then sign them in by password or by the generated passwordless magic link
(in dev, the link is in the app logs: `docker compose logs app`).

> Port 8088 is used because 80/8080 were taken on the dev host. To move it, change `PUBLIC_ORIGIN` in
> `.env` **and** the nginx port mapping in `docker-compose.yml` together (the editor's `server_name`
> must include the public port).

### Rebuild after changes (what you edited → how to rebuild)
| Edited | Command |
|---|---|
| `editor/**` (theme, l10n overrides, Dockerfile, cool-help) | `./scripts/up.sh editor` |
| `frontend/**` (SPA) | `./scripts/up.sh app` |
| `nginx/**` | `docker compose up -d nginx` |
| `backend/**` | nothing — hot-reload (bind-mount) |

> After an editor change, **commit before verifying**: an uncommitted build gets a `<sha>-dirty`
> cache-bust token and the browser may serve stale assets. See [`docs/CO-CHANGES.md`](docs/CO-CHANGES.md) §6/§8.

## Development / tests

```bash
# backend (bind-mounted, hot-reload) — run the test suite:
docker compose exec -T -w /app/backend app pytest -q

# frontend (SPA) — rebuild the app image to apply changes:
./scripts/up.sh app

# end-to-end (admin + user cycles, glass2 chrome check) and the 22-language sweep:
cd e2e && npm install && npx playwright install chromium
npx playwright test                              # full suite
npx playwright test tests/lang-sweep.spec.ts     # just the UI language sweep
```

The language sweep regenerates [`docs/LANGUAGE_REPORT.md`](docs/LANGUAGE_REPORT.md) (per-locale UI report).
