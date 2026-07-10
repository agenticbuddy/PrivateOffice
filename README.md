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

**Prerequisites:** Docker + Docker Compose v2, `git`, `make`, and a free port **8088**.
The editor's first build compiles Collabora Online from source — **slow (~15–25 min once)**, then fast from cache.

```bash
git clone <repo-url> privateoffice && cd privateoffice
make deploy          # ONE command: .env + build + start + admin setup + prints access info
```

`make deploy` (alias `make init`) copies `deploy/.env.example` → `.env` (if absent), builds and starts the
whole stack (editor from source, postgres, minio, app, nginx), waits until it is healthy, gives the SPA
administrator a password, and prints:

```
App (SPA):    http://localhost:8088
Admin panel:  http://localhost:8088/admin   → BasicAuth  admin / 123
SPA sign-in:  admin@example.com / admin123   (administrator; create end-users from the admin panel)
```

**`make` targets**

| Command | Does |
|---|---|
| `make deploy` / `make init` | Full deploy: config + build + start + admin setup + access info |
| `make up` | (Re)build + start the stack |
| `make down` | Stop + remove containers (**data volumes are kept**) |
| `make restart` | `make down` then `make deploy` |
| `make logs` / `make ps` | Follow logs / show stack status |
| `make admin` | Print the admin-panel URL + credentials |

> Override the defaults inline, e.g. `make deploy ADMIN_PASS=secret BOOTSTRAP_ADMIN_PASSWORD=…`.
> `make up` / `make deploy` run `./scripts/up.sh` (**not** a bare `docker compose up -d --build`): it stamps
> `BUILD_ID=<git sha>` so the editor's per-build cache-bust works; a bare compose build leaves
> `BUILD_ID=dev` → stale editor assets can be served after a redeploy.

**Access the admin panel.** Open `http://localhost:8088/admin` → the nginx BasicAuth prompt → sign in with
**`admin` / `123`** (from `nginx/htpasswd`). Create end-user accounts there. To sign in to the SPA as the
administrator, use **`admin@example.com` / `admin123`** (set by `make deploy`); passwordless magic-link
sign-in also works — in dev the link is in `make logs`.

> Port 8088 is used because 80/8080 were taken on the dev host. To move it, change `PUBLIC_ORIGIN` in
> `.env` **and** the nginx port mapping in `docker-compose.yml` together (the editor's `server_name`
> must include the public port).

### Rebuild after changes (what you edited → how to rebuild)
| Edited | Command |
|---|---|
| whole stack | `make up` (or `make restart`) |
| `editor/**` (theme, l10n overrides, Dockerfile, cool-help) | `./scripts/up.sh editor` |
| `frontend/**` (SPA) | `./scripts/up.sh app` |
| `nginx/**` (config is bind-mounted) | `docker compose up -d --force-recreate nginx` |
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
