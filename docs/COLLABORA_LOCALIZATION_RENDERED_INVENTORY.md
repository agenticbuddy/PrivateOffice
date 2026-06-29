# Rendered-инвентаризация локализации Collabora Online

Это второй этап после статической инвентаризации. Здесь проверялся не код и не наличие ключей в JSON, а то, что реально отрисовывает Collabora Online в браузере.

## Область проверки

- URL: `http://localhost:8088`
- Инструмент: Playwright из `e2e/`
- Приложения: Writer, Calc, Impress
- Языки: все 22 языка проекта
- На каждый язык: 36 сценариев
- Всего сценариев: 792
- Проверенные состояния: начальное открытие editor, все видимые вкладки notebookbar, одно context menu на canvas для каждого приложения
- Text/JSON dumps: для всех 792 сценариев
- Screenshots: 132, режим `main` - initial и context-menu для каждого языка и приложения

## Артефакты

Основной каталог:

```text
.qa/l10n-rendered/
```

Содержимое:

| Файл/каталог | Что доказывает |
| --- | --- |
| `scenario_manifest.json` | Какие сценарии должны были быть выполнены |
| `run_manifest.json` | Какие сценарии реально выполнены, с путями к артефактам |
| `visible-text.jsonl` | Машиночитаемый visible text inventory |
| `english-leftovers.csv` | Exact-match кандидаты английских остатков относительно `en` baseline |
| `text/` | Нормализованные text dumps |
| `json/` | DOM/control dumps: text, aria-label, title, id, class |
| `screenshots/` | Скриншоты initial/context-menu |
| `REPORT.md` | Автоматическая техническая сводка collector |

## Что сохраняется в репозитории

В репозитории сохраняются:

- этот Markdown-отчет;
- collector `e2e/scripts/editor-l10n-rendered.mjs`;
- npm-команда `editor-l10n`;
- методические документы по локализации.

Не сохраняются:

- `.qa/l10n-rendered/`;
- `e2e/.qa/l10n-rendered-smoke/`;
- screenshots;
- JSON/text dumps;
- Playwright reports и traces.

Эти данные регенерируемые и тяжелые. Для повторения достаточно запустить collector снова против той же версии проекта и Collabora baseline.

Smoke-прогон перед полным проходом:

```text
e2e/.qa/l10n-rendered-smoke/
```

## Инварианты выполнения

| Проверка | Значение |
| --- | --- |
| Expected scenarios | 792 |
| Executed scenarios | 792 |
| Failed/skipped | 0 |
| Unique `scenario_id` в expected | 792 |
| Unique `scenario_id` в run | 792 |
| JSON dumps | 792 |
| Text dumps | 792 |
| Screenshots | 132 |
| Writer scenarios | 264 |
| Calc scenarios | 264 |
| Impress scenarios | 264 |
| Scenarios per locale | 36 |

Эти числа сходятся: прогон был полным для заявленной области.

## Важное ограничение

`english-leftovers.csv` - это не финальный список переводов.

Он строится как точное совпадение с английским baseline в том же приложении и состоянии. Поэтому там есть реальные проблемы и ожидаемый шум:

- стили Writer вроде `No Spacing`, `Quote`, `Intense Quote`;
- размеры страниц вроде `B5 (ISO)`, `Legal`, `Tabloid`;
- accessibility labels вроде `Status Bar Menu`, `Dialog dropdown`;
- технические подписи вроде `Online Editor`;
- строки, которые могут оставаться английскими намеренно.

Этот CSV нужен как вход для triage, а не как готовый patch list.

## Raw candidate leftovers

| Метрика | Значение |
| --- | --- |
| Всего raw candidate rows | 23607 |
| Writer | 6919 |
| Calc | 8058 |
| Impress | 8630 |

По языкам:

| Язык | Raw candidate rows |
| --- | --- |
| hi | 3897 |
| fa | 3797 |
| th | 3689 |
| ko | 1508 |
| vi | 1381 |
| ja | 1126 |
| ar | 1044 |
| he | 867 |
| tr | 786 |
| ru | 760 |
| pt-BR | 689 |
| it | 687 |
| fr | 565 |
| nl | 448 |
| cs | 444 |
| id | 408 |
| pl | 394 |
| de | 314 |
| uk | 284 |
| es | 277 |
| zh-CN | 242 |

## Термины со скриншотов и близкие к ним строки

Таблица ниже показывает, где английская строка реально осталась видимой в rendered dumps. Это не список исправлений: каждая строка еще должна пройти source-class triage и collision analysis.

| Английская строка | Где реально видна | Приложение |
| --- | --- | --- |
| `Function Library` | ru, it, tr, ja, ko, hi, th, ar, fa | Calc |
| `AutoSum` | de, pt-BR, ru, tr, ja, ko, hi, th, ar, fa | Calc |
| `Logical` | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | Calc |
| `Date & Time` | ru, tr, ja, ko, hi, th, ar, fa | Calc |
| `Math & Trig` | fr, pt-BR, ru, tr, ja, ko, hi, th, ar, fa | Calc |
| `Financial` | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | Calc |
| `Lookup & Reference` | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | Calc |
| `Insert Function` | ru, tr, ja, ko, hi, th, ar, fa | Calc |
| `More Functions` | ru, tr, ja, ko, hi, th, ar, fa | Calc |
| `Range` | pt-BR, ru, tr, ja, ko, hi, th, ar, fa | Calc |
| `Pivot Calculated Field` | es, pt-BR, ru, it, nl, pl, uk, tr, cs, zh-CN, ja, ko, hi, vi, id, th, ar, he, fa | Calc |
| `Table` | es, pt-BR, ru, it, nl, pl, uk, tr, cs, zh-CN, ja, ko, hi, vi, id, th, ar, he, fa | Calc |
| `Category` | es, pt-BR, ru, it, nl, pl, uk, tr, cs, zh-CN, ja, ko, hi, vi, id, th, ar, he, fa | Calc |
| `Sheet` | es, de, fr, pt-BR, ru, it, nl, pl, uk, tr, cs, zh-CN, ja, ko, hi, vi, id, th, ar, he, fa | Calc |
| `Number Format` | es, pt-BR, ru, it, nl, pl, uk, tr, cs, zh-CN, ja, ko, hi, vi, id, th, ar, he, fa | Calc |
| `Illustrations` | fr, tr, ja, ko, hi, th, fa | Writer, Calc, Impress |
| `Formula to Value` | hi, vi | Calc |
| `Line` | hi, th, fa | Impress |

## Примеры, которые подтверждают наблюдения

RU Calc Formula tab:

```text
.qa/l10n-rendered/text/ru__calc__tab-Formula.txt
```

В этом dump видны английские:

```text
Insert Function
AutoSum
Financial
Logical
Date & Time
Lookup & Reference
Math & Trig
More Functions
Function Library
Range
Category
Sheet
```

UK Calc Formula tab:

```text
.qa/l10n-rendered/text/uk__calc__tab-Formula.txt
```

В нем формульные группы уже переведены, но остаются английские `Category` и `Sheet`.

ZH-CN Calc Formula tab:

```text
.qa/l10n-rendered/text/zh-CN__calc__tab-Formula.txt
```

Формульные группы переведены, но остаются английские `Category` и `Sheet`.

Calc Insert tab для `Pivot Calculated Field` и `Table`:

```text
.qa/l10n-rendered/text/ru__calc__tab-Insert.txt
.qa/l10n-rendered/text/uk__calc__tab-Insert.txt
.qa/l10n-rendered/text/zh-CN__calc__tab-Insert.txt
.qa/l10n-rendered/text/ar__calc__tab-Insert.txt
```

Эти строки реально видны английскими во многих языках, включая те, где часть browser JSON уже содержит переводы. Это подтверждает, что их нельзя исправлять только по принципу "добавить ключ в `ui-*.json`" без проверки фактического source class.

## Что это меняет относительно статического отчета

Статический отчет сказал, где строка может жить. Rendered отчет подтвердил, где она реально видна.

Подтверждения:

- RU/AR/HI/TH/FA Formula tab действительно показывают английские прямые browser labels.
- `Pivot Calculated Field` и `Table` действительно остаются английскими на Calc Insert tab в большом числе языков.
- `Category`, `Sheet`, `Number Format` повторяются как rendered leftovers в Calc, что делает их высокоприоритетными для source tracing.
- `Illustrations` уже не является RU/AR проблемой в текущем rendered проходе, но остается английским в нескольких других языках.

## Следующий шаг

Нельзя сразу превращать `english-leftovers.csv` в patch.

Следующий этап:

1. Соединить rendered leftovers с occurrence map из статического отчета.
2. Для каждой строки определить source class: `ui-json`, `uno-json`, `lo-core-mo`, unresolved.
3. Отфильтровать false positives: стили, форматы страниц, технические имена, допустимые английские значения.
4. Построить collision map по реально видимым leftovers.
5. Выделить safe direct `ui-json` candidates.
6. Для `Pivot Calculated Field`, `Table`, `Category`, `Sheet`, `Number Format` сделать отдельный source trace перед любым патчем.
7. После точечных правок повторить этот же collector и сравнить before/after manifests.
