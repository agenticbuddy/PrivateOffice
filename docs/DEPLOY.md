# Развёртывание с нуля / Deploy from scratch

Инструкция 1 из 2. Простыми словами, кратко. / Instruction 1 of 2. Plain language, short.

---

## 🇷🇺 По-русски

### Что нужно заранее
- **Docker** и **Docker Compose v2**, **git**.
- Свободный порт **8088** (весь стек ходит через него).
- Первая сборка редактора идёт из исходников Collabora — это **долго** (≈15–25 мин один раз), потом быстро из кэша.

### Шаги
1. **Склонировать** репозиторий и войти в папку:
   ```bash
   git clone <repo-url> xls && cd xls
   ```
2. **Создать файл `.env`** в корне (он в `.gitignore`, поэтому его нет в репозитории). Нужные ключи:
   ```
   PUBLIC_ORIGIN=http://localhost:8088
   POSTGRES_USER=workspace
   POSTGRES_PASSWORD=workspace
   POSTGRES_DB=workspace
   DATABASE_URL=postgresql+asyncpg://workspace:workspace@postgres:5432/workspace
   MINIO_ROOT_USER=minio
   MINIO_ROOT_PASSWORD=minio12345
   MINIO_ENDPOINT=http://minio:9000
   MINIO_BUCKET=documents
   EDITOR_INTERNAL_URL=http://editor:9980
   EDITOR_USERNAME=admin
   EDITOR_PASSWORD=admin
   WOPI_HOST_URL=http://app:8000
   SECRET_KEY=<любая-длинная-случайная-строка>
   SESSION_COOKIE=po_session
   STATIC_DIR=/app/static
   BOOTSTRAP_ADMIN_EMAIL=admin@example.com
   BOOTSTRAP_ADMIN_NAME=Администратор
   ```
   Пароли/секреты замените на свои. Значения выше — рабочий пример для локального запуска.
3. **Поднять стек** одной командой:
   ```bash
   ./scripts/up.sh
   ```
   Она собирает редактор из исходников + поднимает postgres, minio, app (бэкенд+SPA), nginx.
   **ВАЖНО:** запускать именно `./scripts/up.sh`, **не** `docker compose up --build` напрямую — скрипт проставляет `BUILD_ID` (кэш-баст редактора), иначе браузер может отдавать старые ассеты редактора.
4. **Открыть** http://localhost:8088.
5. **Первый вход:** аккаунт администратора создаётся автоматически из `BOOTSTRAP_ADMIN_EMAIL`. Входим по magic-link со страницы входа (в dev ссылку/токен смотрите в логах: `docker compose logs app`), затем задаём пароль в профиле.

### Пересборка после правок (что менять → чем пересобирать)
| Что правили | Команда |
|---|---|
| `editor/**` (тема, l10n-оверрайды, Dockerfile, cool-help) | `./scripts/up.sh editor` |
| `frontend/**` (SPA) | `./scripts/up.sh app` |
| `nginx/**` | `docker compose up -d nginx` |
| `backend/**` | ничего — авто-перезагрузка (bind-mount) |

### Проверка, что всё живо
- Бэкенд-тесты: `docker compose exec -T -w /app/backend app pytest -q`
- E2E (Playwright): `cd e2e && npm install && npm test`
- Открыть http://localhost:8088, создать документ, убедиться, что редактор открывается и русифицирован.

---

## 🇬🇧 In English

### Prerequisites
- **Docker** + **Docker Compose v2**, **git**.
- Free port **8088** (the whole stack is served through it).
- The editor's first build compiles Collabora from source — this is **slow** (~15–25 min once), then fast from cache.

### Steps
1. **Clone** and enter the folder:
   ```bash
   git clone <repo-url> xls && cd xls
   ```
2. **Create a `.env`** file in the root (it is `.gitignore`d, so not in the repo). Required keys:
   ```
   PUBLIC_ORIGIN=http://localhost:8088
   POSTGRES_USER=workspace
   POSTGRES_PASSWORD=workspace
   POSTGRES_DB=workspace
   DATABASE_URL=postgresql+asyncpg://workspace:workspace@postgres:5432/workspace
   MINIO_ROOT_USER=minio
   MINIO_ROOT_PASSWORD=minio12345
   MINIO_ENDPOINT=http://minio:9000
   MINIO_BUCKET=documents
   EDITOR_INTERNAL_URL=http://editor:9980
   EDITOR_USERNAME=admin
   EDITOR_PASSWORD=admin
   WOPI_HOST_URL=http://app:8000
   SECRET_KEY=<any-long-random-string>
   SESSION_COOKIE=po_session
   STATIC_DIR=/app/static
   BOOTSTRAP_ADMIN_EMAIL=admin@example.com
   BOOTSTRAP_ADMIN_NAME=Administrator
   ```
   Replace passwords/secrets with your own. The values above are a working local example.
3. **Bring up the stack** with one command:
   ```bash
   ./scripts/up.sh
   ```
   It builds the editor from source and starts postgres, minio, app (backend + SPA), nginx.
   **IMPORTANT:** use `./scripts/up.sh`, **not** `docker compose up --build` directly — the script stamps `BUILD_ID` (editor cache-bust); without it the browser may serve stale editor assets.
4. **Open** http://localhost:8088.
5. **First login:** the admin account is auto-created from `BOOTSTRAP_ADMIN_EMAIL`. Log in via the magic-link on the sign-in page (in dev, find the link/token in logs: `docker compose logs app`), then set a password in your profile.

### Rebuild after changes (what you edited → how to rebuild)
| Edited | Command |
|---|---|
| `editor/**` (theme, l10n overrides, Dockerfile, cool-help) | `./scripts/up.sh editor` |
| `frontend/**` (SPA) | `./scripts/up.sh app` |
| `nginx/**` | `docker compose up -d nginx` |
| `backend/**` | nothing — hot-reload (bind-mount) |

### Health check
- Backend tests: `docker compose exec -T -w /app/backend app pytest -q`
- E2E (Playwright): `cd e2e && npm install && npm test`
- Open http://localhost:8088, create a document, confirm the editor opens and is in Russian.
