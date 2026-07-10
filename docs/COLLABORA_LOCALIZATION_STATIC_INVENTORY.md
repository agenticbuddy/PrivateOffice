# Статическая инвентаризация локализации Collabora Online

> **Текущее состояние (обновлено 2026-07): русская локализация редактора доведена до 100%.** В видимом UI не осталось непереведённых клиентских `_()`-строк (кроме международных имён-форматов: A4, B5 (ISO), Letter, Markdown (.md) и т.п.). Разбор всех слоёв, единиц и метода проверки — в [`CO-CHANGES.md`](CO-CHANGES.md). **Списки пропусков ниже — исторический базлайн первичного аудита (июнь 2026)**, по которому и достигалось 100%; сохранены как аудит-трейл, а не как текущее состояние.

Область отчета: первый статический этап по активному запущенному образу Collabora. Проверки реального рендера через Playwright/браузер здесь еще нет.

## Область проверки

- Покрытые приложения: Writer, Calc, Impress, а также общий notebookbar builder, который используется этими приложениями.
- Покрытые языки: все 22 языка проекта из `backend/app/services/locales.py`. Английский считается исходным языком; остальные 21 язык проверяются на пропуски.
- Покрытые источники: `bundle.js` из активного контейнера, `l10n/ui-*.json`, `l10n/uno/*.json`, `l10n/locore/*.json`, а также наличие LibreOffice-ресурсов `program/resource/*/LC_MESSAGES/*.mo`. Для слов со скриншотов отдельно сделан точный RU-поиск `msgid` в `.mo`.
- Что еще не покрыто: доказательство, что конкретная подпись реально рендерится в конкретном состоянии браузера. Это второй этап с Playwright.

## Расшифровка сокращений в таблицах

- `ui-json`: браузерный каталог `l10n/ui-<locale>.json`; прямые строки `_()` относятся к этому классу.
- `uno-json`: каталог UNO-команд `l10n/uno/<locale>.json`; подписи `_UNO(...)` относятся к этому классу.
- `locore-json`: браузерный core-каталог Collabora/LibreOffice `l10n/locore/<locale>.json`; это полезный источник перевода, но он не заменяет `ui-*` для прямых `_()` ключей.
- `lo-core-mo`: скомпилированные gettext-ресурсы LibreOffice в `program/resource/<locale>/LC_MESSAGES/*.mo`; используются серверной/core-частью UI и требуют пересборки `.mo` или образа.
- `missing`: английский `msgid` отсутствует в целевом каталоге.
- `same`: `msgid` есть, но значение равно английскому; иногда это нормально для названий, но требует ручной проверки.
- `translated`: в каталоге есть неанглийское значение, отличающееся от `msgid`.

## Краткий итог

- Найдено прямых браузерных ключей notebookbar: 436 уникальных ключей.
- Найдено подписей UNO, на которые ссылается notebookbar: 300 уникальных подписей из 264 уникальных команд.
- Найдено подписей во всей глобальной UNO-карте команд: 813 уникальных подписей.
- Пропуски в прямых `ui-json`: 434 ключа имеют хотя бы один неанглийский язык, где ключ отсутствует или равен английскому.
- Пропуски в используемых `uno-json`: 167 подписей имеют хотя бы один неанглийский язык, где подпись отсутствует или равна английской.
- Пропуски во всей глобальной `uno-json` карте: 414 подписей имеют хотя бы один неанглийский язык, где подпись отсутствует или равна английской.
- Неразрешенные `_UNO(...)` команды в извлеченных сегментах приложений: 54. Их нельзя чинить вслепую; нужен второй этап с рендером или трассировкой источника.

Практическое разделение такое: прямые браузерные подписи `_()` чинят как данные в `editor/l10n/overrides/client/<lang>.json` (их мёрджит deployed-сборка `editor/Dockerfile.online`; `editor/Dockerfile` — stopgap), добавляя недостающие ключи в `ui-*.json`. Подписи `_UNO(...)` и серверные/core-подписи относятся к каталогам LibreOffice/UNO; честное исправление для них означает пересоздание `uno/*.json` или пересборку образа с исправленными `.mo`, а не случайное добавление ключей в `ui-ru.json`.

## Покрытие по приложениям

| Область | Прямые ключи | Полностью закрыты прямые | Прямые с пропусками | UNO-команды | UNO-подписи | Полностью закрыты UNO | UNO с пропусками | Неразрешенные UNO-команды |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Writer | 96 | 0 | 96 | 171 | 218 | 95 | 123 | 19 |
| Calc | 117 | 0 | 117 | 151 | 170 | 82 | 88 | 21 |
| Impress | 94 | 1 | 93 | 122 | 158 | 72 | 86 | 12 |
| Shared builder | 255 | 2 | 253 | 13 | 17 | 5 | 12 | 2 |

## Пропуски по языкам

| Язык | ui missing | ui same | ui translated | используемые UNO missing | используемые UNO same | используемые UNO translated | все UNO missing | все UNO same | все UNO translated |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hi | 410 | 0 | 26 | 156 | 0 | 144 | 362 | 0 | 451 |
| fa | 276 | 1 | 159 | 95 | 0 | 205 | 224 | 0 | 589 |
| th | 434 | 0 | 2 | 23 | 0 | 277 | 46 | 0 | 767 |
| vi | 23 | 3 | 410 | 138 | 0 | 162 | 338 | 0 | 475 |
| ko | 309 | 1 | 126 | 41 | 0 | 259 | 111 | 1 | 701 |
| ar | 210 | 1 | 225 | 44 | 0 | 256 | 109 | 0 | 704 |
| ja | 236 | 2 | 198 | 20 | 0 | 280 | 30 | 0 | 783 |
| pt-BR | 237 | 3 | 196 | 13 | 1 | 286 | 17 | 2 | 794 |
| tr | 175 | 2 | 259 | 22 | 0 | 278 | 39 | 1 | 773 |
| ru | 164 | 2 | 270 | 13 | 0 | 287 | 17 | 0 | 796 |
| fr | 49 | 32 | 355 | 2 | 9 | 289 | 2 | 23 | 788 |
| he | 48 | 1 | 387 | 18 | 0 | 282 | 37 | 0 | 776 |
| it | 40 | 11 | 385 | 13 | 2 | 285 | 17 | 6 | 790 |
| cs | 23 | 8 | 405 | 13 | 1 | 286 | 17 | 7 | 789 |
| nl | 0 | 16 | 420 | 13 | 8 | 279 | 17 | 12 | 784 |
| id | 1 | 9 | 426 | 13 | 3 | 284 | 17 | 6 | 790 |
| pl | 0 | 6 | 430 | 13 | 2 | 285 | 17 | 3 | 793 |
| es | 1 | 3 | 432 | 15 | 0 | 285 | 20 | 1 | 792 |
| de | 0 | 20 | 416 | 2 | 5 | 293 | 2 | 11 | 800 |
| uk | 0 | 3 | 433 | 13 | 0 | 287 | 17 | 0 | 796 |
| zh-CN | 0 | 0 | 436 | 13 | 0 | 287 | 18 | 0 | 795 |

## Инвентаризация каталогов

| Язык | Направление | ui-ключи | uno-ключи | locore-ключи | LO .mo файлы |
| --- | --- | --- | --- | --- | --- |
| en | ltr | 0 | 0 | 0 | 0 |
| es | ltr | 1438 | 794 | 744 | 30 |
| de | ltr | 1440 | 812 | 746 | 30 |
| fr | ltr | 1179 | 812 | 746 | 30 |
| pt-BR | ltr | 651 | 797 | 746 | 30 |
| ru | ltr | 877 | 797 | 735 | 30 |
| it | ltr | 1277 | 797 | 746 | 30 |
| nl | ltr | 1440 | 797 | 746 | 30 |
| pl | ltr | 1440 | 797 | 746 | 30 |
| uk | ltr | 1409 | 797 | 746 | 30 |
| tr | ltr | 843 | 775 | 745 | 30 |
| cs | ltr | 1201 | 797 | 746 | 30 |
| zh-CN | ltr | 1440 | 796 | 744 | 30 |
| ja | ltr | 601 | 784 | 731 | 30 |
| ko | ltr | 399 | 703 | 638 | 30 |
| hi | ltr | 148 | 452 | 489 | 0 |
| vi | ltr | 1191 | 476 | 528 | 30 |
| id | ltr | 1438 | 797 | 745 | 30 |
| th | ltr | 7 | 768 | 728 | 0 |
| ar | rtl | 679 | 705 | 676 | 30 |
| he | rtl | 1077 | 777 | 703 | 30 |
| fa | rtl | 474 | 590 | 434 | 0 |

## Термины со скриншотов

Эта таблица классифицирует английские слова, видимые на присланных скриншотах Calc. `primary` показывает источник, который надо исправлять первым, если после проверки рендера на втором этапе слово все еще остается английским.

| Термин | primary | прямые попадания в приложениях | попадания в UNO | RU ui | RU uno | RU locore | точный RU msgid в .mo | Рекомендуемый путь исправления |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AutoSum | ui-json | Calc | - | missing | missing | missing | - | Добавлять ключ в `ui-*.json` для нужных языков. |
| Chart | ui-json | Writer, Calc, Impress | - | translated | missing | missing | chart.mo, sfx.mo, svx.mo | Добавлять ключ в `ui-*.json` для нужных языков. |
| Date | ui-json | Writer, Calc, Shared builder | - | translated | translated | translated | chart.mo, cui.mo, dba.mo, frm.mo, pcr.mo, sc.mo, sca.mo, sd.mo, sfx.mo, svx.mo, sw.mo, xsc.mo | Добавлять ключ в `ui-*.json` для нужных языков. |
| Date & Time | ui-json | Calc | - | missing | missing | missing | - | Добавлять ключ в `ui-*.json` для нужных языков. |
| Delete | lo-core-mo | - | - | translated | missing | missing | cui.mo, editeng.mo, sc.mo, sd.mo, sfx.mo, svx.mo, sw.mo | Исправлять или пересобирать LibreOffice `.mo`/`.ui`; патч `ui-*` может ничего не изменить. |
| Financial | ui-json | Calc | - | missing | missing | missing | sc.mo, svx.mo | Добавлять ключ в `ui-*.json` для нужных языков. |
| Formula to Value | uno-json | - | Calc | missing | translated | missing | - | Исправлять или пересобирать UNO/LibreOffice-каталог; патча `ui-*` недостаточно. |
| Function | lo-core-mo | - | - | missing | missing | missing | basctl.mo, sc.mo | Исправлять или пересобирать LibreOffice `.mo`/`.ui`; патч `ui-*` может ничего не изменить. |
| Function Library | ui-json | Calc | - | missing | missing | missing | - | Добавлять ключ в `ui-*.json` для нужных языков. |
| Hyperlink | lo-core-mo | - | - | missing | missing | translated | cui.mo, frm.mo, sc.mo, sd.mo, svx.mo, sw.mo, vcl.mo | Исправлять или пересобирать LibreOffice `.mo`/`.ui`; патч `ui-*` может ничего не изменить. |
| Illustrations | ui-json | Writer, Calc, Impress | - | translated | missing | missing | - | Добавлять ключ в `ui-*.json` для нужных языков. |
| Image | lo-core-mo | - | - | missing | missing | missing | cui.mo, sc.mo, sd.mo, sfx.mo, svx.mo, sw.mo, vcl.mo | Исправлять или пересобирать LibreOffice `.mo`/`.ui`; патч `ui-*` может ничего не изменить. |
| Insert Function | ui-json | Calc | - | missing | missing | missing | - | Добавлять ключ в `ui-*.json` для нужных языков. |
| Line | uno-json | - | Writer, Calc, Impress | missing | translated | missing | chart.mo, cui.mo, sc.mo, svx.mo, sw.mo, vcl.mo | Исправлять или пересобирать UNO/LibreOffice-каталог; патча `ui-*` недостаточно. |
| Logical | ui-json | Calc | - | missing | missing | missing | sc.mo | Добавлять ключ в `ui-*.json` для нужных языков. |
| Lookup & Reference | ui-json | Calc | - | missing | missing | missing | - | Добавлять ключ в `ui-*.json` для нужных языков. |
| Manage | unresolved-static | - | - | missing | missing | missing | - | Нужна проверка рендера или трассировка источника на втором этапе. |
| Math & Trig | ui-json | Calc | - | missing | missing | missing | - | Добавлять ключ в `ui-*.json` для нужных языков. |
| Pivot Calculated Field | unresolved-static | - | - | missing | missing | missing | - | Нужна проверка рендера или трассировка источника на втором этапе. |
| Pivot Table | ui-json | Calc | - | missing | missing | missing | sc.mo | Добавлять ключ в `ui-*.json` для нужных языков. |
| Range | ui-json | Calc | - | missing | missing | missing | flt.mo, pcr.mo, sc.mo, sd.mo, svx.mo, sw.mo | Добавлять ключ в `ui-*.json` для нужных языков. |
| Recalculate | unresolved-static | - | - | missing | missing | missing | - | Нужна проверка рендера или трассировка источника на втором этапе. |
| Refresh range | lo-core-mo | - | - | missing | missing | missing | sc.mo | Исправлять или пересобирать LibreOffice `.mo`/`.ui`; патч `ui-*` может ничего не изменить. |
| Select range | unresolved-static | - | - | translated | missing | missing | - | Нужна проверка рендера или трассировка источника на втором этапе. |
| Set | unresolved-static | - | - | missing | missing | missing | - | Нужна проверка рендера или трассировка источника на втором этапе. |
| Shapes | ui-json | Writer, Calc, Impress | - | translated | missing | translated | sc.mo, sd.mo, sfx.mo, svx.mo, sw.mo | Добавлять ключ в `ui-*.json` для нужных языков. |
| Sparkline | ui-json | Calc | - | translated | missing | missing | - | Добавлять ключ в `ui-*.json` для нужных языков. |
| Table | ui-json | Writer, Calc, Impress | - | translated | missing | translated | cui.mo, dba.mo, pcr.mo, sc.mo, sd.mo, sfx.mo, svx.mo, sw.mo, vcl.mo | Добавлять ключ в `ui-*.json` для нужных языков. |
| Text | ui-json | Writer, Calc, Impress | - | translated | missing | translated | chart.mo, cui.mo, pcr.mo, sc.mo, sca.mo, sd.mo, sfx.mo, svt.mo, sw.mo, vcl.mo | Добавлять ключ в `ui-*.json` для нужных языков. |
| Text Box | lo-core-mo | - | - | missing | missing | missing | fwk.mo, pcr.mo, svx.mo | Исправлять или пересобирать LibreOffice `.mo`/`.ui`; патч `ui-*` может ничего не изменить. |
| Text box | unresolved-static | - | - | missing | missing | missing | - | Нужна проверка рендера или трассировка источника на втором этапе. |
| Time | ui-json | Calc | - | translated | translated | missing | cui.mo, frm.mo, pcr.mo, sc.mo, svx.mo, sw.mo | Добавлять ключ в `ui-*.json` для нужных языков. |
| Update | lo-core-mo | - | - | translated | missing | missing | cui.mo, svx.mo, sw.mo | Исправлять или пересобирать LibreOffice `.mo`/`.ui`; патч `ui-*` может ничего не изменить. |

## Полный индекс пропусков прямых браузерных ключей

Каждая строка ниже — это прямой браузерный `msgid` из `_()`, извлеченный из Writer, Calc, Impress или общего notebookbar builder. В строку попадают только ключи, где хотя бы один неанглийский язык не имеет перевода или оставляет английское значение.

| Msgid | Языки без ключа | Языки со значением как в английском |
| --- | --- | --- |
| EPUB (.epub) | hi, th, fa | es, de, fr, pt-BR, ru, it, nl, pl, uk, tr, cs, ja, ko, id, ar, he |
| Markdown (.md) | es, fr, pt-BR, ru, tr, cs, ja, ko, hi, vi, id, th, ar, he, fa | de, nl, pl |
| Transition Start:  | fr, pt-BR, ru, it, tr, cs, ja, ko, hi, vi, th, ar, he, fa | - |
| Transition End:  | fr, pt-BR, ru, it, tr, cs, ja, ko, hi, vi, th, ar, he, fa | - |
| Set Up | fr, pt-BR, ru, it, tr, cs, ja, ko, hi, vi, th, ar, he, fa | - |
| Scalable Vector Graphics (.svg) | pt-BR, ja, ko, hi, th, fa | fr, it, nl, pl, uk, cs, vi, id |
| Proofing | fr, pt-BR, ru, it, tr, cs, ja, ko, hi, vi, th, ar, he, fa | - |
| Previous Slide | fr, pt-BR, ru, it, tr, cs, ja, ko, hi, vi, th, ar, he, fa | - |
| Present | fr, pt-BR, ru, it, tr, cs, ja, ko, hi, vi, th, ar, he, fa | - |
| Last Slide | fr, pt-BR, ru, it, tr, cs, ja, ko, hi, vi, th, ar, he, fa | - |
| Info | pt-BR, ru, it, tr, ja, ko, hi, th, ar, fa | de, fr, nl, cs |
| Extensions | fr, pt-BR, ru, tr, cs, ja, ko, hi, vi, th, ar, he, fa | id |
| Clone Formatting is active (press Enter on a cell to apply, click again or press Esc to exit) | fr, pt-BR, ru, it, tr, cs, ja, ko, hi, vi, th, ar, he, fa | - |
| Clone Formatting is active (click again or press Esc to exit) | fr, pt-BR, ru, it, tr, cs, ja, ko, hi, vi, th, ar, he, fa | - |
| Clone Formatting (double click to keep active) | fr, pt-BR, ru, it, tr, cs, ja, ko, hi, vi, th, ar, he, fa | - |
| Animation Start:  | fr, pt-BR, ru, it, tr, cs, ja, ko, hi, vi, th, ar, he, fa | - |
| Table Options | fr, pt-BR, ru, tr, cs, ja, ko, hi, vi, th, ar, he, fa | - |
| Start Slide Show | fr, pt-BR, ru, tr, cs, ja, ko, hi, vi, th, ar, he, fa | - |
| Skip All | fr, pt-BR, ru, tr, cs, ja, ko, hi, vi, th, ar, he, fa | - |
| Skip | fr, pt-BR, ru, tr, cs, ja, ko, hi, vi, th, ar, he, fa | - |
| Protection | fr, pt-BR, ru, tr, cs, ja, ko, hi, vi, th, ar, he, fa | - |
| Protect | fr, pt-BR, ru, tr, cs, ja, ko, hi, vi, th, ar, he, fa | - |
| First Slide | fr, pt-BR, ru, tr, cs, ja, ko, hi, vi, th, ar, he, fa | - |
| First | fr, pt-BR, ru, tr, cs, ja, ko, hi, vi, th, ar, he, fa | - |
| Close extension | fr, pt-BR, ru, tr, cs, ja, ko, hi, vi, th, ar, he, fa | - |
| Cell Background | fr, pt-BR, ru, tr, cs, ja, ko, hi, vi, th, ar, he, fa | - |
| Zoom | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | fr, it, nl |
| Waiting for presenter to advance | fr, pt-BR, ru, it, tr, ja, ko, hi, th, ar, he, fa | - |
| View slides as the presenter advances them | fr, pt-BR, ru, it, tr, ja, ko, hi, th, ar, he, fa | - |
| This Presentation | fr, pt-BR, ru, it, tr, ja, ko, hi, th, ar, he, fa | - |
| Stop Following | fr, pt-BR, ru, it, tr, ja, ko, hi, th, ar, he, fa | - |
| Starts a slideshow on every viewer's screen | fr, pt-BR, ru, it, tr, ja, ko, hi, th, ar, he, fa | - |
| Presentation Templates | fr, pt-BR, ru, it, tr, ja, ko, hi, th, ar, he, fa | - |
| Plays inside the document window. Starts at slide 1 | fr, pt-BR, ru, it, tr, ja, ko, hi, th, ar, he, fa | - |
| OK | hi, th | de, fr, pt-BR, it, nl, pl, uk, cs, ja, id |
| Auto Spell Check | fr, pt-BR, ru, it, tr, ja, ko, hi, th, ar, he, fa | - |
| You are on the first slide | fr, pt-BR, ru, tr, ja, ko, hi, th, ar, he, fa | - |
| Variant | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | fr, nl |
| Unlinked citations | fr, pt-BR, ru, it, tr, ja, ko, hi, th, ar, fa | - |
| Table styles are only available in .xlsx files | fr, pt-BR, ru, tr, ja, ko, hi, th, ar, he, fa | - |
| Start | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | de, nl |
| Spelling Options | fr, pt-BR, ru, tr, ja, ko, hi, th, ar, he, fa | - |
| Spellcheck | fr, pt-BR, ru, tr, ja, ko, hi, th, ar, he, fa | - |
| Shows your notes, next slide, and a timer | fr, pt-BR, ru, tr, ja, ko, hi, th, ar, he, fa | - |
| Select a cell range first to insert a styled table | fr, pt-BR, ru, tr, ja, ko, hi, th, ar, he, fa | - |
| Present to all | fr, pt-BR, ru, tr, ja, ko, hi, th, ar, he, fa | - |
| PDF Document (.pdf) with options | fr, pt-BR, ru, tr, ja, ko, hi, th, ar, he, fa | - |
| Open | fr, pt-BR, ru, tr, ja, ko, hi, th, ar, he, fa | - |
| Insert a styled table | fr, pt-BR, ru, tr, ja, ko, hi, th, ar, he, fa | - |
| Fullscreen, starting at this slide | fr, pt-BR, ru, tr, ja, ko, hi, th, ar, he, fa | - |
| Fullscreen, starting at slide 1 | fr, pt-BR, ru, tr, ja, ko, hi, th, ar, he, fa | - |
| Exchange | fr, pt-BR, ru, tr, ja, ko, hi, th, ar, he, fa | - |
| Animation | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | de, fr |
| All slides are hidden! | fr, pt-BR, ru, tr, ja, ko, hi, th, ar, he, fa | - |
| Wrap | pt-BR, ru, it, tr, ja, ko, hi, th, ar, fa | - |
| Viewing | pt-BR, ru, it, tr, ja, ko, hi, th, ar, fa | - |
| Validate Sidebar | pt-BR, ru, it, tr, ja, ko, hi, th, ar, fa | - |
| Validate Dialog | pt-BR, ru, it, tr, ja, ko, hi, th, ar, fa | - |
| Transitions | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | fr |
| Transition | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | fr |
| Total Row | pt-BR, ru, it, tr, ja, ko, hi, th, ar, fa | - |
| Section | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | fr |
| Presenter View | pt-BR, ru, it, tr, ja, ko, hi, th, ar, fa | - |
| Pages | fr, pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Options | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | fr |
| Open Views List | pt-BR, ru, it, tr, ja, ko, hi, th, ar, fa | - |
| Mode | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | fr |
| Math & Trig | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | fr |
| Header Row | pt-BR, ru, it, tr, ja, ko, hi, th, ar, fa | - |
| Function Library | pt-BR, ru, it, tr, ja, ko, hi, th, ar, fa | - |
| Filter Buttons | pt-BR, ru, it, tr, ja, ko, hi, th, ar, fa | - |
| Filter | pt-BR, ru, it, tr, ja, ko, hi, th, ar, fa | - |
| Field | pt-BR, ru, it, tr, ja, ko, hi, th, ar, fa | - |
| Export | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | cs |
| Effect | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | nl |
| Design | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | fr |
| Close backstage | fr, pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Blank Presentation | fr, pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Banded Columns | pt-BR, ru, it, tr, ja, ko, hi, th, ar, fa | - |
| AutoSum | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | de |
| Animations | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | fr |
| export your documents in different formats | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Viewing Mode | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| View document properties and information | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| View Only | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| View Changes | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Ungroup | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Type in the search box to find anything in your document | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Tracking | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Themes | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Text Document | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Table Design | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Symbols | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Start a new document from one of the following templates. | pt-BR, tr, ja, ko, hi, th, ar, he, fa | - |
| Spreadsheet | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Spacing & Color | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Sort | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Slide Views | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Slide Layout | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Size | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Sheets | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Sheet View | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Select | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Search... | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Search templates | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Results | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Remove Sheet View | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Recently opened documents will appear here | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Range | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Present to All | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Pivot Table | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Parts | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Paragraph | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Page Width | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| On mouse click | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| No templates match your search. | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| New Sheet View | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Navigator | ja, ko, hi, th, ar, fa | de, nl, id |
| Navigation Panel | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Navigation | pt-BR, ja, ko, hi, th, ar, fa | de, fr |
| Name | pt-BR, tr, ja, ko, hi, th, ar, fa | de |
| Multi Page View | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Move Up | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Move Down | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| More Templates | pt-BR, tr, ja, ko, hi, th, ar, he, fa | - |
| More Property Info | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| More Functions | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Merge & Split | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Master Slide Templates | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Margin | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Lookup & Reference | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Logical | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Loading templates… | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Lists/Bullets | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Last Column | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Insert Function | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Image Controls | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Header & Footer | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Group | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Freeze | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Forum | hi, th | de, fr, it, nl, pl, tr, id |
| Follow Presenter | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| First Column | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Financial | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| File Name | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Export Document | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Exit Sheet View | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| End Show | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Enable Animations | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Effects | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Editing Mode | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Duration | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Document Info | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Disable Animations | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Default View | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Date & Time | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Comments | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Click to expand | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Click to collapse | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Character | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Blank Spreadsheet | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Blank Document | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Banded Rows | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Background Image | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Back to document | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Arrange | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Apply to All Slides | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Applied animations | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Align | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| After | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | - |
| Untitled | pt-BR, tr, ja, ko, hi, th, ar, fa | - |
| Title, Vertical Text, Clipart | pt-BR, ja, ko, hi, th, ar, he, fa | - |
| Pause | pt-BR, ja, ko, hi, th, fa | de, fr |
| Page | tr, ja, ko, hi, th, ar, fa | fr |
| New | pt-BR, it, ja, ko, hi, th, ar, fa | - |
| Modified Date | pt-BR, tr, ja, ko, hi, th, ar, fa | - |
| Illustrations | pt-BR, tr, ja, ko, hi, th, fa | fr |
| Grid | ru, tr, ja, ko, hi, th, ar, fa | - |
| Formulas | ru, tr, ja, ko, hi, th, ar, fa | - |
| Format Cells | pt-BR, tr, ja, ko, hi, th, ar, fa | - |
| Editing | pt-BR, it, tr, ja, ko, hi, th, fa | - |
| Drawing | ru, tr, ja, ko, hi, th, ar, fa | - |
| Assistant | pt-BR, ja, ko, hi, th, ar, fa | fr |
| Vertical Title, Vertical Text | pt-BR, ja, ko, hi, th, ar, fa | - |
| Vertical Title, Text, Chart | pt-BR, ja, ko, hi, th, ar, fa | - |
| Title, Vertical Text | pt-BR, ja, ko, hi, th, ar, fa | - |
| Title, Content over Content | pt-BR, ja, ko, hi, th, ar, fa | - |
| Title, Content and 2 Content | pt-BR, ja, ko, hi, th, ar, fa | - |
| Title, Content | pt-BR, ja, ko, hi, th, ar, fa | - |
| Title, 6 Content | pt-BR, ja, ko, hi, th, ar, fa | - |
| Title, 4 Content | pt-BR, ja, ko, hi, th, ar, fa | - |
| Title, 2 Content over Content | pt-BR, ja, ko, hi, th, ar, fa | - |
| Title, 2 Content and Content | pt-BR, ja, ko, hi, th, ar, fa | - |
| Title and 2 Content | pt-BR, ja, ko, hi, th, ar, fa | - |
| Title Slide | pt-BR, ja, ko, hi, th, ar, fa | - |
| Title Only | pt-BR, ja, ko, hi, th, ar, fa | - |
| Slide Size | pt-BR, ja, ko, hi, th, ar, fa | - |
| Slide Show | pt-BR, ja, ko, hi, th, ar, fa | - |
| Show sheets | pt-BR, ja, ko, hi, th, ar, fa | - |
| Rich Text | hi, th | de, pt-BR, it, nl, id |
| Reset Layout | pt-BR, ja, ko, hi, th, ar, fa | - |
| Repeat in {0} seconds | pt-BR, ja, ko, hi, th, ar, fa | - |
| Print | tr, ja, ko, hi, th, ar, fa | - |
| Preview Slide {1} | pt-BR, ja, ko, hi, th, ar, fa | - |
| Pause... ( %SECONDS% ) | pt-BR, it, ja, ko, hi, th, fa | - |
| Outline | it, ja, ko, hi, th, ar, fa | - |
| No search results found! | pt-BR, ja, ko, hi, th, ar, fa | - |
| Merge & Center | pt-BR, tr, ja, ko, hi, th, fa | - |
| Loading references | pt-BR, ja, ko, hi, th, ar, fa | - |
| Close Navigation | pt-BR, ja, ko, hi, th, ar, fa | - |
| Change Layout | pt-BR, ja, ko, hi, th, ar, fa | - |
| Centered Text | pt-BR, ja, ko, hi, th, ar, fa | - |
| Blank Slide | pt-BR, ja, ko, hi, th, ar, fa | - |
| Add | pt-BR, ja, ko, hi, th, ar, fa | - |
| Zoom Out | pt-BR, ja, ko, hi, th, fa | - |
| Zoom In | pt-BR, ja, ko, hi, th, fa | - |
| The document is not signed. | pt-BR, ja, ko, hi, th, fa | - |
| Style list | pt-BR, ko, hi, th, ar, fa | - |
| Snap to Grid | pt-BR, ja, ko, hi, th, fa | - |
| Slides | pt-BR, ja, ko, hi, th, fa | - |
| Slide {0} of {1} | pt-BR, ja, ko, hi, th, fa | - |
| Signature | pt-BR, ko, hi, th, fa | fr |
| Show Comments | pt-BR, ja, ko, hi, th, ar | - |
| Resume | pt-BR, ja, ko, hi, th, fa | - |
| Restart | pt-BR, ja, ko, hi, th, fa | - |
| Replace | ja, ko, hi, th, ar, fa | - |
| Previous | pt-BR, ja, ko, hi, th, fa | - |
| Presenter Console | pt-BR, ja, ko, hi, th, fa | - |
| No Notes | pt-BR, ja, ko, hi, th, fa | - |
| Go Back | pt-BR, ja, ko, hi, th, fa | - |
| From Current Slide | pt-BR, ja, ko, hi, th, fa | - |
| From Beginning | pt-BR, ja, ko, hi, th, fa | - |
| Format | hi, th | de, fr, pl, id |
| Focus Cell | pt-BR, ko, hi, th, ar, fa | - |
| Current slide as Tag Image File Format (.tiff) | pt-BR, ja, ko, hi, th, fa | - |
| Current slide as Portable Network Graphics (.png) | pt-BR, ja, ko, hi, th, fa | - |
| Current slide as Graphics Interchange Format (.gif) | pt-BR, ja, ko, hi, th, fa | - |
| Current slide as Bitmap (.bmp) | pt-BR, ja, ko, hi, th, fa | - |
| Current Slide | pt-BR, ja, ko, hi, th, fa | - |
| Click to exit presentation... | pt-BR, ja, ko, hi, th, fa | - |
| AI Assistant | pt-BR, ko, hi, th, ar, fa | - |
| You are already presenting this document | it, ko, hi, th, fa | - |
| Top Margin | pt-BR, ko, hi, th, fa | - |
| Sparkline | ko, hi, th | de, fr |
| Show Grid | ja, ko, hi, th, fa | - |
| Server audit | pt-BR, ko, hi, th, fa | - |
| Presentation disabled | it, ko, hi, th, fa | - |
| Notes View | pt-BR, ko, hi, th, fa | - |
| Notes Pages | pt-BR, ko, hi, th, fa | - |
| Next Slide | pt-BR, ja, ko, hi, th | - |
| Neutral | hi, th | es, de, ru |
| HTML File (.html) | pt-BR, ko, hi, th, fa | - |
| HTML Document (.html) | pt-BR, ko, hi, th, fa | - |
| Full Page Slides | pt-BR, ko, hi, th, fa | - |
| Bottom Margin | pt-BR, ko, hi, th, fa | - |
| Windowed Presentation:  | ko, hi, th, fa | - |
| Windowed Presentation Blocked | ko, hi, th, fa | - |
| Text | hi, th | de, cs |
| Styles | ko, hi, th | fr |
| Sign | ja, hi, th, fa | - |
| Rich Text (.rtf) | th | de, cs, vi |
| Presenting in window | ko, hi, th, fa | - |
| Presentation was blocked. Please allow pop-ups in your browser. This lets slide shows to be displayed in separated windows, allowing for easy screen sharing. | ko, hi, th, fa | - |
| Presentation mode has been disabled for this document | ko, hi, th, fa | - |
| Number Format | hi, th, ar, fa | - |
| Notes | ko, hi, th | fr |
| Next | ja, ko, hi, th | - |
| Layout | hi, th | de, it |
| Invert Background | ko, hi, th, fa | - |
| Insert tabstop | ko, hi, th, fa | - |
| Empty Slide Show | ko, hi, th, fa | - |
| Edit document | ko, hi, th, fa | - |
| Delete tabstop | ko, hi, th, fa | - |
| Data | hi, th | cs, id |
| Close Presentation | ko, hi, th, fa | - |
| Category | ko, hi, th, fa | - |
| Already presenting | ko, hi, th, fa | - |
| Your library is empty | ko, hi, th | - |
| Word Document (.docx) | hi, th, fa | - |
| Word 2003 Document (.doc) | hi, th, fa | - |
| Warning! The browser you are using is not supported. | ko, hi, th | - |
| View | ko, hi, th | - |
| Updating citations | ko, hi, th | - |
| Updated citations | ko, hi, th | - |
| Unlinking citations will prevent PrivateOffice from updating citations and bibliography in this document. | ko, hi, th | - |
| Type | th | fr, nl |
| Title | ko, hi, th | - |
| This document may contain formatting or content that cannot be saved in the current file format. | ko, hi, th | - |
| The signature was valid, but the document has been modified. | ko, hi, th | - |
| The signature is OK, but the document is only partially signed. | ko, hi, th | - |
| The signature is OK, but the certificate could not be validated and the document is only partially signed. | ko, hi, th | - |
| The document could not be locked. | ko, hi, th | - |
| The document could not be locked, and is opened in read-only mode. | ko, hi, th | - |
| The document contains some citations which may be unreachable through web API. It may cause some problems while editing citations or bibliography. | ko, hi, th | - |
| Shape | hi, th, fa | - |
| Server returned this reason: | ko, hi, th | - |
| Screen Reading | hi, th, fa | - |
| Save as ODF format | ko, hi, th | - |
| Review | ko, hi, th | - |
| Rename | hi, th, fa | - |
| Recent | hi, th | nl |
| Read-only | ko, hi, th | - |
| Present in Window | hi, th, fa | - |
| Page Layout | hi, th, fa | - |
| Once citations are entered their storage and display type can not be changed. | ko, hi, th | - |
| ODF Drawing (.odg) | ko, hi, th | - |
| My Publications | ko, hi, th | - |
| Master | hi, th | de |
| Insert Rows Below | ko, hi, th | - |
| Insert Columns Before | ko, hi, th | - |
| Insert Columns After | ko, hi, th | - |
| Insert | ko, hi, th | - |
| Image (.png) | hi, th | fr |
| Help | hi, th | nl |
| Group Libraries | hi, th | fa |
| Go Online | hi, th, fa | - |
| Go Offline | hi, th, fa | - |
| General | hi, th | es |
| Fraction | hi, th | fr |
| Formula | hi, th | it |
| File | hi, th | it |
| Failed to load styles | ko, hi, th | - |
| Failed to load items | ko, hi, th | - |
| Failed to load groups | ko, hi, th | - |
| Failed to load collections | ko, hi, th | - |
| Export As | ko, hi, th | - |
| Enter a file name | ko, hi, th | - |
| Endnotes | ko, hi, th | - |
| Dropdown | hi, th | it |
| Document | th | fr, nl |
| Delete Rows | ko, hi, th | - |
| Delete Columns | ko, hi, th | - |
| Date | hi, th | fr |
| Creator(s) | ko, hi, th | - |
| Continue read only | ko, hi, th | - |
| Continue editing | ko, hi, th | - |
| Confirm | ko, hi, th | - |
| Collapse Tabs | hi, th, fa | - |
| Clipboard | hi, th, fa | - |
| Citations update failed | ko, hi, th | - |
| Citation warning | ko, hi, th | - |
| Citation Style | ko, hi, th | - |
| Checkbox | hi, th | it |
| Chart | hi, th, fa | - |
| Cells | hi, th, fa | - |
| An error occurred while fetching style list | ko, hi, th | - |
| An error occurred while fetching notes | ko, hi, th | - |
| Alignment | hi, th, fa | - |
| Add Note | ko, hi, th | - |
| cell address | hi, th | - |
| Zotero Warning | hi, th | - |
| Zotero API key is not configured | hi, th | - |
| Zotero API key is incorrect | hi, th | - |
| Unlink Citations | hi, th | - |
| Time | hi, th | - |
| This document is digitally signed and the signature is valid. | hi, th | - |
| This document has an invalid signature. | hi, th | - |
| The signature is OK, but the certificate could not be validated. | hi, th | - |
| Table | hi, th | - |
| Style | th | fr |
| Store as: | hi, th | - |
| Status Bar | hi, th | - |
| Smart Picker | hi, th | - |
| Share | hi, th | - |
| Shapes | hi, th | - |
| Send Feedback | hi, th | - |
| See history | hi, th | - |
| Scientific | hi, th | - |
| Save As | hi, th | - |
| Ruler | hi, th | - |
| Row Height | hi, th | - |
| Right Margin | hi, th | - |
| Report an issue | hi, th | - |
| Renaming... | hi, th | - |
| Read mode | hi, th | - |
| Properties | hi, th | - |
| Presentation | hi, th | - |
| PowerPoint Presentation (.pptx) | hi, th | - |
| PowerPoint 2003 Presentation (.ppt) | hi, th | - |
| Picture | hi, th | - |
| Permission Mode | hi, th | - |
| Percent | hi, th | - |
| Page Setup | hi, th | - |
| Online Help | hi, th | - |
| Number | hi, th | - |
| My Library | hi, th | - |
| Master View | hi, th | - |
| Left Margin | hi, th | - |
| Latest Updates | hi, th | - |
| Language: | hi, th | - |
| Insert Rows Above | hi, th | - |
| Home | hi, th | - |
| Heading 2 | hi, th | - |
| Heading 1 | hi, th | - |
| Good | hi, th | - |
| Form | hi, th | - |
| Footnotes | hi, th | - |
| Font Name | hi, th | - |
| Font | th | vi |
| Fields | hi, th | - |
| Export as | hi, th | - |
| Excel Spreadsheet (.xlsx) | hi, th | - |
| Excel 2003 Spreadsheet (.xls) | hi, th | - |
| Edit | hi, th | - |
| Download | hi, th | - |
| Default | hi, th | - |
| Dark Mode | hi, th | - |
| Currency | hi, th | - |
| Compact view | hi, th | - |
| Column Width | hi, th | - |
| CSV File (.csv) | hi, th | - |
| Borders | hi, th | - |
| Boolean Value | hi, th | - |
| Bookmarks | hi, th | - |
| Bad | hi, th | - |
| Tap to expand | th | - |
| Tap to collapse | th | - |
| Search | th | - |
| Scroll up annotations | th | - |
| Scroll down annotations | th | - |
| Saving... | th | - |
| Reset zoom | th | - |
| Repair | th | - |
| Remove | th | - |
| Refresh | th | - |
| PDF Document (.pdf) | th | - |
| ODF text document (.odt) | th | - |
| ODF spreadsheet (.ods) | th | - |
| ODF presentation (.odp) | th | - |
| Loading... | th | - |
| Keyboard shortcuts | th | - |
| Downloading... | th | - |
| Close | th | - |
| About | th | - |

## Полный индекс пропусков используемых UNO-подписей

Каждая строка ниже — это найденная подпись команды `_UNO(...)`, на которую ссылаются Writer, Calc, Impress или общий notebookbar builder. В строку попадают только подписи, где хотя бы один неанглийский язык не имеет перевода или оставляет английское значение.

| UNO label msgid | Языки без ключа | Языки со значением как в английском |
| --- | --- | --- |
| Delete Column | es, de, fr, pt-BR, ru, it, nl, pl, uk, tr, cs, zh-CN, ja, ko, hi, vi, id, th, ar, he, fa | - |
| Alt Text... | es, de, fr, pt-BR, ru, it, nl, pl, uk, tr, cs, zh-CN, ja, ko, hi, vi, id, th, ar, he, fa | - |
| ~Note | es, pt-BR, ru, it, nl, pl, uk, tr, cs, zh-CN, ja, ko, hi, vi, id, th, ar, he, fa | fr |
| ~Select Table | es, pt-BR, ru, it, nl, pl, uk, tr, cs, zh-CN, ja, ko, hi, vi, id, th, ar, he, fa | - |
| ~Remove Table... | es, pt-BR, ru, it, nl, pl, uk, tr, cs, zh-CN, ja, ko, hi, vi, id, th, ar, he, fa | - |
| ~Calculated Field... | es, pt-BR, ru, it, nl, pl, uk, tr, cs, zh-CN, ja, ko, hi, vi, id, th, ar, he, fa | - |
| Table... | es, pt-BR, ru, it, nl, pl, uk, tr, cs, zh-CN, ja, ko, hi, vi, id, th, ar, he, fa | - |
| Shuffle | es, pt-BR, ru, it, nl, pl, uk, tr, cs, zh-CN, ja, ko, hi, vi, id, th, ar, he, fa | - |
| Print Grid Lines | es, pt-BR, ru, it, nl, pl, uk, tr, cs, zh-CN, ja, ko, hi, vi, id, th, ar, he, fa | - |
| Pi~vot Calculated Field... | es, pt-BR, ru, it, nl, pl, uk, tr, cs, zh-CN, ja, ko, hi, vi, id, th, ar, he, fa | - |
| Insert Table | es, pt-BR, ru, it, nl, pl, uk, tr, cs, zh-CN, ja, ko, hi, vi, id, th, ar, he, fa | - |
| Insert Note | es, pt-BR, ru, it, nl, pl, uk, tr, cs, zh-CN, ja, ko, hi, vi, id, th, ar, he, fa | - |
| Add Theme... | es, pt-BR, ru, it, nl, pl, uk, tr, cs, zh-CN, ja, ko, hi, vi, id, th, ar, he, fa | - |
| Manage Tracked Changes | tr, ja, ko, hi, vi, th, ar, he, fa | - |
| ~Optimal | ko, hi, vi, ar, fa | de, fr, id |
| ~Middle | es, tr, ko, hi, vi, th, ar, fa | - |
| Time (~variable) | tr, ko, hi, vi, th, ar, he, fa | - |
| Reject tracked change but keep it | tr, ja, ko, hi, vi, th, ar, fa | - |
| Reject but Track | tr, ja, ko, hi, vi, th, ar, fa | - |
| Previous Tracked Change | tr, ja, ko, hi, vi, th, ar, fa | - |
| Next Tracked Change | tr, ja, ko, hi, vi, th, ar, fa | - |
| Insert Soft Hyphen... | tr, ko, hi, vi, th, ar, he, fa | - |
| Fontwork... | hi, vi, he | fr, pt-BR, it, nl, pl |
| Connectors (double click for multi-selection) | es, tr, ko, hi, vi, th, ar, fa | - |
| ~Parallel | ko, hi, vi, ar, fa | de |
| Symbol | hi, vi, ar | de, pl, cs |
| Insert page number | ko, hi, vi, ar, he, fa | - |
| Give a label to identify an object | ja, ko, hi, vi, ar, fa | - |
| Connectors | ko, hi, vi, th, ar, fa | - |
| ~Through | ko, hi, vi, ar, fa | - |
| ~Page Number... | ko, hi, vi, ar, fa | - |
| Translate... | ko, hi, vi, ar, fa | - |
| Theme... | ko, hi, vi, ar, fa | - |
| Insert columns after | ko, hi, vi, ar, fa | - |
| Insert Text Box (double click for multi-selection) | ko, hi, vi, ar, fa | - |
| Insert Line (double click for multi-selection) | ko, hi, vi, ar, fa | - |
| Add descriptions of non-text content (for accessibility) | ja, ko, hi, vi, ar | - |
| Split Cells... | ko, hi, vi, fa | - |
| Se~ction... | hi, vi, fa | fr |
| Set Heading Numbering | hi, vi, ar, fa | - |
| Orientation | hi, vi, fa | fr |
| None | ko, hi, vi, fa | - |
| Merge Cells | ko, hi, vi, fa | - |
| Insert rows above | hi, vi, ar, fa | - |
| Insert Column After | hi, vi, ar, fa | - |
| F~rame... | hi, vi, fa | nl |
| Delete ~Columns | hi, vi, ar, fa | - |
| Columns A~fter | ko, hi, vi, ar | - |
| Animation | hi, vi | de, fr |
| ~Text Box | hi, vi, fa | - |
| ~Table Properties... | hi, vi, fa | - |
| ~Slide Number | hi, vi, fa | - |
| ~Remove Outline | hi, vi, fa | - |
| ~Image... | hi, vi | fr |
| ~Hyperlink... | hi, vi, fa | - |
| ~Delete Slide | hi, vi, fa | - |
| ~Accessibility Check... | hi, vi, fa | - |
| Vertical Grids | hi, vi, fa | - |
| Unprotect Cells | hi, vi, fa | - |
| Toggle Shadow | hi, vi, fa | - |
| Toggle Formatting Marks | hi, vi, fa | - |
| Slide ~Count | hi, vi, fa | - |
| Slide Properties... | hi, vi, fa | - |
| Show Navigator Window | hi, vi, fa | - |
| Select Cell | hi, vi, fa | - |
| Reject Change | hi, vi, fa | - |
| Reject | hi, vi, fa | - |
| QR and ~Barcode... | hi, vi, fa | - |
| Pr~evious | hi, vi, fa | - |
| Na~vigator | - | de, nl, id |
| Insert Vertical Text | hi, vi, fa | - |
| Insert Special Characters | hi, vi, fa | - |
| Insert Row Above | hi, vi, fa | - |
| Insert Frame | hi, vi, fa | - |
| Insert Fontwork Text | hi, vi, fa | - |
| Insert Field | hi, vi, fa | - |
| Insert Columns ~After | hi, ar, fa | - |
| Insert Caption... | hi, vi, fa | - |
| Increase Size | hi, vi, fa | - |
| Increase Font Size | hi, vi, fa | - |
| Image Mode | hi, vi, fa | - |
| Horizontal Grids | hi, vi, fa | - |
| Heading ~Numbering... | hi, vi, fa | - |
| For~matting Marks | hi, vi, fa | - |
| Format Legend | hi, vi, ar | - |
| Fiel~d | hi, vi, fa | - |
| E~xit Group | hi, vi, fa | - |
| Duplicate ~Slide | hi, vi, fa | - |
| Delete selected columns | hi, vi, fa | - |
| Decrease Size | hi, vi, fa | - |
| Decrease Font Size | hi, vi, fa | - |
| C~haracter... | hi, vi, fa | - |
| C~ell | hi, vi, fa | - |
| Crop Image | hi, vi, fa | - |
| Compare Non-Track Changed Document | hi, vi, fa | - |
| Character Highlighting Color | ko, hi, vi | - |
| Borders (Shift to overwrite) | hi, vi, fa | - |
| Before | ko, hi, vi | - |
| ~Word Count... | hi, vi | - |
| ~Unordered List | hi, fa | - |
| ~Undo | hi, vi | - |
| ~Redo | hi, vi | - |
| ~Properties... | hi, vi | - |
| ~Page Style... | hi, vi | - |
| ~Page Break | hi, fa | - |
| ~Ordered List | hi, fa | - |
| ~Format Cells... | hi, vi | - |
| ~Define Range... | hi, vi | - |
| ~Data Table... | hi, vi | - |
| ~Cut | hi, vi | - |
| ~Column | hi, vi | - |
| Wrap Text | hi, vi | - |
| Watermark... | hi, vi | - |
| Unmerge Cells | hi, vi | - |
| Toggle Unordered List | hi, fa | - |
| Toggle Ordered List | hi, fa | - |
| Slide ~Layout | hi, vi | - |
| Set Line Spacing | hi, vi | - |
| Select ~Range... | hi, vi | - |
| Row | hi, vi | - |
| Prin~t Ranges | hi, vi | - |
| Pi~vot Table... | hi, vi | - |
| Next | hi, vi | - |
| Media | - | it, id |
| Lis~ts | hi, vi | - |
| Line Spacing | hi, vi | - |
| Insert ~Table... | hi, vi | - |
| Insert Page Break | hi, fa | - |
| Insert Image... | hi, vi | - |
| Insert Comment | hi, vi | - |
| Formula to Value | hi, vi | - |
| Format as Percent | hi, vi | - |
| Format as Currency | hi, vi | - |
| Format Pa~ge... | hi, vi | - |
| Delete table | hi, vi | - |
| Delete Table | hi, vi | - |
| Delete Decimal Place | hi, vi | - |
| Cop~y | hi, vi | - |
| Compare | hi, vi | - |
| Columns ~After | hi, ar | - |
| Column | hi, vi | - |
| Clear Direct Formatting | hi, vi | - |
| Center Vertically | hi, vi | - |
| Align Top to Anchor | hi, vi | - |
| Align Bottom to Anchor | hi, vi | - |
| Add Decimal Place | hi, vi | - |
| Accept Change | hi, vi | - |
| ~Thesaurus... | - | nl |
| ~Spelling... | - | nl |
| ~Page... | - | fr |
| ~Interaction... | - | fr |
| ~Clear Direct Formatting | vi | - |
| Superscript | - | nl |
| Subscript | - | nl |
| Rows ~Above | hi | - |
| Resolved Comments | hi | - |
| Insert Rows ~Above | hi | - |
| Insert Audio or Video | hi | - |
| Increase Indent | hi | - |
| Freeze Rows and Columns | hi | - |
| Freeze First Row | hi | - |
| Freeze First Column | hi | - |
| Flip Horizontally | fa | - |
| Decrease Indent | hi | - |
| Crop | hi | - |
| Contrast | - | nl |
| Align Center | hi | - |

## Полный индекс пропусков глобальной UNO-карты

Это шире видимого notebookbar: сюда входят все подписи из встроенной карты команд `unoCommandsArray`, где хотя бы один неанглийский язык не имеет перевода или оставляет английское значение.

| UNO label msgid | Языки без ключа | Языки со значением как в английском |
| --- | --- | --- |
| Delete Column | es, de, fr, pt-BR, ru, it, nl, pl, uk, tr, cs, zh-CN, ja, ko, hi, vi, id, th, ar, he, fa | - |
| Alt Text... | es, de, fr, pt-BR, ru, it, nl, pl, uk, tr, cs, zh-CN, ja, ko, hi, vi, id, th, ar, he, fa | - |
| ~Note | es, pt-BR, ru, it, nl, pl, uk, tr, cs, zh-CN, ja, ko, hi, vi, id, th, ar, he, fa | fr |
| ~Select Table | es, pt-BR, ru, it, nl, pl, uk, tr, cs, zh-CN, ja, ko, hi, vi, id, th, ar, he, fa | - |
| ~Remove Table... | es, pt-BR, ru, it, nl, pl, uk, tr, cs, zh-CN, ja, ko, hi, vi, id, th, ar, he, fa | - |
| ~Insert Table... | es, pt-BR, ru, it, nl, pl, uk, tr, cs, zh-CN, ja, ko, hi, vi, id, th, ar, he, fa | - |
| ~Calculated Field... | es, pt-BR, ru, it, nl, pl, uk, tr, cs, zh-CN, ja, ko, hi, vi, id, th, ar, he, fa | - |
| Table... | es, pt-BR, ru, it, nl, pl, uk, tr, cs, zh-CN, ja, ko, hi, vi, id, th, ar, he, fa | - |
| Table Style Options | es, pt-BR, ru, it, nl, pl, uk, tr, cs, zh-CN, ja, ko, hi, vi, id, th, ar, he, fa | - |
| Shuffle | es, pt-BR, ru, it, nl, pl, uk, tr, cs, zh-CN, ja, ko, hi, vi, id, th, ar, he, fa | - |
| Print Grid Lines | es, pt-BR, ru, it, nl, pl, uk, tr, cs, zh-CN, ja, ko, hi, vi, id, th, ar, he, fa | - |
| Pi~vot Calculated Field... | es, pt-BR, ru, it, nl, pl, uk, tr, cs, zh-CN, ja, ko, hi, vi, id, th, ar, he, fa | - |
| New Canvas Slide | es, pt-BR, ru, it, nl, pl, uk, tr, cs, zh-CN, ja, ko, hi, vi, id, th, ar, he, fa | - |
| Manage Themes... | es, pt-BR, ru, it, nl, pl, uk, tr, cs, zh-CN, ja, ko, hi, vi, id, th, ar, he, fa | - |
| Insert Table | es, pt-BR, ru, it, nl, pl, uk, tr, cs, zh-CN, ja, ko, hi, vi, id, th, ar, he, fa | - |
| Insert Note | es, pt-BR, ru, it, nl, pl, uk, tr, cs, zh-CN, ja, ko, hi, vi, id, th, ar, he, fa | - |
| Add Theme... | es, pt-BR, ru, it, nl, pl, uk, tr, cs, zh-CN, ja, ko, hi, vi, id, th, ar, he, fa | - |
| Manage Tracked Changes | tr, ja, ko, hi, vi, th, ar, he, fa | - |
| ~Optimal | ko, hi, vi, ar, fa | de, fr, id |
| ~Middle | es, tr, ko, hi, vi, th, ar, fa | - |
| Time (~variable) | tr, ko, hi, vi, th, ar, he, fa | - |
| Select Sheet View | zh-CN, ja, ko, hi, vi, th, ar, fa | - |
| Reject tracked change but keep it | tr, ja, ko, hi, vi, th, ar, fa | - |
| Reject but Track | tr, ja, ko, hi, vi, th, ar, fa | - |
| Record Tracked Changes | tr, ja, ko, hi, vi, th, ar, fa | - |
| Previous Tracked Change | tr, ja, ko, hi, vi, th, ar, fa | - |
| Next Tracked Change | tr, ja, ko, hi, vi, th, ar, fa | - |
| Insert Soft Hyphen... | tr, ko, hi, vi, th, ar, he, fa | - |
| Fontwork... | hi, vi, he | fr, pt-BR, it, nl, pl |
| Delete Content Control | ja, ko, hi, vi, th, ar, he, fa | - |
| Connectors (double click for multi-selection) | es, tr, ko, hi, vi, th, ar, fa | - |
| Unfloat Frame Content | ja, ko, hi, vi, ar, he, fa | - |
| Straight Connector with Arrows | tr, ko, hi, vi, th, ar, fa | - |
| Straight Connector ends with Arrow | tr, ko, hi, vi, th, ar, fa | - |
| Straight Connector | tr, ko, hi, vi, th, ar, fa | - |
| Line Connector Ends with Arrow | tr, ko, hi, vi, th, ar, fa | - |
| Line Connector | tr, ko, hi, vi, th, ar, fa | - |
| Insert ~Y Error Bars... | ko, hi, vi, th, ar, he, fa | - |
| Insert ~X Error Bars... | ko, hi, vi, th, ar, he, fa | - |
| Insert Hyperlink... | tr, ko, hi, vi, th, ar, fa | - |
| Curved Connector with Arrows | tr, ko, hi, vi, th, ar, fa | - |
| Curved Connector Ends with Arrow | tr, ko, hi, vi, th, ar, fa | - |
| Curved Connector | tr, ko, hi, vi, th, ar, fa | - |
| Connector with Arrows | tr, ko, hi, vi, th, ar, fa | - |
| Connector Ends with Arrow | tr, ko, hi, vi, th, ar, fa | - |
| Add To Dictionary | tr, ko, hi, vi, th, ar, fa | - |
| ~Parallel | ko, hi, vi, ar, fa | de |
| ~F-test... | hi, vi | fr, cs, ko, id |
| Symbol | hi, vi, ar | de, pl, cs |
| Promote Outline Level with Subpoints | ko, hi, vi, ar, he, fa | - |
| Move Item Up with Subpoints | ko, hi, vi, ar, he, fa | - |
| Move Item Down with Subpoints | ko, hi, vi, ar, he, fa | - |
| Insert page number | ko, hi, vi, ar, he, fa | - |
| Insert Page Number | ko, hi, vi, ar, he, fa | - |
| Ignore All | ja, ko, hi, vi, ar, fa | - |
| Give a label to identify an object | ja, ko, hi, vi, ar, fa | - |
| Demote Outline Level with Subpoints | ko, hi, vi, ar, he, fa | - |
| Delete Index | ko, hi, vi, th, ar, fa | - |
| Connectors | ko, hi, vi, th, ar, fa | - |
| Connector | ko, hi, vi, th, ar, fa | - |
| ~Zero-width Space | ko, hi, vi, ar, fa | - |
| ~Word Joiner | ko, hi, vi, ar, fa | - |
| ~Through | ko, hi, vi, ar, fa | - |
| ~Soft Hyphen | ko, hi, vi, ar, fa | - |
| ~Right-to-Left Mark | ko, hi, vi, ar, fa | - |
| ~Page Number... | ko, hi, vi, ar, fa | - |
| ~No-break Space | ko, hi, vi, ar, fa | - |
| ~Left-to-Right Mark | ko, hi, vi, ar, fa | - |
| ~Index Entry... | ko, hi, vi, ar, fa | - |
| ~Hyperlink | ko, hi, vi, fa | nl |
| Vertically ~Top | ko, hi, vi, ar, fa | - |
| Vertically ~Bottom | ko, hi, vi, ar, fa | - |
| Vertically S~pacing | ko, hi, vi, ar, fa | - |
| Update ~Index | ko, hi, vi, ar, fa | - |
| Translate... | ko, hi, vi, ar, fa | - |
| Theme... | ko, hi, vi, ar, fa | - |
| Sparkline... | hi, vi | fr, it, nl |
| Rectangle (double click for multi-selection) | ko, hi, vi, ar, fa | - |
| Properties | ko, hi, vi, ar, fa | - |
| Promote Outline Level | ko, hi, vi, he, fa | - |
| Open the Elements Deck | ja, hi, vi, ar, fa | - |
| Open the Accessibility Check Deck | hi, vi, ar, he, fa | - |
| Non-breaking ~Hyphen | ko, hi, vi, ar, fa | - |
| Move Item Up | ko, hi, vi, ar, fa | - |
| Move Item Down | ko, hi, vi, ar, fa | - |
| Insert columns after | ko, hi, vi, ar, fa | - |
| Insert Text Box (double click for multi-selection) | ko, hi, vi, ar, fa | - |
| Insert Line (double click for multi-selection) | ko, hi, vi, ar, fa | - |
| Horizontally ~Right | ko, hi, vi, ar, fa | - |
| Horizontally ~Left | ko, hi, vi, ar, fa | - |
| E~xecute Interaction... | hi, vi, ar, he, fa | - |
| Ellipse (double click for multi-selection) | ko, hi, vi, ar, fa | - |
| Demote Outline Level | ko, hi, vi, he, fa | - |
| Cuboid | ko, hi, vi, ar, fa | - |
| Add descriptions of non-text content (for accessibility) | ja, ko, hi, vi, ar | - |
| ~Z-test... | hi, vi | fr, cs |
| ~Remove Hyperlink | ko, hi, vi, fa | - |
| ~Footnote/Endnote Settings... | ko, hi, vi, ar | - |
| ~Data | hi, vi | cs, id |
| Vertically C~enter | ko, hi, vi, fa | - |
| Te~xt | hi, vi | de, cs |
| Split Cells... | ko, hi, vi, fa | - |
| Sparklines | hi, vi | de, fr |
| Signat~ure Line... | hi, vi, ar, fa | - |
| Show | hi, vi, ar, fa | - |
| Se~ction... | hi, vi, fa | fr |
| Set Heading Numbering | hi, vi, ar, fa | - |
| Reject and Move to Next | ko, hi, vi, fa | - |
| Puzzle | - | de, fr, it, cs |
| Page Properties... | hi, vi, ar, fa | - |
| Outline Font Effect | ko, hi, vi, fa | - |
| Orientation | hi, vi, fa | fr |
| None | ko, hi, vi, fa | - |
| No List | ko, hi, vi, fa | - |
| Merge Cells | ko, hi, vi, fa | - |
| Insert rows below | hi, vi, ar, fa | - |
| Insert rows above | hi, vi, ar, fa | - |
| Insert columns before | ko, hi, vi, ar | - |
| Insert Column After | hi, vi, ar, fa | - |
| Horizontally ~Spacing | ko, hi, vi, fa | - |
| Horizontally ~Center | ko, hi, vi, fa | - |
| Go t~o Slide... | es, hi, vi, ar | - |
| F~rame... | hi, vi, fa | nl |
| Edit Hyperlink... | ko, hi, vi, fa | - |
| Delete ~Columns | hi, vi, ar, fa | - |
| Delete selected rows | hi, vi, he, fa | - |
| Delete Row | hi, vi, ar, fa | - |
| Cross-~reference... | ko, hi, vi, fa | - |
| Content Control Properties | ko, hi, ar, he | - |
| Columns A~fter | ko, hi, vi, ar | - |
| Animation | hi, vi | de, fr |
| ~Text Box | hi, vi, fa | - |
| ~Table Properties... | hi, vi, fa | - |
| ~Slide Number | hi, vi, fa | - |
| ~Remove Outline | hi, vi, fa | - |
| ~Page | hi, vi | fr |
| ~New Slide | hi, vi, fa | - |
| ~More Options... | hi, vi, fa | - |
| ~More Fields... | hi, vi, fa | - |
| ~Image... | hi, vi | fr |
| ~Hyperlink... | hi, vi, fa | - |
| ~Endnote | hi, vi, fa | - |
| ~Delete Slide | hi, vi, fa | - |
| ~Add to List | ko, hi, vi | - |
| ~Accessibility Check... | hi, vi, fa | - |
| Vertical Grids | hi, vi, fa | - |
| Unprotect Cells | hi, vi, fa | - |
| Ungroup Sparklines | hi, vi, fa | - |
| Toggle Shadow | hi, vi, fa | - |
| Toggle Formatting Marks | hi, vi, fa | - |
| To Cell (~resize with cell) | hi, vi, ar | - |
| S~pecial Character... | hi, vi, fa | - |
| S~lide | hi, vi | pt-BR |
| Slide ~Count | hi, vi, fa | - |
| Slide Tit~le | hi, vi, fa | - |
| Slide Properties... | hi, vi, fa | - |
| Show Navigator Window | hi, vi, fa | - |
| Select Cell | hi, vi, fa | - |
| Rename S~heet... | hi, vi, ar | - |
| Reject Change | hi, vi, fa | - |
| Reject All | hi, vi, fa | - |
| Reject | hi, vi, fa | - |
| QR and ~Barcode... | hi, vi, fa | - |
| Pr~evious | hi, vi, fa | - |
| Prohibited | hi, vi, fa | - |
| Page Tit~le | hi, vi, fa | - |
| Open the Styles Deck | hi, vi, fa | - |
| New Page | hi, vi, fa | - |
| Na~vigator | - | de, nl, id |
| Merge and center or unmerge cells depending on the current toggle state | hi, vi, fa | - |
| Line Spacing: 1.15 | hi, vi, fa | - |
| License Information | hi, vi, fa | - |
| Insert Vertical Text | hi, vi, fa | - |
| Insert Text Box | hi, vi, fa | - |
| Insert Special Characters | hi, vi, fa | - |
| Insert Special Character | hi, vi, fa | - |
| Insert Row Above | hi, vi, fa | - |
| Insert Frame | hi, vi, fa | - |
| Insert Fontwork Text | hi, vi, fa | - |
| Insert Field | hi, vi, fa | - |
| Insert Endnote | hi, vi, fa | - |
| Insert Cross-reference | hi, vi, fa | - |
| Insert Columns ~After | hi, ar, fa | - |
| Insert Column Before | hi, vi, fa | - |
| Insert Caption... | hi, vi, fa | - |
| Insert Bookmark | hi, vi, fa | - |
| Increase Size | hi, vi, fa | - |
| Increase Font Size | hi, vi, fa | - |
| Image Mode | hi, vi, fa | - |
| Ignore | hi, vi, fa | - |
| Horizontal Grids | hi, vi, fa | - |
| He~ader and Footer | hi, vi, fa | - |
| Heading ~Numbering... | hi, vi, fa | - |
| Group Sparklines | hi, vi, fa | - |
| Fo~rm | hi, vi | tr |
| For~matting Marks | hi, vi, fa | - |
| Format Legend | hi, vi, ar | - |
| For All Text | hi, vi, fa | - |
| First ~Author | hi, vi, fa | - |
| Fiel~d | hi, vi, fa | - |
| E~xit Group | hi, vi, fa | - |
| Edit Sparkline... | hi, vi, fa | - |
| Edit Sparkline Group... | hi, vi, fa | - |
| Edit Section... | hi, vi, fa | - |
| D~elete Page | hi, vi, fa | - |
| Duplicate ~Slide | hi, vi, fa | - |
| Duplicate Page | hi, vi, fa | - |
| Double Underline | hi, vi, fa | - |
| Delete selected columns | hi, vi, fa | - |
| Decrease Size | hi, vi, fa | - |
| Decrease Font Size | hi, vi, fa | - |
| Date | hi, vi | fr |
| C~haracter... | hi, vi, fa | - |
| C~ell | hi, vi, fa | - |
| Cycle Case | hi, vi, fa | - |
| Current ~Index | hi, vi, fa | - |
| Crop Image | hi, vi, fa | - |
| Copy Hyperlink Location | ko, hi, vi | - |
| Compare Non-Track Changed Document | hi, vi, fa | - |
| Columns B~efore | hi, vi, ar | - |
| Character Highlighting Color | ko, hi, vi | - |
| Borders (Shift to overwrite) | hi, vi, fa | - |
| Before | ko, hi, vi | - |
| After | ko, hi, vi | - |
| Accept and Move to Next | ko, hi, vi | - |
| ~Word Count... | hi, vi | - |
| ~Unordered List | hi, fa | - |
| ~Undo | hi, vi | - |
| ~Tab Color... | hi, vi | - |
| ~Spacing | hi, vi | - |
| ~Show Sheet... | hi, vi | - |
| ~Shape | hi, vi | - |
| ~Save... | hi, vi | - |
| ~Sampling... | hi, vi | - |
| ~Reset Filter | hi, vi | - |
| ~Regression... | hi, vi | - |
| ~Redo | hi, vi | - |
| ~Properties... | hi, vi | - |
| ~Page Style... | hi, vi | - |
| ~Page Break | hi, fa | - |
| ~Ordered List | hi, fa | - |
| ~Named Ranges and Expressions | hi, vi | - |
| ~Moving Average... | hi, vi | - |
| ~Move or Copy Sheet... | hi, vi | - |
| ~Insert or Edit... | hi, vi | - |
| ~Hide Sheet | hi, vi | - |
| ~Headers and Footers... | hi, vi | - |
| ~Go to Sheet... | hi, vi | - |
| ~Formula Object... | hi, vi | - |
| ~Format Cells... | hi, vi | - |
| ~Footnote | hi, vi | - |
| ~Exponential Smoothing... | hi, vi | - |
| ~Display Grid | hi, fa | - |
| ~Descriptive Statistics... | hi, vi | - |
| ~Delete Sheet... | hi, vi | - |
| ~Define Range... | hi, vi | - |
| ~Data Table... | hi, vi | - |
| ~Cut | hi, vi | - |
| ~Covariance... | hi, vi | - |
| ~Correlation... | hi, vi | - |
| ~Column | hi, vi | - |
| ~Clear | hi, vi | - |
| ~Chi-square Test... | hi, vi | - |
| ~Analysis of Variance (ANOVA)... | hi, vi | - |
| Wrap Text | hi, vi | - |
| Watermark... | hi, vi | - |
| Unmerge Cells | hi, vi | - |
| T~able | hi, vi | - |
| Track Chan~ges | hi, vi | - |
| Toggle Unordered List | hi, fa | - |
| Toggle Ordered List | hi, fa | - |
| Thousands Separator | hi, vi | - |
| Table of Contents and Inde~x | hi, vi | - |
| S~how Columns | hi, vi | - |
| Slide ~Layout | hi, vi | - |
| Slide Transition | hi, vi | - |
| Sho~w Rows | hi, vi | - |
| Sheet ~Tab Color... | hi, vi | - |
| Set Line Spacing | hi, vi | - |
| Set Character Spacing | hi, vi | - |
| Set Background Image... | hi, vi | - |
| Select ~Range... | hi, vi | - |
| Save... | hi, vi | - |
| Row | hi, vi | - |
| Rot~ate | hi, vi | - |
| Rotate 90° ~Right | vi, fa | - |
| Rotate 90° ~Left | vi, fa | - |
| Ring | - | de, nl |
| Prin~t Ranges | hi, vi | - |
| Pi~vot Table... | hi, vi | - |
| Paired ~t-test... | hi, vi | - |
| Number Format: Date | hi, vi | - |
| Next | hi, vi | - |
| More ~Filters | hi, vi | - |
| Media | - | it, id |
| Master Slides | hi, vi | - |
| Lis~ts | hi, vi | - |
| Line Spacing: 2 | hi, vi | - |
| Line Spacing: 1.5 | hi, vi | - |
| Line Spacing | hi, vi | - |
| Insert ~Table... | hi, vi | - |
| Insert Row Below | hi, vi | - |
| Insert Page Break | hi, fa | - |
| Insert Image... | hi, vi | - |
| Insert Footnote | hi, vi | - |
| Insert Comment | hi, vi | - |
| Insert Columns ~Before | hi, fa | - |
| Increase Paragraph Spacing | hi, vi | - |
| H~ide Columns | hi, vi | - |
| Go t~o Page... | hi, vi | - |
| F~ourier Analysis... | hi, vi | - |
| F~ormat | - | pl, id |
| Formula to Value | hi, vi | - |
| Format as Time | hi, vi | - |
| Format as Scientific | hi, vi | - |
| Format as Percent | hi, vi | - |
| Format as Number | hi, vi | - |
| Format as General | hi, vi | - |
| Format as Date | hi, vi | - |
| Format as Currency | hi, vi | - |
| Format Pa~ge... | hi, vi | - |
| Find and Rep~lace... | ko, hi | - |
| Explosion | - | de, fr |
| Ellipse | - | de, fr |
| Display Grid | hi, fa | - |
| De~lete... | hi, vi | - |
| Delete table | hi, vi | - |
| Delete Table | hi, vi | - |
| Delete Sparkline Group | hi, vi | - |
| Delete Sparkline | hi, vi | - |
| Delete Decimal Place | hi, vi | - |
| Decrease Paragraph Spacing | hi, vi | - |
| Date... | vi | fr |
| C~onditional | hi, vi | - |
| Co~mpress... | hi, vi | - |
| Cop~y | hi, vi | - |
| Compare | hi, vi | - |
| Columns ~After | hi, ar | - |
| Column | hi, vi | - |
| Cl~ear Contents... | hi, vi | - |
| Clone Formatting | hi, vi | - |
| Cle~ar Cells... | hi, vi | - |
| Clear Direct Formatting | hi, vi | - |
| Center Vertically | hi, vi | - |
| Apply Suggestion | hi, vi | - |
| Anc~hor | hi, vi | - |
| Align Top to Anchor | hi, vi | - |
| Align Tex~t | hi, vi | - |
| Align Bottom to Anchor | hi, vi | - |
| Add Decimal Place | hi, vi | - |
| Accept Change | hi, vi | - |
| 6-Point Star, Concave | hi, vi | - |
| ~Thesaurus... | - | nl |
| ~Spelling... | - | nl |
| ~Sentence case | fa | - |
| ~Page... | - | fr |
| ~Page Numbers... | vi | - |
| ~Interaction... | - | fr |
| ~Insert... | hi | - |
| ~Help | - | nl |
| ~File | - | it |
| ~Date | - | fr |
| ~Contour | - | fr |
| ~Clear Direct Formatting | vi | - |
| ~Automatic Spell Checking | hi | - |
| View Grid Lines | hi | - |
| Superscript | - | nl |
| Subscript | - | nl |
| Stop | - | it |
| Small capitals | fa | - |
| Rows ~Below | hi | - |
| Rows ~Above | hi | - |
| Resolved Comments | hi | - |
| Reset all Data Points | fa | - |
| Reset Data Point | fa | - |
| Reply Comment | fa | - |
| Rectangle | - | fr |
| Pop Art | - | cs |
| Language Status | fa | - |
| Insert ~Rows | hi | - |
| Insert Rows ~Below | hi | - |
| Insert Rows ~Above | hi | - |
| Insert Mean ~Value Line | fa | - |
| Insert Co~lumns | hi | - |
| Insert Audio or Video | hi | - |
| Increase Indent | hi | - |
| Icon Set... | vi | - |
| General | - | es |
| Freeze ~Cells | hi | - |
| Freeze Rows and Columns | hi | - |
| Freeze First Row | hi | - |
| Freeze First Column | hi | - |
| Format Y Error Bars... | fa | - |
| Format X Error Bars... | fa | - |
| Format Stock Loss... | fa | - |
| Format Stock Gain... | fa | - |
| Format Single Data Label... | fa | - |
| Format Mean Value Line... | fa | - |
| Format Data Series... | fa | - |
| Format Data Point... | fa | - |
| For Selection | fa | - |
| For Paragraph | fa | - |
| Flip Horizontally | fa | - |
| Decrease Indent | hi | - |
| Data Bar... | vi | - |
| Curve Up | fa | - |
| Curve Down | fa | - |
| Crop | hi | - |
| Contrast | - | nl |
| Columns ~Before | hi | - |
| Color Scale... | vi | - |
| Chevron | - | fr |
| Character Spacing | vi | - |
| Align Center | hi | - |

## Неразрешенные UNO-команды notebookbar

| Область | UNO-команда | component argument | Сколько раз встречается |
| --- | --- | --- | --- |
| Writer | CellVertBottom | - | 1 |
| Writer | ChangeFont | text | 1 |
| Writer | DeleteRows | text | 1 |
| Writer | DrawText | - | 1 |
| Writer | FlipVertical | - | 2 |
| Writer | FormatMenu | text | 1 |
| Writer | FormatPaintbrush | - | 1 |
| Writer | FormatSelection | - | 1 |
| Writer | InsertColumnsBefore | text | 1 |
| Writer | InsertRowsAfter | text | 1 |
| Writer | Italic | - | 1 |
| Writer | NumberFormatDate | text | 1 |
| Writer | ReplyComment | - | 1 |
| Writer | SelectAll | - | 1 |
| Writer | Sidebar | - | 1 |
| Writer | Spacing | - | 1 |
| Writer | TitlePageDialog | text | 2 |
| Writer | TrackChanges | text | 1 |
| Writer | WrapRight | text | 3 |
| Calc | ConditionalFormatMenu | spreadsheet | 2 |
| Calc | DataFilterRemoveFilter | spreadsheet | 1 |
| Calc | DeletePivotTable | spreadsheet | 1 |
| Calc | DeleteRows | spreadsheet | 1 |
| Calc | DeleteSparkline | spreadsheet | 1 |
| Calc | DrawText | - | 1 |
| Calc | EditHeaderAndFooter | spreadsheet | 1 |
| Calc | EditSparkline | spreadsheet | 1 |
| Calc | FlipVertical | - | 2 |
| Calc | FormatMenu | spreadsheet | 1 |
| Calc | FormatPaintbrush | - | 1 |
| Calc | InsertColumnsBefore | spreadsheet | 1 |
| Calc | InsertCurrentDate | spreadsheet | 1 |
| Calc | InsertRowsAfter | spreadsheet | 1 |
| Calc | Italic | - | 1 |
| Calc | NumberFormatDecimal | spreadsheet | 1 |
| Calc | SelectAll | - | 1 |
| Calc | Sidebar | - | 1 |
| Calc | ToggleSheetGrid | spreadsheet | 1 |
| Calc | Validation | spreadsheet | 1 |
| Calc | WrapRight | text | 2 |
| Impress | CellVertBottom | - | 2 |
| Impress | DeleteRows | presentation | 1 |
| Impress | FlipVertical | - | 2 |
| Impress | FormatPaintbrush | - | 1 |
| Impress | HideSlide | presentation | 1 |
| Impress | InsertColumnsBefore | presentation | 1 |
| Impress | InsertRowsAfter | presentation | 1 |
| Impress | InsertSlideTitleField | presentation | 1 |
| Impress | InsertTimeFieldFix | presentation | 1 |
| Impress | Italic | - | 1 |
| Impress | Sidebar | - | 1 |
| Impress | Spacing | - | 1 |
| Shared builder | Italic | - | 1 |
| Shared builder | Spacing | - | 1 |

## Следующий этап

1. Запустить Playwright для Writer, Calc и Impress на всех 22 языках и собрать инвентарь реально отрендеренного текста.
2. Сравнить английские остатки из рендера с этим статическим отчетом.
3. Для остатков класса `ui-json` пополнять `editor/l10n/overrides/client/<lang>.json` (мёрджит deployed-сборка `editor/Dockerfile.online`; `editor/Dockerfile` — stopgap).
4. Для остатков класса `uno-json` / `lo-core-mo` пересобрать образ с исправленными UNO/LibreOffice-каталогами или явно задокументировать осознанное неисправление, если английское значение является названием продукта или технической командой.
5. Повторно снять скриншоты и визуально проверить каждый измененный перевод перед принятием патча.

