# Architecture — PrivateOffice Workspace

> Internal, self-hosted office workspace built around **an embedded self-hosted editor**.
> Reference seriousness: **Google Drive**. Visual language: between **Asana** and **Monday**.

## 1. Goal & scope

A small-team document workspace where:

- Users are provisioned **only by an administrator**.
- Each user has a private tree of **folders & files**.
- Any node a user **owns** can be **shared** with other users at three levels:
  `owner` (full control, can be many) · `editor` (read + edit) · `reader` (read only).
- Files of **the editor-supported formats** can be created or uploaded and edited in the
  browser through the embedded editor.
- The UI is **localized per viewer**: the interface always renders in the locale of
  the person looking at it; new documents are created in the locale of their creator.
- Works on **wide desktop screens and modern mobile phones**.

## 2. Container topology (Docker Compose)

Single public origin on `http://localhost` (development profile). `nginx` is the only
container that publishes a host port.

```
                         ┌──────────── browser ────────────┐
                         │  Vue SPA  +  <iframe> the editor editor  │
                         └───────┬───────────────┬──────────┘
                    http://localhost (:80)        │ websocket /cool
                                 │                │
                          ┌──────▼────────────────▼──────┐
                          │           nginx               │  (reverse proxy, single origin)
                          │  /            → app (SPA)      │
                          │  /api /wopi   → app (FastAPI)  │
                          │  /hosting /browser /cool → the editor  │
                          │  /admin/*     → app + BasicAuth│
                          └───┬───────────────────┬───────┘
                     ┌────────▼──────┐      ┌──────▼─────────┐
                     │  app          │      │  editor     │
                     │  FastAPI +    │◄─────┤  (CODE)        │
                     │  built SPA    │ WOPI │  coolwsd       │
                     └──┬────────┬───┘      └────────────────┘
                ┌───────▼──┐  ┌──▼────────┐
                │ postgres │  │  minio    │  (S3 object store: file bytes & versions)
                └──────────┘  └───────────┘
```

| Container  | Image (base)                | Role |
|------------|-----------------------------|------|
| `nginx`    | `nginx:1.27-alpine`         | Reverse proxy, single entry point, BasicAuth on `/admin`, WS upgrade for the editor |
| `app`      | multi-stage: `node` → `python:3.12-slim` | FastAPI backend (`/api`, `/wopi`) **and** serves built Vue SPA at `/` |
| `postgres` | `postgres:16-alpine`        | Relational metadata (users, nodes, shares, versions, audit) |
| `editor`| `collabora/code:latest`     | Document engine, WOPI client |
| `minio`    | `minio/minio:latest`        | S3-compatible object storage for file bytes & version snapshots |

> The `app` container deliberately bundles backend + built frontend (per project
> constraint "контейнер с бекендом и фронтендом"). The SPA is built in a node stage
> and copied into the python image; FastAPI serves it as static files with SPA
> fallback to `index.html`.

## 3. The editor reachability model (the critical part)

The editor has three independent network relationships. Getting them right is the whole game.

1. **Browser → the editor** (load editor assets + websocket). Proxied through nginx so it is
   the **same origin** as the SPA: `http://localhost/browser/...`, `ws://localhost/cool/...`.
   This avoids cross-origin / mixed-content issues and lets cookies/PostMessage stay simple.
2. **the editor → app** (WOPI callbacks: CheckFileInfo, GetFile, PutFile). Happens **inside the
   compose network**, never via the browser. `WOPISrc = http://app:8000/wopi/files/{id}`.
   The browser never contacts this URL.
3. **app → the editor** (server-side discovery). The app fetches `http://editor:9980/hosting/discovery`
   once, parses `urlsrc`, and **rewrites the host** to the public origin (`http://localhost`)
   before handing the iframe URL to the browser.

Editor configuration (env on the `editor` container):

- `aliasgroup1=http://app:8000` — allow the WOPI host.
- `extra_params=--o:ssl.enable=false --o:ssl.termination=false` — plain HTTP for localhost dev.
- `server_name=localhost` — public name the editor believes it is served under (behind proxy).
- `username`/`password` — the editor admin console.

`CheckFileInfo` returns `PostMessageOrigin: "http://localhost"` so the editor posts
events back to our SPA window.

## 4. Component contracts

All app endpoints are under `/api` (JSON) or `/wopi` (WOPI protocol). Auth for `/api`
is a **httpOnly cookie session**; auth for `/admin` adds an **nginx BasicAuth** gate
(`admin` / `123`) on top. WOPI auth is the per-open `access_token`.

### 4.1 Auth & session — `/api/auth`

| Method | Path | Body | Result |
|--------|------|------|--------|
| POST | `/api/auth/login` | `{email, password}` | sets session cookie, `200 {user}` |
| POST | `/api/auth/magic/{token}` | – | consumes magic-link, sets session, `200 {user}` |
| POST | `/api/auth/password` | `{password}` | set/replace own password (session required) |
| POST | `/api/auth/logout` | – | clears session |
| GET  | `/api/auth/me` | – | `200 {user}` current session user |
| PATCH| `/api/auth/me` | `{locale}` | update own UI locale |

`user = {id, email, full_name, locale, is_active, has_password, is_admin}`.

### 4.2 Admin — `/api/admin` (behind BasicAuth)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/admin/users` | list users + summary counts |
| POST | `/api/admin/users` | create user `{email, full_name, locale}` |
| GET | `/api/admin/users/{id}` | full bio + statistics (files, folders, shares, history) |
| PATCH | `/api/admin/users/{id}` | update bio / locale / active |
| POST | `/api/admin/users/{id}/magic-link` | generate a passwordless login link |
| POST | `/api/admin/users/{id}/password` | set a password for the user |
| DELETE | `/api/admin/users/{id}/nodes/{nodeId}` | delete a user's folder/file |

### 4.3 Nodes (folders & files) — `/api/nodes`

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/nodes?parent={id}` | list children visible to me (owned + shared) |
| GET | `/api/nodes/shared-with-me` | nodes shared with me at root |
| POST | `/api/nodes/folder` | create folder `{name, parent_id}` |
| POST | `/api/nodes/file` | create empty file `{name, parent_id, format}` (format∈docx/xlsx/pptx) |
| POST | `/api/nodes/upload` | multipart upload `{parent_id, file}` (format validated) |
| GET | `/api/nodes/{id}` | node detail + my effective role |
| PATCH | `/api/nodes/{id}` | rename / move |
| DELETE | `/api/nodes/{id}` | delete (owner only) |
| GET | `/api/nodes/{id}/download` | download current bytes |
| GET | `/api/nodes/{id}/versions` | version history (snapshots) |
| GET | `/api/nodes/{id}/audit` | audit trail for the node |

### 4.4 Sharing — `/api/nodes/{id}/shares`

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/nodes/{id}/shares` | list grants |
| PUT | `/api/nodes/{id}/shares` | upsert `{user_id, role}` (owner only) |
| DELETE | `/api/nodes/{id}/shares/{userId}` | revoke |
| GET | `/api/users` | directory of all users (available to everyone, for sharing) |

### 4.5 Editor session — `/api/editor`

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/editor/{nodeId}` | returns `{iframe_url, access_token, access_token_ttl, lang}` |

`iframe_url` = rewritten discovery `urlsrc` + `WOPISrc` (internal app URL) + `lang`
(viewer's locale). The SPA renders a POST form into the iframe with the token.

### 4.6 WOPI — `/wopi` (consumed by the editor only)

| Method | Path | WOPI op |
|--------|------|---------|
| GET | `/wopi/files/{id}` | CheckFileInfo → file metadata + permissions JSON |
| GET | `/wopi/files/{id}/contents` | GetFile → raw bytes |
| POST | `/wopi/files/{id}/contents` | PutFile → save bytes, create new version, audit |

Token is validated on every WOPI call: it encodes `(user_id, node_id, can_write, exp)`
signed server-side; permission (`UserCanWrite`) is derived from the user's effective
role on the node at open time and re-checked on PutFile.

## 5. Database schema (PostgreSQL)

```
users
  id            uuid pk
  email         text unique not null
  full_name     text not null
  locale        text not null default 'en'        -- BCP-47 UI locale
  bio           text
  password_hash text null                          -- argon2; null => passwordless only
  is_admin      boolean not null default false
  is_active     boolean not null default true
  created_at    timestamptz default now()

magic_links
  token       text pk            -- url-safe random
  user_id     uuid fk users
  expires_at  timestamptz not null
  used_at     timestamptz null

sessions
  id          text pk            -- cookie value (random)
  user_id     uuid fk users
  expires_at  timestamptz not null
  created_at  timestamptz default now()

nodes                              -- unified folder/file tree
  id            uuid pk
  type          text not null      -- 'folder' | 'file'
  name          text not null
  parent_id     uuid fk nodes null -- null => user root level
  created_by    uuid fk users
  -- file-only fields:
  co_format     text null          -- 'docx','xlsx','pptx','odt',... mime-derived
  mime          text null
  storage_key   text null          -- MinIO object key of current bytes
  size          bigint null
  current_version_id uuid null
  creator_locale text null         -- locale doc was created in
  created_at    timestamptz default now()
  updated_at    timestamptz default now()

shares                             -- explicit grants on a node
  node_id   uuid fk nodes
  user_id   uuid fk users
  role      text not null          -- 'owner' | 'editor' | 'reader'
  created_at timestamptz default now()
  pk (node_id, user_id)

file_versions                      -- content snapshots (history)
  id          uuid pk
  node_id     uuid fk nodes
  storage_key text not null        -- MinIO key of this snapshot
  size        bigint not null
  author_id   uuid fk users null
  created_at  timestamptz default now()

audit_log                          -- who/what/when
  id        bigserial pk
  actor_id  uuid fk users null
  node_id   uuid fk nodes null
  action    text not null          -- create_file, upload, edit_save, share, unshare, delete, login...
  meta      jsonb
  created_at timestamptz default now()
```

### Permission resolution

A user's **effective role** on a node = the strongest of:
- explicit `shares` grant on the node, OR
- inherited grant from the nearest ancestor folder that has a `shares` row for the user.

`owner > editor > reader`. The node `created_by` user is treated as an implicit `owner`.
Admin endpoints bypass this (operate on any node).

## 6. Storage layout (MinIO)

Single bucket `documents`. Object keys:

- Current bytes:  `nodes/{node_id}/current`
- Version snapshot: `nodes/{node_id}/versions/{version_id}`

On `PutFile`: copy `current` → new version object, then overwrite `current`, insert
`file_versions` row, set `nodes.current_version_id`, write `audit_log(edit_save)`.

## 7. Localization model

- `lang` is decided **per request** from the viewing user's `locale`.
- SPA UI: `vue-i18n`, message catalogs per locale; falls back to `en`.
- the editor editor: the `lang` URL parameter on the iframe = viewer locale → the editor renders its
  own toolbars/menus in that language (CODE ships all UI language packs).
- New documents: stored `creator_locale = creator.locale` (informational; document
  default language for spellcheck follows the editor `allowed_languages`).
- Supported set: see `docs/LANGUAGES.md` (the the editor-supported list; UI translated subset
  + `en` fallback for the rest).

## 8. Testing strategy

- **Contract-first** per block: pytest tests describe the API contract before code.
- Backend: `pytest` + `httpx` AsyncClient against the FastAPI app (sqlite/pg test DB,
  MinIO via a fake/`moto`-style or a real ephemeral minio for integration).
- E2E: **Playwright** drives the real compose stack (admin cycle, user cycle, editor open).
- Language sweep: Playwright loads the app under 20+ locales and screenshots, producing
  a real quality report (`docs/LANGUAGE_REPORT.md`).
