# Фильтрация, сортировка и группировка по типу задачи (work item type)

**Status:** реализовано в рабочем дереве ветки `feat/plane-3-4-work-item-type-filter-sort-group`.
Составлен 2026-08-25. Пройдено: `pnpm check` (0 ошибок), `pytest -m unit` (414 passed),
`pytest -k "issue_type or pit_level or rich_filter"` (56 passed), `ruff check` — чисто.
Осталось: ручная проверка в UI по чеклисту Verification ниже.

## Контекст

В форке типы задач — полноценная сущность: `IssueType` / `ProjectIssueType` в БД, сидинг шести типов
(Task, Story, Subtask, Epic, Bug, Spike) в
[apps/api/plane/utils/issue_type.py](../../apps/api/plane/utils/issue_type.py), `Issue.type` FK, стор
[apps/web/core/store/issue-type.store.ts](../../apps/web/core/store/issue-type.store.ts), рендер иконки
типа в
[apps/web/ce/components/issues/issue-details/issue-identifier.tsx](../../apps/web/ce/components/issues/issue-details/issue-identifier.tsx).

Но тип задачи присутствует в UI только как **display property** («Work Item Types» в панели Display).
Его нет ни в дропдауне Filters, ни в списках Group by / Sub-group by / Order by. Пользователь не может
ни отфильтровать доску по Bug, ни сгруппировать канбан по типам, ни отсортировать список.

Цель: довести тип задачи до уровня остальных свойств (state, priority, cycle, module) — фильтр в
rich-filters, опция Group by / Sub-group by, опция Order by.

**Решения по объёму (согласованы с заказчиком):**

- Фильтр + Order by + Group by/Sub-group by.
- Только проектные страницы: work items проекта, циклы, модули, project views, архив
  (`ISSUE_DISPLAY_FILTERS_BY_PAGE.issues` / `archived_issues`). Workspace-уровень (My work items,
  All issues, profile) — вне объёма: там нужен новый workspace-scoped эндпоинт типов, сейчас
  `IssueTypeViewSet` только project-scoped.
- Сортировка — в порядке настройки типов проекта (`ProjectIssueType.level`), а не по алфавиту.

## Ключевые соглашения кодовой базы

Их нужно соблюсти, иначе фича не поедет:

- Имя rich-filter свойства **должно совпадать** с именем фильтра в `IssueFilterSet`: фронт шлёт
  `{"type_id__in": [...]}` в query-параметре `filters` (JSON), `ComplexFilterBackend` валидирует ключи
  по `filterset_class.base_filters`. Поэтому свойство называем `type_id`.
- Догрузка страницы внутри одной группы идёт **не** через rich-filters, а через legacy flat-параметр:
  `EServerGroupByToFilterOptions[group_by]` → ключ `TIssueParams` → `issue_filters()` в
  [apps/api/plane/utils/issue_filters.py](../../apps/api/plane/utils/issue_filters.py). Значит нужен и
  legacy-фильтр.
- `order_by` санитизируется по `ISSUE_ORDER_BY_ALLOWLIST`; синтетические ключи оформляются как в
  `priority` → аннотация + возврат имени аннотации для курсорного пагинатора.

## Backend (`apps/api`)

1. **[plane/utils/filters/filterset.py](../../apps/api/plane/utils/filters/filterset.py)** — в
   `IssueFilterSet` рядом с `state_id`:

   ```python
   type_id = filters.UUIDFilter(field_name="type_id")
   type_id__in = UUIDInFilter(field_name="type_id", lookup_expr="in")
   ```

   Этого достаточно для rich-фильтра: `_validate_fields` пропустит ключ, `build_combined_q` соберёт `Q`.

2. **[plane/utils/issue_filters.py](../../apps/api/plane/utils/issue_filters.py)** — legacy-фильтр для
   догрузки группы. Новая `filter_issue_type` по образцу `filter_cycle` (строка 346): поддержать
   `"None"` → `type_id__isnull=True`, остальное через `filter_valid_uuids` → `type_id__in`.
   Зарегистрировать в словаре `ISSUE_FILTER` под ключом `"issue_type"` (этот ключ уже есть в
   `TIssueParams`).

3. **[plane/utils/grouper.py](../../apps/api/plane/utils/grouper.py)** — в `issue_group_values` ветка
   для `"type_id"`: вернуть id типов проекта (через
   `IssueType.objects.filter(project_issue_types__project_id=..., project_issue_types__deleted_at__isnull=True)`,
   `.distinct()`) + `"None"`, по образцу веток `cycle_id` / `issue_module__module_id`.
   `issue_on_results` править не нужно — `type_id` уже в `required_fields` (строка 125).

4. **[plane/utils/order_queryset.py](../../apps/api/plane/utils/order_queryset.py)** — добавить
   `"type__level"` в `ISSUE_ORDER_BY_ALLOWLIST` и спец-ветку в `order_issue_queryset` (по образцу
   `priority`): аннотация `work_item_type_order` =
   `Subquery(ProjectIssueType.objects.filter(issue_type_id=OuterRef("type_id"), project_id=OuterRef("project_id"), deleted_at__isnull=True).values("level")[:1])`,
   сортировка с `nulls_last`, вернуть `"work_item_type_order"` / `"-work_item_type_order"` как
   `order_by_param`.

   Порядок берём из `ProjectIssueType.level`, а не `IssueType.level`: сериализатор отдаёт фронту именно
   `pit_level`
   ([apps/api/plane/app/serializers/issue_type.py](../../apps/api/plane/app/serializers/issue_type.py)),
   и настройки проекта упорядочены по нему.

5. **[plane/utils/filters/converters.py](../../apps/api/plane/utils/filters/converters.py)** — в
   `LegacyToRichFiltersConverter` добавить `"issue_type": "type_id"` в `DEFAULT_FIELD_MAPPINGS` и
   `"type_id"` в `DEFAULT_UUID_FIELDS`, чтобы сохранённые вьюхи со старым форматом мигрировали
   корректно.

## Types (`packages/types`)

- [src/view-props.ts](../../packages/types/src/view-props.ts): `"type_id"` →
  `WORK_ITEM_FILTER_PROPERTY_KEYS`; `"work_item_type"` → `TIssueGroupByOptions`;
  `"type__level" | "-type__level"` → `TIssueOrderByOptions`.
- [src/issues.ts](../../packages/types/src/issues.ts): `"work_item_type"` → `GroupByColumnTypes`.

Компилятор сам подсветит все обязательные `Record<...>`, которые после этого станут неполными — это
основной способ найти забытые места.

## Constants (`packages/constants`)

- [src/issue/common.ts](../../packages/constants/src/issue/common.ts):
  `EIssueGroupByToServerOptions["work_item_type"] = "type_id"`;
  `EIssueGroupBYServerToProperty["type_id"] = "type_id"`; запись в `ISSUE_GROUP_BY_OPTIONS` и в
  `ISSUE_ORDER_BY_OPTIONS` (ключ `"type__level"`).
- [src/issue/filter.ts](../../packages/constants/src/issue/filter.ts):
  `EServerGroupByToFilterOptions["type_id"] = "issue_type"`; `"type_id"` в
  `ISSUE_DISPLAY_FILTERS_BY_PAGE.issues.filters` и `archived_issues.filters`; `"work_item_type"` в
  `group_by`/`sub_group_by` для layout'ов `list` и `kanban`; `"type__level"` в `order_by` для `list`,
  `kanban`, `spreadsheet`, `gantt_chart`.

## Rich-filter config (`packages/utils`)

Новый `packages/utils/src/work-item-filters/configs/filters/work-item-type.ts` — точная калька
[cycle.ts](../../packages/utils/src/work-item-filters/configs/filters/cycle.ts):
`getWorkItemTypeFilterConfig<P>(key)` c `getMultiSelectConfig<TIssueType, string, TLogoProps>`,
`items: params.workItemTypes`, `getIconData: (type) => type.logo_props`, оператор
`COLLECTION_OPERATOR.IN`. React в этом пакете нет — иконка приходит через `getOptionIcon` из хука.
Экспорт из
[configs/filters/index.ts](../../packages/utils/src/work-item-filters/configs/filters/index.ts).

## Web (`apps/web`)

- **[core/hooks/work-item-filters/use-work-item-filters-config.tsx](../../apps/web/core/hooks/work-item-filters/use-work-item-filters-config.tsx)**:
  добавить `workItemTypeIds?: string[]` в `TWorkItemFiltersEntityProps`, резолвить типы через
  `useIssueType().getIssueTypeById`, собрать `workItemTypeFilterConfig` с
  `isEnabled: isFilterEnabled("type_id") && workItemTypes !== undefined && workItemTypes.length > 0`
  (гейт по образцу `project?.cycle_view === true` у циклов),
  `getOptionIcon: (logoProps) => <Logo logo={logoProps} size={12} />`,
  `label: t("work_item_types.label_singular")`. Добавить в массив `configs` и в `configMap`.
- **[core/components/work-item-filters/filters-hoc/project-level.tsx](../../apps/web/core/components/work-item-filters/filters-hoc/project-level.tsx)**:
  прокинуть `workItemTypeIds={getProjectIssueTypeIds(projectId)}` из `useIssueType()` в
  `WorkItemFiltersHOC` — рядом с `cycleIds` / `labelIds` / `stateIds`. Типы уже подгружаются в
  [core/layouts/auth-layout/project-wrapper.tsx:140](../../apps/web/core/layouts/auth-layout/project-wrapper.tsx)
  при включённом `is_issue_type_enabled`, отдельный fetch не нужен.
- **[core/components/issues/issue-layouts/utils.tsx](../../apps/web/core/components/issues/issue-layouts/utils.tsx)**:
  новый `getWorkItemTypeColumns({ projectId })` по образцу `getStateColumns` — берёт
  `store.issueType.getProjectIssueTypes(projectId ?? store.router.projectId)` (уже отсортированы по
  level), иконка `<Logo logo={type.logo_props} size={14} />`, `payload: { type_id: type.id }`, плюс
  колонка `"None"`. Зарегистрировать в `groupByColumnMap`.
- **[core/store/issue/helpers/base-issues.store.ts](../../apps/web/core/store/issue/helpers/base-issues.store.ts)**:
  `ISSUE_GROUP_BY_KEY.work_item_type = "type_id"`, `ISSUE_FILTER_DEFAULT_DATA.work_item_type = "type_id"`,
  `ISSUE_ORDERBY_KEY["type__level"] = "type_id"` и `["-type__level"] = "type_id"`.
- **[ce/components/issues/issue-layouts/utils.tsx](../../apps/web/ce/components/issues/issue-layouts/utils.tsx)**:
  в `useGroupByOptions` скрывать `work_item_type`, когда у проекта нет типов — ровно тем же приёмом,
  что уже применён к `board_column` (`hasBoardColumns`).
- Drag & drop между колонками типов **не включаем**: `work_item_type` не добавляем в
  `DRAG_ALLOWED_GROUPS`, поэтому `list-group.tsx` / `kanban-group.tsx` автоматически отключат
  перетаскивание. Quick-add внутри группы при этом работает — тип подставится из `payload`.

## i18n (`packages/i18n`)

- `work-item-type.json`: новый ключ `work_item_types.label_singular` = «Work item type» (существующий
  `label` — «Work item Types», множественное число, годится для Group by, но не для Filters/Order by).
- Прогнать через скилл `/translate` по всем 19 локалям в `packages/i18n/src/locales`.

## Тесты

- Backend, рядом с
  [plane/tests/contract/app/test_issue_type_app.py](../../apps/api/plane/tests/contract/app/test_issue_type_app.py):
  фильтрация списка по `filters={"type_id__in": [...]}`; legacy-параметр `issue_type=<uuid>` и
  `issue_type=None`; `group_by=type_id` — проверить состав `group_by_fields`; `order_by=type__level` —
  проверить, что порядок совпадает с `ProjectIssueType.level` и что задачи без типа идут в конец.

  ```bash
  docker compose -f docker-compose-test.yml run --rm api-tests pytest -k issue_type
  ```

- Frontend: unit на `getGroupedWorkItemIds` с `groupByKey="work_item_type"` в существующем наборе
  тестов store-хелперов (если он есть — иначе ограничиться ручной проверкой).

## Verification

1. Пересобрать API: `docker compose -f docker-compose-local.yml up -d --build --force-recreate api`,
   фронт — `pnpm dev` (API на порту 8002 в этом чекауте).
2. Проект с включённым `is_issue_type_enabled` → Work items:
   - Filters → в списке появился «Work item type», выбрать Bug — в списке только баги, чип фильтра
     отрисован в строке применённых фильтров, URL/сохранение в user properties переживает reload.
   - Display → Group by → Work item type: колонки в порядке Task, Story, Subtask, Epic, Bug, Spike +
     «None»; в канбане то же плюс Sub-group by; перетаскивание между колонками недоступно; quick-add в
     колонке создаёт задачу с этим типом.
   - Display → Order by → Work item type: порядок совпадает с настройками проекта (Settings → Work item
     types), задачи без типа в конце; проверить в list и spreadsheet.
   - Проскроллить группу до догрузки следующей страницы — убедиться, что элементы не «протекают» из
     других типов (это проверка legacy-фильтра `issue_type`).
3. Повторить на страницах цикла, модуля и project view; сохранить view с фильтром по типу и
   переоткрыть — фильтр восстановился.
4. Проект с выключенными типами задач: «Work item type» отсутствует и в Filters, и в Group by,
   и не ломает Display-панель.
5. `pnpm check` (format + lint + types) и
   `docker compose -f docker-compose-test.yml run --rm api-tests pytest -m unit`.
