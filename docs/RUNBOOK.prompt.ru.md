# PrivateOffice — RUNBOOK (развернуть · править · проверить)

> Копия инструкций 1–2 в промпт-стиле: императив, ноль воды, таблицы, ЖЁСТКИЕ ПРАВИЛА капсом.

КОНТЕКСТ: self-hosted документ-редактор. Collabora (собирается ИЗ ИСХОДНИКОВ) + FastAPI/Vue SPA за nginx, Postgres, MinIO. Единая точка входа — порт **8088**.

---

## 1 · РАЗВЕРНУТЬ С НУЛЯ

ТРЕБОВАНИЯ: Docker + Docker Compose v2 + git. Порт 8088 свободен. Первый билд редактора ≈15–25 мин (из исходников), далее — из кэша.

ШАГИ:
1. `git clone <url> xls && cd xls`
2. Создать `.env` в корне (он `.gitignore`d — в репо его НЕТ). Ключи → таблица ниже.
3. `./scripts/up.sh` — собрать + поднять весь стек.
4. http://localhost:8088 → войти по magic-link (dev: ссылка в `docker compose logs app`) → задать пароль.

`.env` — минимум:
| Ключ | Пример |
|---|---|
| PUBLIC_ORIGIN | http://localhost:8088 |
| POSTGRES_USER/PASSWORD/DB | workspace / workspace / workspace |
| DATABASE_URL | postgresql+asyncpg://workspace:workspace@postgres:5432/workspace |
| MINIO_ROOT_USER/PASSWORD | minio / minio12345 |
| MINIO_ENDPOINT · BUCKET | http://minio:9000 · documents |
| EDITOR_INTERNAL_URL | http://editor:9980 |
| WOPI_HOST_URL | http://app:8000 |
| SECRET_KEY | `<длинная случайная строка>` |
| BOOTSTRAP_ADMIN_EMAIL/NAME | admin@example.com / Администратор |

ЗАПРЕЩЕНО: `docker compose up --build` напрямую. ТОЛЬКО `./scripts/up.sh` — он проставляет `BUILD_ID` (кэш-баст редактора). Иначе `BUILD_ID=dev` → браузер отдаёт СТАРЫЕ ассеты редактора.

ПЕРЕСБОРКА (правил → пересобери):
| editor/** | `./scripts/up.sh editor` |
| frontend/** | `./scripts/up.sh app` |
| nginx/** | `docker compose up -d nginx` |
| backend/** | НИЧЕГО — hot-reload |

---

## 2 · СЛОИ — ЧИНИТЬ В ИСТОЧНИКЕ

ПРАВИЛО: правь РЕАЛЬНЫЙ слой. НЕ клади override-стили/патчи ПОВЕРХ как замену починке.
ПРИНЦИП РЕНДЕРА: строка идёт клиентом (`_()`) ИЛИ сервером (`.ui`→`.mo`) ИЛИ как UNO-метка. Слой = ПУТЬ РЕНДЕРА, не место на экране. Не тот слой → перевод в каталоге есть, экран английский.

| Зона | Слой (файл) | Доезд до UI |
|---|---|---|
| Тема / дизайн / выделения / glass | `editor/branding-privateoffice.css` (scoped `html[data-po=glass\|glass2]`) | → `bundle.css` при сборке |
| Клиентские строки (`_()`: лента, меню, тултипы) | `editor/l10n/overrides/client/<lang>.json` | → `ui-<lang>.json` |
| UNO-метки команд | `editor/l10n/overrides/uno/<lang>.json` | → `uno/<lang>.json` |
| Серверные диалоги / боковые панели (`.ui`) | `editor/l10n/overrides/core/<lang>/<module>.po` | → движковый `<module>.mo` (gettext) до systemplate |
| Справка горячих клавиш | `editor/l10n/help/ru.json` → `editor/cool-help.ru.html` | `COPY` → `dist/cool-help.html` |
| Ребренд · URL · `?b=` · патчи · код-фиксы | `editor/Dockerfile.online` (seds по `bundle.js`/`cool.html`, `git apply`) | правит собранные ассеты |
| SPA + тексты SPA | `frontend/src/**` · `frontend/src/i18n/messages/<locale>.json` | сборка SPA |
| Бэкенд (WOPI, шаблоны, уведомления) | `backend/app/**` | hot-reload |

СДЕЛАНО В ЭТУ СЕССИЮ (слой → чем проверено):
| Работа | Слой | Проверка |
|---|---|---|
| Русификация 100% | client/ru.json · core/ru/sc.po · l10n/help/* | покрытие по `bundle.js` = 0 непереведённых + рендер |
| #66 чекбокс не нажимался | `Dockerfile.online` (кэш-баст `branding.css`) | `elementFromPoint` над чекбоксом = чекбокс |
| #61 «-36 мин» | `Dockerfile.online` (sed `narrow`→`short` в `bundle.js`) | тултип «N мин. назад» |
| #58 автофильтр | `branding-privateoffice.css` | инъекция + `getComputedStyle` |

---

## 3 · ПРОВЕРКА — RENDER = ЕДИНСТВЕННАЯ ИСТИНА

| Метод | Когда | Как |
|---|---|---|
| Playwright `e2e/` | всегда для UI | `cd e2e && npm i && npm test` |
| Инъекция + `getComputedStyle` | модалки/меню Collabora (НЕ скриншотятся) | тест-элемент с классами в iframe → читать computed |
| Покрытие l10n | доказать полноту перевода | `_("...")` из `bundle.js` − ключи `ui-ru.json` → 0 (кроме имён-форматов) |
| Кэш-баст | после правок editor | `?b=<токен>` == HEAD |
| Backend pytest | правки backend | `docker compose exec -T -w /app/backend app pytest -q` |

---

## ЖЁСТКИЕ ПРАВИЛА
- КОММИТЬ перед проверкой редактора. Незакоммичено → токен `-dirty` → стейл-кэш.
- `?b=<токен>` отданных ассетов ДОЛЖЕН == git HEAD.
- КАТАЛОГ ≠ РЕНДЕР. Верь только экрану.
- Модалки Collabora НЕ скриншотятся → только `getComputedStyle`.
- Имена-форматы (A4, B5 (ISO), Markdown (.md)) НЕ переводить — международные обозначения.
- ЗАПУСК только `./scripts/up.sh` (никогда `docker compose up --build`).
