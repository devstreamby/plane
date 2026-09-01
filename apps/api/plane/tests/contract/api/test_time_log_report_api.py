# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Contract coverage for the API-key authenticated time log report endpoints."""

from datetime import datetime, timedelta, timezone as dt_timezone

import pytest
from rest_framework import status

from plane.db.models import (
    APIToken,
    Issue,
    IssueTimeLog,
    Project,
    ProjectMember,
    State,
    User,
    WorkspaceMember,
)

WORKSPACE_URL = "/api/v1/workspaces/{slug}/time-logs-report/"
PROJECT_URL = "/api/v1/workspaces/{slug}/projects/{project_id}/time-logs-report/"

# A fixed period well clear of "now", so the numbers never depend on the clock.
PERIOD = {"start_date": "2026-08-01", "end_date": "2026-08-31"}


def log_hours(issue, user, day, hours, started_hour=9):
    """Log `hours` on `issue` starting at `started_hour` UTC on the given day."""
    started_at = datetime(2026, 8, day, started_hour, tzinfo=dt_timezone.utc)
    return IssueTimeLog.objects.create(
        issue=issue,
        project=issue.project,
        workspace=issue.workspace,
        user=user,
        date=started_at.date(),
        started_at=started_at,
        stopped_at=started_at + timedelta(hours=hours),
        duration_seconds=hours * 3600,
        created_by=user,
    )


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(
        name="Report Project",
        identifier="RP",
        workspace=workspace,
        created_by=create_user,
    )
    ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
    return project


@pytest.fixture
def in_progress_state(db, project):
    return State.objects.create(
        name="In Progress",
        group="started",
        project=project,
        workspace=project.workspace,
    )


@pytest.mark.contract
@pytest.mark.django_db
class TestTimeLogReportAPIEndpoint:
    def test_returns_aggregated_report_for_api_key(
        self, api_key_client, workspace, project, create_user, in_progress_state
    ):
        issue = Issue.objects.create(
            name="Reported work item", project=project, workspace=workspace, state=in_progress_state
        )
        log_hours(issue, create_user, day=3, hours=2)
        log_hours(issue, create_user, day=3, hours=1, started_hour=14)
        log_hours(issue, create_user, day=4, hours=3)

        response = api_key_client.get(WORKSPACE_URL.format(slug=workspace.slug), PERIOD)

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["can_view_others"] is True
        # Same user, same issue, same day collapses into one entry.
        entries = {(entry["date"], entry["duration_seconds"]) for entry in payload["entries"]}
        assert entries == {("2026-08-03", 3 * 3600), ("2026-08-04", 3 * 3600)}

        reported_issue = payload["issues"][str(issue.id)]
        assert reported_issue["name"] == "Reported work item"
        assert reported_issue["project_identifier"] == "RP"
        assert reported_issue["state_name"] == "In Progress"
        assert reported_issue["archived"] is False

        reported_user = payload["users"][str(create_user.id)]
        assert reported_user["email"] == create_user.email

    def test_archived_draft_and_triage_work_items_are_reported(self, api_key_client, workspace, project, create_user):
        """Hours on work items hidden from Issue.issue_objects must still be reported."""
        triage_state = State.objects.create(
            name="Triage", group="triage", is_triage=True, project=project, workspace=workspace
        )
        archived = Issue.objects.create(
            name="Archived item",
            project=project,
            workspace=workspace,
            archived_at=datetime(2026, 8, 20, tzinfo=dt_timezone.utc).date(),
        )
        draft = Issue.objects.create(name="Draft item", project=project, workspace=workspace, is_draft=True)
        triaged = Issue.objects.create(name="Triage item", project=project, workspace=workspace, state=triage_state)
        for issue in (archived, draft, triaged):
            log_hours(issue, create_user, day=5, hours=1)

        response = api_key_client.get(WORKSPACE_URL.format(slug=workspace.slug), PERIOD)

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        reported_issue_ids = {entry["issue_id"] for entry in payload["entries"]}
        assert {str(archived.id), str(draft.id), str(triaged.id)} <= reported_issue_ids
        assert payload["issues"][str(archived.id)]["archived"] is True
        assert payload["issues"][str(draft.id)]["archived"] is False
        assert payload["issues"][str(triaged.id)]["state_name"] == "Triage"

    def test_running_timers_are_not_reported(self, api_key_client, workspace, project, create_user):
        issue = Issue.objects.create(name="Running", project=project, workspace=workspace)
        started_at = datetime(2026, 8, 6, 9, tzinfo=dt_timezone.utc)
        IssueTimeLog.objects.create(
            issue=issue,
            project=project,
            workspace=workspace,
            user=create_user,
            date=started_at.date(),
            started_at=started_at,
            stopped_at=None,
            duration_seconds=0,
            created_by=create_user,
        )

        response = api_key_client.get(WORKSPACE_URL.format(slug=workspace.slug), PERIOD)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["entries"] == []

    def test_project_scoped_endpoint_reports_only_that_project(self, api_key_client, workspace, project, create_user):
        other_project = Project.objects.create(
            name="Other", identifier="OTH", workspace=workspace, created_by=create_user
        )
        ProjectMember.objects.create(project=other_project, member=create_user, role=20, is_active=True)
        issue = Issue.objects.create(name="Reported", project=project, workspace=workspace)
        other_issue = Issue.objects.create(name="Not reported", project=other_project, workspace=workspace)
        log_hours(issue, create_user, day=7, hours=1)
        log_hours(other_issue, create_user, day=7, hours=5)

        response = api_key_client.get(PROJECT_URL.format(slug=workspace.slug, project_id=project.id), PERIOD)

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert {entry["project_id"] for entry in payload["entries"]} == {str(project.id)}

    def test_missing_or_oversized_period_returns_400(self, api_key_client, workspace, project):
        url = WORKSPACE_URL.format(slug=workspace.slug)

        missing = api_key_client.get(url)
        oversized = api_key_client.get(url, {"start_date": "2026-01-01", "end_date": "2026-12-31"})

        assert missing.status_code == status.HTTP_400_BAD_REQUEST
        assert "start_date" in missing.json()["error"]
        assert oversized.status_code == status.HTTP_400_BAD_REQUEST
        assert "92" in oversized.json()["error"]

    def test_request_without_api_key_is_rejected(self, api_client, workspace):
        response = api_client.get(WORKSPACE_URL.format(slug=workspace.slug), PERIOD)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.contract
@pytest.mark.django_db
class TestTimeLogReportVisibility:
    """A plain project member only sees their own logs, and is told so."""

    @pytest.fixture
    def member_client(self, api_client, db, workspace, project, create_user):
        member = User.objects.create_user(email="reporter@plane.so", username="report_member")
        WorkspaceMember.objects.create(workspace=workspace, member=member, role=15, is_active=True)
        ProjectMember.objects.create(project=project, member=member, role=15, is_active=True)
        token = APIToken.objects.create(user=member, label="Member token", token="member-api-token-12345")
        api_client.credentials(HTTP_X_API_KEY=token.token)
        return api_client, member

    def test_member_gets_own_logs_and_a_restricted_project_marker(self, member_client, workspace, project, create_user):
        client, member = member_client
        issue = Issue.objects.create(name="Shared item", project=project, workspace=workspace)
        log_hours(issue, member, day=10, hours=2)
        log_hours(issue, create_user, day=10, hours=4)

        response = client.get(WORKSPACE_URL.format(slug=workspace.slug), PERIOD)

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["can_view_others"] is False
        assert payload["restricted_project_ids"] == [str(project.id)]
        assert {entry["user_id"] for entry in payload["entries"]} == {str(member.id)}

    def test_strict_mode_fails_instead_of_reporting_partial_data(self, member_client, workspace, project):
        client, member = member_client
        issue = Issue.objects.create(name="Shared item", project=project, workspace=workspace)
        log_hours(issue, member, day=11, hours=2)

        response = client.get(WORKSPACE_URL.format(slug=workspace.slug), {**PERIOD, "strict": "true"})

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["restricted_project_ids"] == [str(project.id)]

    def test_unavailable_projects_are_reported_back(self, api_key_client, workspace, project, create_user):
        """A requested project the token owner is not a member of is named, not silently dropped."""
        foreign_project = Project.objects.create(
            name="Foreign", identifier="FRN", workspace=workspace, created_by=create_user
        )

        response = api_key_client.get(
            WORKSPACE_URL.format(slug=workspace.slug),
            {**PERIOD, "project_ids": f"{project.id},{foreign_project.id}"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["unavailable_project_ids"] == [str(foreign_project.id)]
