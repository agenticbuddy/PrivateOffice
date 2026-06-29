# PrivateOffice Workspace

Self-hosted, internal document workspace built around **PrivateOffice**.
Admin-provisioned users, a shared folder/file tree with `owner`/`editor`/`reader`
sharing, in-browser editing, per-viewer localized UI.

- Architecture & contracts: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- Design system: [`DESIGN.md`](DESIGN.md)
- Languages: [`docs/LANGUAGES.md`](docs/LANGUAGES.md)

## Stack

nginx · FastAPI (Python) + Vue 3 (TypeScript) · PostgreSQL · a self-hosted editor (CODE) · MinIO,
all in Docker Compose on a single `http://localhost` origin.

## Quick start

```bash
cp deploy/.env.example .env          # compose reads .env from the repo root
docker compose up -d --build         # builds the SPA into the app image
# app:   http://localhost:8088
# admin: http://localhost:8088/admin   (BasicAuth  admin / 123)
```

A default admin user (`admin@example.com`) is bootstrapped on first boot. Create
end-user accounts from the admin area, then sign them in by password or by the
generated passwordless magic link.

> Port 8088 is used because 80/8080 were taken on the dev host. Change `PUBLIC_ORIGIN`
> in `.env` and the nginx port mapping in `docker-compose.yml` together if you move it
> (the editor's `server_name` must include the public port).

## Development

```bash
# backend (bind-mounted, hot-reload) — run the test suite:
docker compose exec -w /app/backend app pytest -q

# frontend changes are baked into the image — rebuild to apply:
docker compose build app && docker compose up -d app

# end-to-end (admin + user cycles) and the 22-language sweep:
cd e2e && npm install && npx playwright install chromium
npx playwright test                  # admin + user cycles + language sweep
npx playwright test tests/lang-sweep.spec.ts   # just the language sweep
```

See [`docs/LANGUAGE_REPORT.md`](docs/LANGUAGE_REPORT.md) for the 22-locale UI report.
