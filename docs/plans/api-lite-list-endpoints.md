# `-lite` эндпоинты внешнего API (совместимость с plane-mcp-server)

**Status:** реализовано в ветке `feat/api-lite-list-endpoints`.
Составлен 2026-08-28. Пройдено: новые контрактные тесты (14 passed), полный
`pytest plane/tests/contract/` (213 passed), `ruff check` — чисто.

## Контекст

Официальный [plane-mcp-server](https://github.com/makeplane/plane-mcp-server) настроен на
`https://plane.devstream.by` через `.mcp.json` в проектах `plane` и `second_brain`. Четыре его
list-действия не работали против нашего инстанса:

| Действие MCP            | Эндпоинт                                             | Наш инстанс |
| ----------------------- | ---------------------------------------------------- | ----------- |
| `project list`          | `GET /workspaces/{slug}/projects-lite/`              | **404**     |
| `member list_workspace` | `GET /workspaces/{slug}/members-lite/`               | **404**     |
| `cycle list`            | `GET /workspaces/{slug}/projects/{id}/cycles-lite/`  | **404**     |
| `module list`           | `GET /workspaces/{slug}/projects/{id}/modules-lite/` | **404**     |

Обычные `/projects/`, `/members/`, `/cycles/`, `/modules/` отвечают 200 — клиент просто новее
сервера. Роутов `-lite` не было нигде в `apps/api/plane/api/urls/`: upstream добавил их уже
после точки, от которой отпочкован форк.

Это discovery-действия (найти id проекта, разрезолвить исполнителя), поэтому без них MCP
неудобен в ежедневной работе. Альтернативу — откатить MCP-сервер на 0.2.9, последнюю версию
перед миграцией на `-lite` в 0.2.10 — отклонили: она даёт 109 плоских инструментов вместо 30
сгруппированных и замораживает тулинг на июне 2026.

## Что сделано

Все три lite-сериализатора уже существовали во внешнем API и совпадают с тем, что ожидают
pydantic-модели SDK — переиспользованы как есть:

- [ProjectLiteSerializer](../../apps/api/plane/api/serializers/project.py)
- [CycleLiteSerializer](../../apps/api/plane/api/serializers/cycle.py) (`fields = "__all__"`)
- [ModuleLiteSerializer](../../apps/api/plane/api/serializers/module.py) (`fields = "__all__"`)

`BaseAPIView.paginate()` из [paginator.py](../../apps/api/plane/utils/paginator.py) уже отдаёт
ровно тот конверт, который ждёт `PaginatedResponse` SDK (`total_count`, `next_cursor`,
`next_page_results`, …), и по умолчанию использует `per_page=1000` с тем же потолком. Поэтому
работа свелась к четырём тонким read-only вьюхам и роутам.

### projects-lite

`ProjectLiteListAPIEndpoint` — те же правила видимости, что у GET
`ProjectListCreateAPIEndpoint` (участник проекта ИЛИ `network=2`), но без единого `annotate()`:
lite-форме счётчики не нужны. Параметр `include_archived` (по умолчанию false) и `order_by`.
В `ProjectLiteSerializer` добавлено поле `archived_at` — без него `include_archived` бессмысленен,
и оно есть в документированной lite-форме.

### members-lite

`WorkspaceMemberLiteAPIEndpoint`. Два осознанных отличия от существующего `/members/`, который
не тронут:

- Отдаёт **пагинированный конверт**, а не голый массив, и сериализует только страницу, а не всех
  участников воркспейса разом.
- Доступен **любому активному участнику** (`WorkspaceEntityPermission`), а не только админам.
  Резолв исполнителей — повседневная операция, а поля (имя, email, роль) и так видны каждому
  участнику в UI. Решение согласовано с заказчиком; на него есть отдельный тест, который
  упадёт, если вьюху переключат обратно на `WorkSpaceAdminPermission`.

### cycles-lite

`CycleLiteListAPIEndpoint`. Предикаты фильтрации по статусу вынесены из
`CycleListCreateAPIEndpoint.get` в общую функцию `filter_cycles_by_status()`, чтобы два
эндпоинта не разъехались. Существующий эндпоинт переведён на неё — поведение сохранено
один в один.

Два отличия от полного списка:

- Статус приходит как `status`; алиаса `cycle_view` тут нет.
- **Все** бакеты, включая `current`, отвечают пагинированным конвертом. Полный список для
  `current` отдаёт голый массив; SDK явно документирует, что lite-роут так не делает. Скопировать
  этот кунштюк — значит сломать `cycle list` ровно на одном значении статуса, что легче всего
  не заметить. На это есть отдельный тест.

### modules-lite

`ModuleLiteListAPIEndpoint` — самый простой: фильтр по членству, `order_by`, курсорная
пагинация, без дополнительных фильтров.

## Тесты

[test_lite_endpoints.py](../../apps/api/plane/tests/contract/api/test_lite_endpoints.py) —
14 контрактных тестов. Ключевые:

- форма пагинированного конверта содержит все ключи, которых требует `PaginatedResponse` SDK;
- `projects-lite`: архивный проект скрыт по умолчанию и появляется при `include_archived=true`;
- `members-lite`: конверт, а не голый массив; в каждой строке есть `role`; **не-админ получает
  200**; посторонний — 403;
- `cycles-lite`: `status=current` всё ещё пагинируется.

```bash
docker compose -f docker-compose-test.yml run --rm api-tests pytest plane/tests/contract/api/test_lite_endpoints.py -v
```

## Развёртывание

Прод продолжит отвечать 404 до пересборки образа — деплой делается отдельно и только по явному
запросу, по процедуре из [CLAUDE.md](../../CLAUDE.md).

## Вне объёма

- Деплой на прод.
- Любые изменения существующих `/projects/`, `/members/`, `/cycles/`, `/modules/` — кроме
  вынесения фильтра циклов в общий хелпер, которое поведение не меняет.
