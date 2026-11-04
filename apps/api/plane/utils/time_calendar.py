# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Individual time logs for one person over a date window.

Used by the My Work week calendar and the team calendar. The timesheet report
stays aggregated; this query returns the rows the grid draws and edits.
"""

import uuid
from datetime import timedelta

import pytz
from django.db.models import Q

from plane.db.models import IssueTimeLog, ProjectMember, User, Workspace, WorkspaceMember
from plane.db.models.project import ROLE
from plane.utils.time_report import (
    MAX_REPORT_RANGE_DAYS,
    TimeLogReportValidationError,
    _local_midnight_utc,
    _parse_date,
)
from plane.utils.working_hours import working_schedule_for_range


class TimeLogCalendarForbidden(Exception):
    """The caller asked for someone else's logs without administering a project."""


class TimeLogCalendarNotFound(Exception):
    """The requested user is not an active member of the workspace."""


class TimeLogCalendarBadRequest(Exception):
    """`user_id` was not a UUID."""


def _admin_project_ids(user, slug):
    """Projects where `user` may see and manage other members' time logs.

    Matches `build_time_log_report`: a workspace admin who belongs to the
    project, or a project admin.
    """
    member_roles = dict(
        ProjectMember.objects.filter(
            member=user,
            workspace__slug=slug,
            is_active=True,
            project__deleted_at__isnull=True,
            project__archived_at__isnull=True,
        ).values_list("project_id", "role")
    )
    is_workspace_admin = WorkspaceMember.objects.filter(
        member=user, workspace__slug=slug, role=ROLE.ADMIN.value, is_active=True
    ).exists()
    if is_workspace_admin:
        admin_ids = list(member_roles.keys())
    else:
        admin_ids = [project_id for project_id, role in member_roles.items() if role == ROLE.ADMIN.value]
    return member_roles, admin_ids


def build_time_log_calendar(slug, user, start_date_str, end_date_str, target_user_id=None):
    """Return one user's time logs overlapping a workspace-local date window.

    Selection starts from ``IssueTimeLog`` and does not pass through
    ``Issue.issue_objects``, so logs on archived, draft, and triage work items
    stay in the week. Raises ``TimeLogReportValidationError`` for a bad range,
    ``TimeLogCalendarBadRequest`` for a ``user_id`` that is not a UUID,
    ``TimeLogCalendarForbidden`` when another user's logs were requested without
    an administered project, and ``TimeLogCalendarNotFound`` when that user is
    not an active workspace member.
    """
    start_date = _parse_date(start_date_str)
    end_date = _parse_date(end_date_str)
    if not start_date or not end_date:
        raise TimeLogReportValidationError("invalid_dates")
    if start_date > end_date:
        raise TimeLogReportValidationError("inverted_range")
    if (end_date - start_date).days + 1 > MAX_REPORT_RANGE_DAYS:
        raise TimeLogReportValidationError("range_too_long")

    workspace = Workspace.objects.filter(slug=slug).only("timezone", "working_hours").first()
    if workspace is None:
        raise TimeLogCalendarNotFound()

    member_roles, admin_ids = _admin_project_ids(user, slug)
    admin_id_set = set(admin_ids)
    own_request = target_user_id in (None, "", str(user.id))

    if own_request:
        target_user = user
        scoped_project_ids = list(member_roles.keys())
    else:
        try:
            uuid.UUID(str(target_user_id))
        except (ValueError, TypeError, AttributeError):
            raise TimeLogCalendarBadRequest() from None
        if not admin_ids:
            raise TimeLogCalendarForbidden()
        if not WorkspaceMember.objects.filter(
            workspace__slug=slug, member_id=target_user_id, is_active=True
        ).exists():
            raise TimeLogCalendarNotFound()
        try:
            target_user = User.objects.get(pk=target_user_id)
        except User.DoesNotExist:
            raise TimeLogCalendarNotFound()
        scoped_project_ids = list(admin_ids)

    tz_name = workspace.timezone or "UTC"
    tz = pytz.timezone(tz_name)
    window_start = _local_midnight_utc(tz, start_date)
    window_end = _local_midnight_utc(tz, end_date + timedelta(days=1))
    schedule = working_schedule_for_range(workspace.working_hours, start_date, end_date)

    empty = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "timezone": tz_name,
        "working_hours": workspace.working_hours,
        "schedule": schedule,
        "can_view_others": bool(admin_ids),
        "editable_project_ids": [str(project_id) for project_id in admin_ids],
        "logs": [],
    }
    if not scoped_project_ids:
        return empty

    logs = (
        IssueTimeLog.objects.filter(
            workspace__slug=slug,
            user_id=target_user.id,
            project_id__in=scoped_project_ids,
        )
        .filter(
            Q(stopped_at__isnull=True)
            | Q(date__gte=start_date, date__lte=end_date)
            | Q(started_at__lt=window_end, stopped_at__gt=window_start, stopped_at__isnull=False)
        )
        .select_related("issue", "issue__project")
        .order_by("started_at", "id")
    )

    serialized = []
    for log in logs:
        issue = log.issue
        serialized.append(
            {
                "id": str(log.id),
                "project_id": str(log.project_id),
                "issue_id": str(log.issue_id),
                "user_id": str(log.user_id) if log.user_id else None,
                "date": log.date.isoformat(),
                "started_at": log.started_at.isoformat(),
                "stopped_at": log.stopped_at.isoformat() if log.stopped_at else None,
                "duration_seconds": log.duration_seconds,
                "stop_reason": log.stop_reason,
                "can_manage": log.user_id == user.id or log.project_id in admin_id_set,
                "issue": {
                    "name": issue.name,
                    "sequence_id": issue.sequence_id,
                    "project_identifier": issue.project.identifier,
                },
            }
        )

    empty["logs"] = serialized
    return empty
