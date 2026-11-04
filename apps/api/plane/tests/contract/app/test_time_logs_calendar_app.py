# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from datetime import datetime, timedelta

import pytest
import pytz
from rest_framework import status

from plane.db.models import Issue, IssueTimeLog, Project, ProjectMember, User, WorkspaceMember
from plane.db.models.workspace import get_default_working_hours


def _aware(year, month, day, hour, minute=0):
    return pytz.utc.localize(datetime(year, month, day, hour, minute))


@pytest.mark.contract
class TestWorkspaceTimeLogsCalendar:
    """Week-calendar listing: own logs, admin visibility, archived work items."""

    @pytest.fixture
    def calendar_context(self, workspace, create_user):
        workspace.timezone = "Europe/Minsk"
        working_hours = get_default_working_hours()
        working_hours["enabled"] = True
        working_hours["holiday_calendar"] = {"country_code": "US", "subdivision_code": None}
        workspace.working_hours = working_hours
        workspace.save(update_fields=["timezone", "working_hours", "updated_at"])

        project_a = Project.objects.create(name="Calendar A", identifier="CALA", workspace=workspace)
        project_b = Project.objects.create(name="Calendar B", identifier="CALB", workspace=workspace)
        ProjectMember.objects.create(project=project_a, member=create_user, role=20)
        ProjectMember.objects.create(project=project_b, member=create_user, role=20)

        member = User.objects.create_user(email="calendar-member@plane.so", username="calendar_member")
        WorkspaceMember.objects.create(workspace=workspace, member=member, role=15)
        ProjectMember.objects.create(project=project_a, member=member, role=15)
        ProjectMember.objects.create(project=project_b, member=member, role=15)

        project_admin = User.objects.create_user(email="calendar-padmin@plane.so", username="calendar_padmin")
        WorkspaceMember.objects.create(workspace=workspace, member=project_admin, role=15)
        ProjectMember.objects.create(project=project_a, member=project_admin, role=20)

        issue_a = Issue.objects.create(name="Visible issue", project=project_a, workspace=workspace)
        archived = Issue.objects.create(name="Archived issue", project=project_a, workspace=workspace)
        archived.archived_at = datetime(2026, 10, 27).date()
        archived.save(update_fields=["archived_at", "updated_at"])
        issue_b = Issue.objects.create(name="Other project", project=project_b, workspace=workspace)

        inside = _aware(2026, 10, 27, 8, 12)
        IssueTimeLog.objects.create(
            issue=issue_a,
            project=project_a,
            workspace=workspace,
            user=member,
            date=datetime(2026, 10, 27).date(),
            started_at=inside,
            stopped_at=inside + timedelta(hours=1, minutes=35),
            duration_seconds=5700,
            stop_reason=IssueTimeLog.StopReason.STATE_CHANGE,
        )
        IssueTimeLog.objects.create(
            issue=archived,
            project=project_a,
            workspace=workspace,
            user=member,
            date=datetime(2026, 10, 28).date(),
            started_at=_aware(2026, 10, 28, 0, 0),
            stopped_at=_aware(2026, 10, 28, 1, 0),
            duration_seconds=3600,
            stop_reason=IssueTimeLog.StopReason.MANUAL_ENTRY,
        )
        IssueTimeLog.objects.create(
            issue=issue_b,
            project=project_b,
            workspace=workspace,
            user=member,
            date=datetime(2026, 10, 27).date(),
            started_at=_aware(2026, 10, 27, 10, 0),
            stopped_at=_aware(2026, 10, 27, 11, 0),
            duration_seconds=3600,
            stop_reason=IssueTimeLog.StopReason.STATE_CHANGE,
        )
        IssueTimeLog.objects.create(
            issue=issue_a,
            project=project_a,
            workspace=workspace,
            user=member,
            date=datetime(2026, 9, 1).date(),
            started_at=_aware(2026, 9, 1, 9, 0),
            stopped_at=_aware(2026, 9, 1, 10, 0),
            duration_seconds=3600,
            stop_reason=IssueTimeLog.StopReason.MANUAL_ENTRY,
        )
        IssueTimeLog.objects.create(
            issue=issue_a,
            project=project_a,
            workspace=workspace,
            user=member,
            date=datetime(2026, 10, 26).date(),
            started_at=_aware(2026, 10, 26, 6, 0),
            stopped_at=None,
            duration_seconds=0,
            stop_reason=None,
        )

        return {
            "member": member,
            "project_admin": project_admin,
            "project_a": project_a,
            "project_b": project_b,
        }

    @staticmethod
    def url(workspace_slug, user_id=None):
        base = f"/api/workspaces/{workspace_slug}/time-logs/?start_date=2026-10-26&end_date=2026-11-01"
        if user_id:
            return f"{base}&user_id={user_id}"
        return base

    @pytest.mark.django_db
    def test_member_sees_own_logs_including_archived_and_open_timer(
        self, session_client, workspace, calendar_context
    ):
        member = calendar_context["member"]
        session_client.force_authenticate(user=member)

        response = session_client.get(self.url(workspace.slug))

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["timezone"] == "Europe/Minsk"
        assert body["can_view_others"] is False
        assert len(body["logs"]) == 4
        names = {log["issue"]["name"] for log in body["logs"]}
        assert names == {"Visible issue", "Archived issue", "Other project"}
        open_logs = [log for log in body["logs"] if log["stopped_at"] is None]
        assert len(open_logs) == 1
        assert open_logs[0]["can_manage"] is True
        thursday = next(day for day in body["schedule"] if day["date"] == "2026-10-29")
        assert thursday["working"] is True
        assert thursday["start"] == "09:00"
        new_year_week_note = next(day for day in body["schedule"] if day["date"] == "2026-10-31")
        assert new_year_week_note["working"] is False

    @pytest.mark.django_db
    def test_member_cannot_read_another_users_logs(self, session_client, workspace, create_user, calendar_context):
        session_client.force_authenticate(user=calendar_context["member"])

        response = session_client.get(self.url(workspace.slug, create_user.id))

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["code"] == "forbidden"

    @pytest.mark.django_db
    def test_project_admin_sees_only_administered_projects(self, session_client, workspace, calendar_context):
        session_client.force_authenticate(user=calendar_context["project_admin"])

        response = session_client.get(self.url(workspace.slug, calendar_context["member"].id))

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["can_view_others"] is True
        assert str(calendar_context["project_a"].id) in body["editable_project_ids"]
        assert str(calendar_context["project_b"].id) not in body["editable_project_ids"]
        names = {log["issue"]["name"] for log in body["logs"]}
        assert "Other project" not in names
        assert "Visible issue" in names
        assert "Archived issue" in names
        assert all(log["can_manage"] for log in body["logs"])

    @pytest.mark.django_db
    def test_workspace_admin_sees_member_logs_in_both_projects(
        self, session_client, workspace, create_user, calendar_context
    ):
        session_client.force_authenticate(user=create_user)

        response = session_client.get(self.url(workspace.slug, calendar_context["member"].id))

        assert response.status_code == status.HTTP_200_OK
        names = {log["issue"]["name"] for log in response.json()["logs"]}
        assert names == {"Visible issue", "Archived issue", "Other project"}

    @pytest.mark.django_db
    def test_holiday_is_non_working(self, session_client, workspace, calendar_context):
        session_client.force_authenticate(user=calendar_context["member"])

        response = session_client.get(
            f"/api/workspaces/{workspace.slug}/time-logs/?start_date=2025-12-29&end_date=2026-01-04"
        )

        assert response.status_code == status.HTTP_200_OK
        schedule = {day["date"]: day for day in response.json()["schedule"]}
        assert schedule["2026-01-01"]["working"] is False
        assert schedule["2025-12-29"]["working"] is True
        assert schedule["2026-01-03"]["working"] is False

    @pytest.mark.django_db
    def test_manual_log_stored_at_utc_midnight_stays_in_a_west_of_utc_week(
        self, session_client, workspace, calendar_context
    ):
        workspace.timezone = "America/Los_Angeles"
        workspace.save(update_fields=["timezone", "updated_at"])
        issue = Issue.objects.get(name="Visible issue", workspace=workspace)
        project = calendar_context["project_a"]
        IssueTimeLog.objects.create(
            issue=issue,
            project=project,
            workspace=workspace,
            user=calendar_context["member"],
            date=datetime(2026, 10, 26).date(),
            started_at=_aware(2026, 10, 26, 0, 0),
            stopped_at=_aware(2026, 10, 26, 1, 0),
            duration_seconds=3600,
            stop_reason=IssueTimeLog.StopReason.MANUAL_ENTRY,
        )
        session_client.force_authenticate(user=calendar_context["member"])

        response = session_client.get(self.url(workspace.slug))

        assert response.status_code == status.HTTP_200_OK
        matched = [
            log
            for log in response.json()["logs"]
            if log["date"] == "2026-10-26" and log["stop_reason"] == "manual_entry"
        ]
        assert len(matched) == 1

    @pytest.mark.django_db
    def test_invalid_range_is_rejected(self, session_client, workspace, calendar_context):
        session_client.force_authenticate(user=calendar_context["member"])

        response = session_client.get(
            f"/api/workspaces/{workspace.slug}/time-logs/?start_date=2026-11-01&end_date=2026-10-01"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_unknown_user_is_not_found(self, session_client, workspace, create_user, calendar_context):
        session_client.force_authenticate(user=create_user)

        response = session_client.get(
            f"/api/workspaces/{workspace.slug}/time-logs/"
            "?start_date=2026-10-26&end_date=2026-11-01&user_id=00000000-0000-0000-0000-000000000000"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
