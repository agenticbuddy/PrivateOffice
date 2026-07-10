# PrivateOffice — полный список изменений редактора (Collabora Online)

Всё, что мы меняем в CO относительно апстрима — переводы, стили, ребренд, код-фиксы, приватность, кэш.
Источники: `editor/manifests/patchset.json` (каталог единиц), `editor/patches/*` (browser-патчи),
`editor/l10n/**`, `editor/branding-privateoffice.css`, `editor/Dockerfile.online`, `docker-compose.yml`.

---

## 0. На чём построено (пин)
- **Base image:** `collabora/code@sha256:75859…` = CODE **26.04.1-4**. Движок LibreOffice — **бинарь базового образа** (НЕ из исходников).
- **Collabora Online** (coolwsd + browser-бандл) — собирается **ИЗ ИСХОДНИКОВ** `online.mirror @ cp-26.04.1-4` против движка базы.
- **Сборка:** `editor/Dockerfile.online` (боевая, from-source) · `editor/Dockerfile` (stopgap, патчит готовый образ).
- 22 UI-локали · приложения **Writer / Calc / Impress**. Пины — `editor/manifests/upstream.json`.

---

## 1. Локализация (переводы)
Строка чинится в том слое, по которому она **рендерится** (клиент `_()` / сервер `.ui`→`.mo` / UNO-метка).

| Слой | Файл → куда мержится | Что покрывает | Объём (ru) |
|---|---|---|---|
| Клиент `_()` | `editor/l10n/overrides/client/<lang>.json` → `ui-<lang>.json` | лента, меню, тултипы, имена фигур/команд/диаграмм, отслеживание изменений, спарклайны, AI-строки, CSV-импорт | **1287** ключей |
| UNO-метки | `editor/l10n/overrides/uno/ru.json` → `uno/ru.json` | метки команд (Таблица, Вставить таблицу) | 2 |
| Серверные `.ui` (core) | `editor/l10n/overrides/core/ru/sc.po` → `sc.mo` (gettext) | «Создать таблицу»; боковая панель «Table Style Options» + «Категория»; «Проверка данных → Действие при ошибке» | 23 записи |
| Справка горячих клавиш | `editor/l10n/help/ru.json` → `editor/cool-help.ru.html` → `dist/cool-help.html` | весь справочник клавиш | 527 строк |

Другие языки (client-оверрайды): ar 11, ja 8, ko 7, pt_BR 8, tr 6, по 1 в cs/fr/he/it/uk/vi.

**Browser-патчи, которые чинят ПУТЬ РЕНДЕРА** (иначе перевод есть в каталоге, но на экране английский):
- **0001** `Definitions.Menu.ts` — локализованные имена функций в дропдаунах ленты для всех локалей; чинит И отображение, И вставку (RU-ядро принимает только локализованное имя). Данные: `editor/po-funcnames.js` (генерит `scripts/build-l10n-funcnames.py`).
- **0004** `Widget.Listbox.ts` — локализованные имена стилей ячеек (сайдбар «Стили» + дропдаун условного форматирования). Данные: `editor/po-stylenames.js`.
- **0005** `Widget.IconView.ts` — локализованные имена тем документа (галерея «Темы»). Данные: `editor/po-themenames.js` (вручную).

**Итог:** видимый UI = **0 непереведённых** `_()`-строк. Английскими остаются только имена-форматы (A4, B5 (ISO), Markdown (.md), Legal, Letter) — международные обозначения, не переводятся.

---

## 2. Стили / дизайн (тема)
- `editor/branding-privateoffice.css` (~1478 строк) сворачивается в `bundle.css` при сборке (**PO-THEME-001**); гейт — `editor/po-toggle.js` через `?po_design` → атрибут `data-po` (правильно на первом кадре, CSP-safe).
- **Три дизайна:** `classic` (сток) · `glass` (зелёный, ~219 правил) · `glass2` (синий `#2563d9`, ~223 правила).
- **Покрытие:** лента, меню, попапы, диалоги, боковая панель, пикеры, тултипы, автофильтр.
- **Конкретные стиль-фиксы** (из истории): комбобокс = одно поле (убрать двойную рамку/узкий фокус); скруглённые accent-пилюли дропдаунов ленты; outlined-выделение тумблеров сайдбара; переключатель режима (де-грей + акцент); popup-overlay fix (убрать backdrop-filter с ленты); **автофильтр — мягкое accent-выделение вместо тяжёлой заливки (#58)**.

---

## 3. Ребрендинг
- «Collabora …» → «**PrivateOffice**» в отображаемых строках/копирайте (**PO-BRAND-003**, sed по границе слова — чтобы не ломать «Collaborative»).
- Логотипы → `editor/po-logo.svg` (About-вордмарк, шапка) (**PO-ASSET-008**).
- Serve-time плейсхолдеры `%PRODUCT_BRANDING_NAME/URL%` → PrivateOffice / about:blank; экран welcome удалён (**PO-BRAND-011**).
- `--o:product_name=PrivateOffice` (compose).

---

## 4. Приватность / no phone-home
- Все апстрим-URL → `about:blank` (**PO-URL-007**): header-logo, release notes, docs, proxy.
- `--o:help_url=` пусто → скрыты все внешние кнопки справки. **0006** `FormulaErrorHelpSection.ts` — убраны внешние ссылки Collabora (Forum / Report an issue / Latest Updates / Send Feedback / help по ошибке формулы).
- `--o:fetch_update_check=0`, `--o:allow_update_popup=false` — без проверки обновлений/попапов.
- `--o:welcome`/feedback/buyproduct — пусто.

---

## 5. Код-фиксы (функциональные баги)
**Browser-патчи** (в исходнике, `git apply` до `configure`):
- **0002** `Widget.TreeView.ts` — `row -1` = «снять выделение», а не ошибка (убирает спам `console.warn`).
- **0003** `Control.Notebookbar.js` — вкладка «Формулы» остаётся активной после вставки функции (+ фикс опечатки имени).

**Post-build seds по `bundle.js`:**
- **PO-CODE-004** — «More options for {1}» через каталог (не сырой `concat`, не течёт id контрола).
- **PO-CODE-005** — «Open {name}» через каталог (не течёт англ. фрагмент / порядок слов).
- **PO-CODE-010** — `getImageURL` guard: пустое имя иконки → `''` (нет 404 по `images/`).
- **PO-ASSET-009** — досоздан `lc_pastespecial.svg` (апстрим не кладёт → 404 + пустая иконка).
- **#61** — `Intl.RelativeTimeFormat` стиль `narrow`→`short`: тултип «Последнее сохранение: N мин. назад» вместо «-36 мин» (narrow даёт знаковое число для ru/fr).
- **PO-CSP-002** — удалён мёртвый inline dark-theme `<script>` из cool.html (нарушал CSP, никогда не исполнялся).

---

## 6. Кэш / сборка
- `./scripts/up.sh` проставляет `BUILD_ID=<git short sha>` (или `<sha>-dirty` при незакоммиченном).
- **PO-CACHE-012** — ETag через `ver_suffix = BUILD_ID` в `coolwsd.xml`.
- **PO-CACHE-013** — `?b=BUILD_ID` на все `*.css/js/json`, что упомянуты в cool.html.
- **PO-BRAND-011** — свой пустой (инертный) `branding.js`, инжектится своим тегом → попадает под `?b=` (не un-cache-busted serve-time инжект coolwsd).
- **#66** — свой `<link>` для `branding.css` вместо serve-time плейсхолдера `%BRANDING_CSS%` → тоже под `?b=`. Устранил баг: устаревший закэшированный branding.css нёс `.jsdialog-window{overflow:hidden}` и клипал диалоги (чекбоксы не нажимались).

---

## 7. Механизмы (как устроено)
- **`editor/Dockerfile.online`** — from-source: `git clone online.mirror@cp-26.04.1-4` → `git apply editor/patches/*` → `configure` → build → мерж client/uno-оверрайдов в каталоги → core `.po`→`.mo` (gettext) до systemplate → seds (ребренд/URL/код) → замена логотипов → `COPY cool-help.ru.html` → cache-bust (`ver_suffix`, `?b=`).
- **`editor/patches/*.patch`** (**PO-SRC-014**) — правки исходника CO; при re-pin **rebase** (иначе `git apply` валит сборку — это сигнал).
- **`editor/l10n/overrides/`** — данные переводов (client / uno / core).
- **`editor/po-*.js`** — parse-blocking head-скрипты: `po-toggle` (тема) + `po-funcnames`/`po-stylenames`/`po-themenames` (данные для патчей 0001/0004/0005).
- **`editor/manifests/`** — `upstream.json` (пины) + `patchset.json` (каждая единица как типизированный юнит).

---

## Приложение: каталог единиц (`patchset.json`)
| ID | Тип | Что |
|---|---|---|
| PO-THEME-001 | theme | Тема в bundle.css + гейт `po-toggle.js` |
| PO-CSP-002 | code-fix | Удалить мёртвый dark-theme `<script>` |
| PO-BRAND-003 | rebrand | Collabora → PrivateOffice (строки/копирайт) |
| PO-CODE-004 | code-fix | «More options for {1}» через каталог |
| PO-CODE-005 | code-fix | «Open {name}» через каталог |
| PO-L10N-006 | translation-data | Инъекции клиентского каталога (12 языков) → мигрировано в overrides |
| PO-URL-007 | privacy | URL → about:blank |
| PO-ASSET-008 | asset | Логотипы → PrivateOffice |
| PO-ASSET-009 | asset | Досоздать `lc_pastespecial.svg` |
| PO-CODE-010 | code-fix | `getImageURL` guard |
| PO-BRAND-011 | privacy | Serve-time бренд-плейсхолдеры + свой branding.js + убрать welcome |
| PO-CACHE-012 | cache | ETag = `ver_suffix = BUILD_ID` |
| PO-CACHE-013 | cache | `?b=BUILD_ID` на ассеты cool.html |
| PO-SRC-014 | code-fix | Механизм source-патчей |
| PO-QA-015 | qa | Снимок несмерженного source-каталога |
| PO-SRC-016 | code-fix | (0001) имена функций в дропдаунах ленты |
| PO-SRC-017 | code-fix | (0002) TreeView row -1 = clear-selection |
| PO-SRC-018 | code-fix | (0003) держать вкладку «Формулы» |
| PO-SRC-019 | code-fix | (0004) имена стилей ячеек |
| PO-SRC-020 | code-fix | (0005) имена тем документа |
| PO-SRC-021 | code-fix | (0006) убрать внешние ссылки справки |

> **NB:** несколько единиц этой сессии ещё НЕ каталогизированы в `patchset.json` (branding.css cache-bust #66, RelativeTimeFormat narrow→short #61, `cool-help.ru.html` #48, расширения `sc.po` для сайдбара/валидации, автофильтр #58). При желании синхронизирую `patchset.json`.
