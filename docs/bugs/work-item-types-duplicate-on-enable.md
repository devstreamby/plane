# Work item types: duplicated on enable, undeletable via trash icon

**Status:** fixed 2026-08-25 on `fix/plane-8-work-item-types-duplicates`. Found
2026-08-19 while cleaning up duplicate issue types on the `neodoc` workspace
(project `NDOC`) on prod.

## Symptom

When "work item types" is turned on for a project, the six default types
(Task, Story, Subtask, Epic, Bug, Spike) are sometimes created **twice** —
two rows per name show up in the settings list. Trying to delete the extra
copies via the trash icon appears to do nothing: the confirm dialog closes,
no error, but the duplicate stays in the list forever.

This is actually two independent bugs that combine to produce that symptom.

## Bug A — duplicate creation (race condition, no unique constraint)

`ensure_default_issue_types()` ([apps/api/plane/utils/issue_type.py:33](../../apps/api/plane/utils/issue_type.py))
is called from two different request paths that can fire close together:

1. `ProjectViewSet.partial_update` ([apps/api/plane/app/views/project/base.py:371](../../apps/api/plane/app/views/project/base.py)) —
   runs synchronously inside the `PATCH` that sets `is_issue_type_enabled=True`.
   This is what fires when the frontend's `handleEnable()` calls `updateProject(...)`
   ([apps/web/core/components/work-item-types/root.tsx:52-60](../../apps/web/core/components/work-item-types/root.tsx)).
2. `IssueTypeViewSet.list` ([apps/api/plane/app/views/issue_type/base.py:44-50](../../apps/api/plane/app/views/issue_type/base.py)) —
   runs whenever the type list is empty. The frontend's `useSWR` in
   `WorkItemTypesRoot` starts fetching the list the moment `isEnabled` flips
   true, which can land at nearly the same instant as the enabling `PATCH`
   commits.

Both paths call:

```python
IssueType.objects.get_or_create(
    workspace_id=project.workspace_id,
    name=name,
    defaults={"is_active": True, "is_epic": is_epic, "logo_props": logo_props},
)
```

`IssueType` ([apps/api/plane/db/models/issue_type.py:14](../../apps/api/plane/db/models/issue_type.py))
has **no unique constraint on `(workspace, name)`** — only `ProjectIssueType`
has one, on `(project, issue_type)`. `get_or_create` is only atomic against
concurrent calls when a DB constraint backs it; without one it's a classic
TOCTOU race: both requests' `SELECT` finds no existing row, both `INSERT`
succeed, and the workspace ends up with two `IssueType` rows sharing the
same name. Each gets its own `ProjectIssueType` link, so both show up in
the project's type list.

Observed on prod: duplicate pairs were created ~1ms apart (e.g. two `Bug`
rows at `08:05:32.067370` and `08:05:32.068310`), which matches two
near-simultaneous requests rather than a single accidental double-click.

## Bug B — delete (trash icon) silently no-ops

`IssueTypeViewSet.destroy` ([apps/api/plane/app/views/issue_type/base.py:99-119](../../apps/api/plane/app/views/issue_type/base.py))
only flips `is_active = False`. It never sets `deleted_at` on `IssueType`
or on the `ProjectIssueType` link.

`IssueTypeViewSet.get_queryset` ([apps/api/plane/app/views/issue_type/base.py:24-42](../../apps/api/plane/app/views/issue_type/base.py))
— used by both `list` and `destroy`'s own lookup — filters only on
`project_issue_types__deleted_at__isnull=True`, **never on `is_active`**.

The frontend mirrors this exactly:

- `issueTypeStore.getProjectIssueTypes()` ([apps/web/core/store/issue-type.store.ts:79-84](../../apps/web/core/store/issue-type.store.ts))
  returns every entry in the local map, no `is_active` filter.
- `deleteIssueType()` ([apps/web/core/store/issue-type.store.ts:141-146](../../apps/web/core/store/issue-type.store.ts))
  calls the `DELETE` endpoint (which succeeds, 204) and then patches the
  local map entry to `{ ...existing, is_active: false }` — it never removes
  the entry from the map.

Net effect: click trash → confirm → request succeeds → item is patched to
`is_active: false` → immediately re-rendered anyway because nothing, front
or back, filters on `is_active`. The row never disappears. This is exactly
why the duplicates found on prod came in pairs of one `is_active=True` +
one `is_active=False`: someone had already tried the trash icon on the
extra copy, and it silently failed.

## Prod cleanup already done (2026-08-19)

6 duplicate `IssueType` rows (the `is_active=False` half of each pair) were
soft-deleted directly via Django shell on `neodoc` / project `NDOC`
(`6c48e7b2-cf08-440f-aac5-bd2a38d39a61`) — `deleted_at` set on both the
`IssueType` row and its `ProjectIssueType` link. None of the removed rows
were referenced by any `Issue`. Verified afterward that the project's
`get_queryset()` returns exactly 6 types (Task, Story, Subtask, Epic, Bug,
Spike), each `is_active=True`. This was a data fix only — the underlying
code bugs below are still present and will reproduce the same mess the
next time someone enables work item types on a project, or clicks trash on
one.

## Fix

Three changes, because Bug B's fix is undone by a third problem found while
implementing it.

**Bug A — `IssueType(workspace, name)` is now unique.**
[apps/api/plane/db/models/issue_type.py](../../apps/api/plane/db/models/issue_type.py)
gained a partial `UniqueConstraint` scoped to `deleted_at IS NULL`, mirroring
`ProjectIssueType`. That is what makes `get_or_create` atomic: the losing request
now hits an `IntegrityError`, which `get_or_create` catches and resolves by
re-reading the winner's row. Migration
[0129_issuetype_unique_workspace_name](../../apps/api/plane/db/migrations/0129_issuetype_unique_workspace_name.py)
merges pre-existing duplicates before adding the constraint: the surviving row is
the active one (a deactivated survivor could not be set as a project default),
tie-broken by work item count then age. Work items and draft work items are
repointed at the survivor, project links are moved across, and a link that would
collide with one the survivor already has is dropped — carrying its `is_default`
flag over first so the project is not left without a default type.

`ensure_default_issue_types()` also switched its `ProjectIssueType` lookup to
`get_or_create`; the previous `filter().first()` then `create()` had the same race
against `ProjectIssueType`'s own constraint, which would have surfaced as a 500 on
the enabling `PATCH`.

The serializer's `validate_name` no longer filters on `is_active`. A deactivated
type still holds its name at the DB level, so the old check would have let a
colliding name through to the constraint and returned a 500 instead of a 400.

**Bug B — `destroy()` performs a real soft delete.**
[apps/api/plane/app/views/issue_type/base.py](../../apps/api/plane/app/views/issue_type/base.py)
sets `deleted_at` on the `ProjectIssueType` link, which is what `get_queryset()`
actually filters on. `is_active` is left alone: it is the activate/deactivate
toggle the list item's `ToggleSwitch` drives, not a delete marker, so filtering
the queryset on it (the other option in the original writeup) would have made
deactivating a type hide it.

Types are workspace-scoped and shared by every project that links them, so the
`IssueType` row itself is only soft-deleted once no live link remains — otherwise
deleting `Bug` in one project would remove it from every other project in the
workspace. That last step sets `deleted_at` via `update()` rather than calling
`delete()`: the model's `delete()` queues `soft_delete_related_objects`, which
would null out `type` on work items across the whole workspace.

The frontend half is in
[apps/web/core/store/issue-type.store.ts](../../apps/web/core/store/issue-type.store.ts):
`deleteIssueType()` now `unset`s the map entry instead of patching it to
`is_active: false`.

**Bug C — the defaults were re-seeded on every project save.**
`ProjectViewSet.partial_update`
([apps/api/plane/app/views/project/base.py](../../apps/api/plane/app/views/project/base.py))
called `ensure_default_issue_types()` whenever `serializer.data` reported
`is_issue_type_enabled` — and `serializer.data` is the whole project, so _any_
project settings save re-ran it. A type deleted through the (now working) trash
icon came straight back the next time someone renamed the project. Seeding now
runs only on the off → on transition, captured before `serializer.save()` mutates
the instance.

## Verification

- 58 backend tests pass, including new coverage for the constraint, the merge
  logic, per-project unlink semantics, name reuse after delete, and the
  non-resurrection of a deleted type across a project save. The 8 failures in
  `test_authentication.py` on a full run are pre-existing on `preview`.
- The migration was run against the local dev database after planting the exact
  prod shape (six active/inactive duplicate pairs created 1ms apart, one work item
  pointing at a duplicate): 12 type rows and 12 links collapsed to 6 and 6, the
  single `is_default` marker survived, and the work item was repointed to the
  surviving active row. A subsequent duplicate `INSERT` is refused by the index.
- Against the live API: delete removed the type from the list and it stayed gone
  across a project re-save, the freed name could be re-created, and deleting the
  project default still returns 400.
