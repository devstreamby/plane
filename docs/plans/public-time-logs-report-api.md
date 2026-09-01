# Публичный API: отчёт по time logs одним запросом

**Status:** реализовано в ветке `feat/PLANE-8-public-time-logs-report`.
Составлен 2026-09-01. Задача — [PLANE-8](https://plane.devstream.by/devstream/projects/bd3a3d28-fa93-47b9-8857-61e8dd9c0a1d/issues/f36ddf84-14a9-4721-a3c8-bcaa51c3b8eb).
Пройдено: новые контрактные тесты (9 passed), `pytest plane/tests/contract/` (222 passed,
8 предсуществующих падений в `contract/app/test_authentication.py::TestMagic*` — воспроизводятся
и на чистом `preview`), `ruff check` — чисто, `manage.py spectacular` — схема генерируется без
ошибок по новым вьюхам.

## Контекст

Внешний `report-generator` строил месячный Excel, обходя задачи проекта постранично и запрашивая
`GET /api/v1/workspaces/{slug}/projects/{project_id}/work-items/{issue_id}/time-logs/` по каждой
задаче с ненулевым `total_time_spent`. Порядка 300 запросов на три проекта, при
`API_KEY_RATE_LIMIT=60/minute` — около пяти минут почти целиком в троттлинге.

Хуже того, перечисление задач в публичном API идёт через `Issue.issue_objects`, а этот менеджер
исключает archived, draft и triage. Часы на архивных задачах в отчёт не попадали, и обойти это
снаружи было нельзя: `archived-issues` живёт только в app API под сессионной авторизацией.

Нужная агрегация уже была — `build_time_log_report()`, — но выставлена только на app API, где
`BaseAPIView` использует `BaseSessionAuthentication`, то есть по `X-API-Key` недоступна.

## Что сделано

### 1. Агрегатор вынесен в `plane/utils/time_report.py`

`build_time_log_report()` вместе с хелперами дат переехал из
[app/views/analytic/time_report.py](../../apps/api/plane/app/views/analytic/time_report.py) в
[utils/time_report.py](../../apps/api/plane/utils/time_report.py). Причина — `plane/api/` нигде не
импортирует `plane.app.views`, и заводить такую связь ради переиспользования не хотелось. В app-модуле
остались только два сессионных эндпоинта, логика не дублируется: оба API считают по одному коду.
`_split_ids` переименован в публичный `split_ids`, `ROLE` берётся из `plane.db.models.project`,
чтобы утилита не тянула `plane.app.permissions`.

В докстринге функции зафиксировано контрактом то, что раньше было побочным эффектом: выборка идёт
от `IssueTimeLog` и **не** должна фильтроваться через `Issue.issue_objects` — иначе часы на
архивных, черновых и triage-задачах молча пропадут.

### 2. Новые эндпоинты публичного API

[api/views/time_report.py](../../apps/api/plane/api/views/time_report.py), наследуются от
`plane/api/views/base.py::BaseAPIView` — значит работают `APIKeyAuthentication` и
`ApiKeyRateThrottle`:

- `GET /api/v1/workspaces/{slug}/time-logs-report/` — `WorkspaceEntityPermission`
- `GET /api/v1/workspaces/{slug}/projects/{project_id}/time-logs-report/` — `ProjectEntityPermission`

Параметры: `start_date`, `end_date` (обязательные, `YYYY-MM-DD`), `project_ids`, `user_ids`
(опциональные, через запятую) — как в app-версии, плюс новый `strict` (см. ниже).
Маршруты — [api/urls/time_report.py](../../apps/api/plane/api/urls/time_report.py).

### 3. Payload дополнен

Чтобы потребителю не требовались дополнительные запросы:

| Где      | Поле                      | Зачем                                                                           |
| -------- | ------------------------- | ------------------------------------------------------------------------------- |
| `issues` | `state_name`              | колонка Current status в отчёте                                                 |
| `issues` | `archived`                | явный признак архивной задачи вместо догадок                                    |
| `users`  | `email`                   | восстановление ФИО, когда у импортированного из EVA аккаунта пустой `last_name` |
| корень   | `restricted_project_ids`  | проекты, по которым отданы только собственные логи                              |
| корень   | `unavailable_project_ids` | запрошенные проекты, к которым у владельца токена нет доступа                   |

`state_name` берётся через `select_related("issue__state")`, лишних запросов не добавляет.
`email` безопасен: фильтр видимости и так ограничивает `users` самим вызывающим плюс участниками
проектов, где он админ. Поля аддитивные — веб-клиент
([time-report.service.ts](../../apps/web/core/services/time-report.service.ts), типы обновлены)
и сессионные эндпоинты продолжают работать без изменений.

### 4. Права доступа: явный признак вместо тихого усечения

Поведение `build_time_log_report()` сохранено: чужие логи отдаются только по проектам, где
пользователь админ проекта либо админ воркспейса, иначе — только свои и `can_view_others: false`.
Ловушку «молча неполный отчёт» закрыли двумя способами:

- в ответе всегда есть `restricted_project_ids` и `unavailable_project_ids` — потребитель видит,
  где данные урезаны;
- `?strict=true` превращает такой случай в `403` с перечислением обеих групп проектов.

Безусловный `403` не делали: он сломал бы законный сценарий, когда рядовой участник тянет по
токену собственные часы по проекту, где он не админ. `strict` даёт генератору отчётов ровно то,
что нужно, — падать громко, — не забирая эту возможность у остальных.

### 5. Ограничение периода

`MAX_REPORT_RANGE_DAYS = 92` не менялся. Тест фиксирует, что выход за лимит даёт `400` с текстом,
где упомянуто число дней; отсутствие дат — `400` с упоминанием `start_date`.

### 6. Документация

Схема drf-spectacular: декоратор `time_report_docs` и параметры `REPORT_*` в
[utils/openapi](../../apps/api/plane/utils/openapi/), сериализаторы ответа (только для схемы) в
[api/serializers/time_report.py](../../apps/api/plane/api/serializers/time_report.py), новый тег
`Time Tracking` в [settings/openapi.py](../../apps/api/plane/settings/openapi.py). В описании
эндпоинта отдельно сказано, что архивные задачи включены всегда, что незакрытые таймеры не
отдаются и какие права нужны токену.

### 7. Тесты

[tests/contract/api/test_time_log_report_api.py](../../apps/api/plane/tests/contract/api/test_time_log_report_api.py) — 9 тестов:
агрегация по дням, включение archived/draft/triage (ключевой критерий приёмки), игнорирование
незакрытых таймеров, project-scoped выборка, `400` на плохой период, `401` без ключа,
`restricted_project_ids` и `strict` для рядового участника, `unavailable_project_ids`.

## Не сделано (отдельной задачей)

`API_KEY_RATE_LIMIT` на проде остаётся `60/minute`. Это переменная окружения
([common.py](../../apps/api/plane/settings/common.py), значение по умолчанию в `.env.example`),
менять её нужно на хосте `plane` по стандартной процедуре деплоя. С новым эндпоинтом месячный
отчёт укладывается в 1–3 запроса, так что срочности больше нет, но поднять лимит до `600/minute`
всё равно стоит ради остальных интеграций.

## Примечание при переходе на новый эндпоинт

`build_time_log_report()` считает не по сохранённому полю `date`, а раскладывает интервал
`started_at`–`stopped_at` по локальным датам воркспейса и игнорирует незакрытые таймеры
(`stopped_at IS NULL`). Текущая реализация в генераторе фильтрует по `date`. На стыках суток и по
«висящим» таймерам числа могут немного разойтись — при переключении это надо сверить на одном и
том же периоде.
