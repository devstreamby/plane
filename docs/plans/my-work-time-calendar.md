# My Work time calendar

**Status:** implemented. Written 2026-10-28.
**Depends on:** `IssueTimeLog`, the per-issue time-log routes, `build_time_log_report()` visibility.

A week calendar for a person's time logs, in the style of Jira Clockwork. My Work is where you see and edit your own week. A separate Team time page lets a project or workspace admin open someone else's week. The grid is `react-big-calendar`. Create, move, and delete keep the current mutation API; the UI translates a gesture into the body those routes already accept.

## Decisions

- My Work gains a **Time** tab at `/{workspaceSlug}/profile/{userId}/time`. The tab is rendered only when `userId` is the signed-in user. On that tab the profile project-stats sidebar is hidden so the week grid can use the full width.
- Team time is a separate workspace page at `/{workspaceSlug}/team-time`, linked beside Reports. It is the only place a manager opens another person's week. Another user's profile does not grow a Time tab.
- One new read endpoint returns individual logs for a date window. The timesheet report stays aggregated and is left alone.
- Mutations stay on the existing per-issue routes. No new write fields, no `clock_time` column.

## What the current mutations store

`POST` and `PATCH` on a work item's time logs accept `date` (`YYYY-MM-DD`), `duration_seconds` (or `hours` and `minutes`), and an optional `user_id`. `parse_manual_time_log_payload()` returns only the date and the duration. The handlers then set:

- `started_at` = 00:00 UTC on `date` (`TIME_ZONE` is `UTC`)
- `stopped_at` = `started_at` + `duration_seconds`
- `duration_seconds` = the parsed duration, raised to at least 60 seconds
- `stop_reason` = `manual_entry` on create

A client cannot send a clock time. Any `started_at` in the body is ignored. `PATCH` also replaces an existing interval, including one that a timer recorded at a real time of day.

`DELETE` removes the log and recalculates `issue.total_time_spent`. That route already does what the calendar needs.

Routes, app API (session auth), already wrapped by `IssueService.createTimeLog`, `updateTimeLog`, and `deleteTimeLog`:

- `POST /api/workspaces/{slug}/projects/{project_id}/issues/{issue_id}/time-logs/`
- `PATCH /api/workspaces/{slug}/projects/{project_id}/issues/{issue_id}/time-logs/{id}/`
- `DELETE /api/workspaces/{slug}/projects/{project_id}/issues/{issue_id}/time-logs/{id}/`

Who can write is unchanged. A member can create a log for themselves and can edit or delete their own log. A project admin, or a workspace admin who is a member of the project, can pass `user_id` and can edit or delete any log in that project. Guests can read a work item's logs and cannot mutate them.

## UI mapping

`react-big-calendar` speaks `{ start: Date, end: Date }`. The mutation API speaks `{ date, duration_seconds }`. The calendar converts, in the **workspace timezone**, before it calls the API.

| Gesture                                               | Request                                                                                                                                                                          |
| ----------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Drag a range on a day column (`onSelectSlot`)         | `POST` `{ date, duration_seconds }`. `date` is the workspace-local calendar day of `start`. `duration_seconds` is `end - start`, snapped to 15 minutes, and at least 60 seconds. |
| Drop an editable event on another day (`onEventDrop`) | `PATCH` `{ date: the new day, duration_seconds: unchanged }`.                                                                                                                    |
| Edit duration in the popover                          | `PATCH` `{ date: unchanged, duration_seconds: the new length }`.                                                                                                                 |
| Delete from the popover                               | `DELETE`.                                                                                                                                                                        |

Snap is 15 minutes (`step={15}`, `timeslots={1}`). The server still raises any positive duration to a whole minute.

`date` is formatted in the workspace timezone (`workspace.timezone`, an IANA name), not in the browser zone. Use `Intl.DateTimeFormat` with that `timeZone` and a `YYYY-MM-DD` calendar. The week columns and the "today" highlight use the same zone, so a browser set to UTC still shows a Minsk week as Minsk days.

After every successful `POST` or `PATCH`, the block is positioned from the **response** timestamps, not from where the pointer was released. Those timestamps start at 00:00 UTC. The gesture picks a day and a length. It does not pick a time of day, because the API does not store one.

### Two kinds of event

The list endpoint returns `started_at`, `stopped_at`, and `stop_reason`. The grid uses them as follows.

**Clock events.** `stop_reason` is `state_change` or `working_hours`. Drawn on the hour grid from `started_at` to `stopped_at`. An open timer (`stopped_at` null, `duration_seconds` 0) is drawn from `started_at` to now and updates once a minute. Clock events are not draggable and not resizable: a `PATCH` would replace the recorded interval with midnight UTC plus a duration. They can be deleted from the popover when `can_manage` is true.

**Duration events.** `stop_reason` is `manual_entry`, which is every log the sidebar form or this calendar creates. Drawn as all-day events on `date`, with the duration in the label (`S2WEB-18 · 1h 35m`). Dragging one to another day changes `date` only. The hour of the original pointer-down is discarded once the request succeeds, and the chip stays in the all-day row. Creating from an hour-grid selection works the same way: the height of the selection is the duration, the column is the day, and the saved event appears in the all-day row.

Title for both kinds is `{project_identifier}-{sequence_id}` plus the work item name. A log that crosses midnight is one record; a clock event uses the real `started_at` / `stopped_at`, so the library draws it across the two columns.

## Read API

`GET /api/workspaces/{slug}/time-logs/?start_date=&end_date=&user_id=`

Session auth, workspace member or admin. `start_date` and `end_date` are required `YYYY-MM-DD`. The same validation as the timesheet applies: both required, `start_date` not after `end_date`, span at most 92 days. `user_id` defaults to the caller.

The window is midnight-to-midnight in the workspace timezone, converted to UTC the same way `_local_midnight_utc` does in `plane/utils/time_report.py`. A log is included when it belongs to `user_id` and any of these hold: it is still running (`stopped_at` is null), its stored `date` falls in the window, or `[started_at, stopped_at)` overlaps the window. The `date` clause is required because a manual log is stored at 00:00 UTC, which can sit before local midnight for timezones west of UTC.

Visibility matches `build_time_log_report()`:

- The caller's own logs, in every project they belong to.
- Another user's logs only in projects where the caller is a project admin, or a workspace admin who belongs to that project.
- A request for someone else with no such project returns 403.

The query starts from `IssueTimeLog` and does not pass through `Issue.issue_objects`, so hours on archived, draft, and triage work items stay visible. Same rule as the report.

```json
{
  "start_date": "2026-10-26",
  "end_date": "2026-11-01",
  "timezone": "Europe/Minsk",
  "working_hours": {},
  "schedule": [{ "date": "2026-10-26", "working": true, "start": "09:00", "end": "18:00" }],
  "can_view_others": true,
  "editable_project_ids": ["..."],
  "logs": [
    {
      "id": "...",
      "project_id": "...",
      "issue_id": "...",
      "user_id": "...",
      "date": "2026-10-27",
      "started_at": "2026-10-27T08:12:00+00:00",
      "stopped_at": "2026-10-27T09:47:00+00:00",
      "duration_seconds": 5700,
      "stop_reason": "state_change",
      "can_manage": true,
      "issue": {
        "name": "Mortgage/Visa statement",
        "sequence_id": 18,
        "project_identifier": "S2WEB"
      }
    }
  ]
}
```

`working_hours` is the workspace JSON (`enabled`, `global_hours`, `days`, `holiday_calendar`). `schedule` is that config resolved for each date in the window, including holidays, so the client can shade days and sum capacity without a holiday library. When the schedule is disabled every day is `working: false` and the client skips both shading and capacity. `editable_project_ids` is every project the caller administers, including weeks with no logs, so the team page can still create one. `can_manage` on each log is true when the log is the caller's or its project is in that admin set. `can_view_others` is true when that admin set is non-empty, same meaning as on the report.

Duration events are all-day chips. `react-big-calendar` treats a resize of an all-day chip as a change in how many days it spans, so the grid does not resize them. Duration is edited in the popover, which sends `date` and `duration_seconds`. Dragging a chip to another day still sends a `PATCH` with the new `date` and the same duration.

The public API (`/api/v1/...`) does not grow this route.

## Pages

### My Work

Files to add or extend:

- Tab constant in `packages/constants/src/profile.ts`, route `time`, shown from `ProfileNavbar` only for the signed-in user.
- Page `apps/web/app/(all)/[workspaceSlug]/(projects)/profile/[userId]/time/page.tsx`.
- In the profile layout, skip `ProfileSidebar` when the path ends in `/time`.

The page loads the read endpoint for the signed-in user and the visible week. Writes go through `IssueService` with that log's `project_id` and `issue_id`. `user_id` is omitted, so the log stays attributed to the caller.

Header: previous week, next week, Today, the week range, logged time against capacity, and the workspace timezone name. Logged time is the sum of `duration_seconds` for logs whose `date` falls in the visible week, plus the live elapsed of an open timer. Capacity is the sum of that week's working-hour intervals from `working_hours` when the schedule is enabled (the default Mon–Fri 09:00–18:00 week is 45h). Holidays from the configured holiday calendar are excluded. When working hours are disabled, the header shows the logged total and no capacity.

The hour grid shades slots outside the working interval for that weekday. Weekends that are disabled in `days` are shaded for the whole column. `min` / `max` stay at the full day so early and late clock events remain reachable by scroll; the initial scroll position is the start of `global_hours`.

Right rail: up to 20 work items assigned to the signed-in user, most recently updated, from `GET /api/workspaces/{slug}/user-issues/{userId}/` (the profile Assigned source). Choosing one, then dragging a range, creates the log on that work item. A selection with no work item chosen opens the same list in the create popover. The popover on an existing duration event edits the day and the duration and can delete. The popover on a clock event shows the interval and can delete when `can_manage` is true.

### Team time

`apps/web/app/(all)/[workspaceSlug]/(projects)/team-time/page.tsx`, registered next to `reports` in `packages/constants/src/workspace.ts` and `apps/web/app/routes/core.ts`. Workspace members and admins can open it.

The grid is the same component, with a member picker of workspace members. Selecting a member calls the read endpoint with their `user_id`. A 403 renders inline: team calendars are available to project and workspace admins, and your own week is on My Work.

Edits follow `can_manage` and `editable_project_ids`. Creating a log for the selected person sends `user_id` on the `POST`. The work-item picker lists issues in `editable_project_ids`. Duration events the caller can manage are draggable. Clock events stay fixed, and can be deleted when `can_manage` is true.

## Library

Add `react-big-calendar` to `apps/web`. Use `withDragAndDrop` from `react-big-calendar/lib/addons/dragAndDrop` and `dateFnsLocalizer` ( `date-fns` is already a dependency). Import the base CSS and the drag-and-drop CSS, then override them with the existing theme tokens so the week view matches the dark shell.

`draggableAccessor` returns true only for duration events with `can_manage`. `resizableAccessor` returns false. `selectable` is on so an empty range can create a log. Custom `eventPropGetter` is enough for the work-item label; no second calendar component.

## Out of scope

- Extending `POST` / `PATCH` to accept `started_at` or `stopped_at`.
- Changing the work item a log belongs to.
- Clockwork's Timesheet and Worklogs tabs. The team timesheet remains `/{workspaceSlug}/reports`.
- Editing a running timer from the grid. It is closed by leaving the Started state or by the working-hours job, as today.
- Per-user timezone. The workspace timezone is the calendar timezone.

## Verification

- Create from a 1h 35m drag on a Tuesday: the stored row has `date` of that Tuesday, `duration_seconds` 5700, `started_at` at 00:00 UTC, `stop_reason` `manual_entry`, and the chip lands in the all-day row.
- Drag that chip to Wednesday: `date` changes, duration is unchanged, `total_time_spent` on the work item is unchanged.
- Resize or popover edit to 2h: `duration_seconds` is 7200 and `total_time_spent` moves by the difference.
- Delete: the log is gone and `total_time_spent` drops by its duration.
- A `state_change` log stays on its real interval and does not move when dragged.
- An open timer renders to now, is not draggable, and is not `PATCH`ed.
- A member `GET` with another user's id returns 403. A project admin receives that user's logs only for projects they admin.
- A log on an archived work item is present in the week.
- Sidebar manual entry and this calendar write the same body, and both show up as duration events.
- Week total and the shaded hours follow `working_hours` in the workspace timezone, including a browser whose zone is not the workspace zone.
