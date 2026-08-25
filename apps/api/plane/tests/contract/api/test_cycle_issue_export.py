# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import csv
from io import StringIO

import pytest

from plane.db.models import Cycle, CycleIssue, Issue, Project, ProjectMember


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(
        name="Test Project",
        identifier="TP",
        workspace=workspace,
        created_by=create_user,
    )
    ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
    return project


@pytest.fixture
def cycle(db, project, create_user):
    return Cycle.objects.create(
        name="Sprint 1",
        project=project,
        workspace=project.workspace,
        owned_by=create_user,
    )


@pytest.fixture
def cycle_issue(db, project, cycle, create_user):
    issue = Issue.objects.create(
        name="Fix login bug",
        description_html="<p>Users could not <strong>log in</strong> on mobile.</p>",
        project=project,
        workspace=project.workspace,
        created_by=create_user,
    )
    CycleIssue.objects.create(issue=issue, cycle=cycle, project=project, workspace=project.workspace)
    return issue


def _export_url(workspace_slug, project_id, cycle_id, **params):
    url = f"/api/workspaces/{workspace_slug}/projects/{project_id}/cycles/{cycle_id}/export/"
    if params:
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{query}"
    return url


@pytest.mark.contract
@pytest.mark.django_db
class TestCycleIssueExportEndpoint:
    def test_default_csv_export_has_three_mandatory_columns(self, session_client, workspace, project, cycle, cycle_issue):
        response = session_client.get(_export_url(workspace.slug, project.id, cycle.id))

        assert response.status_code == 200
        assert response["Content-Type"].startswith("text/csv")
        assert "attachment;" in response["Content-Disposition"]

        rows = list(csv.reader(StringIO(response.content.decode("utf-8"))))
        assert rows[0] == ["Identifier", "Name", "Description"]
        assert rows[1][0] == f"{project.identifier}-{cycle_issue.sequence_id}"
        assert rows[1][1] == "Fix login bug"
        assert "**log in**" in rows[1][2]

    def test_markdown_export_renders_heading_and_body(self, session_client, workspace, project, cycle, cycle_issue):
        response = session_client.get(_export_url(workspace.slug, project.id, cycle.id, export_format="markdown"))

        assert response.status_code == 200
        assert response["Content-Type"].startswith("text/markdown")
        content = response.content.decode("utf-8")
        assert f"### {project.identifier}-{cycle_issue.sequence_id} — Fix login bug" in content
        assert "**log in**" in content

    def test_custom_fields_are_included_and_others_excluded(self, session_client, workspace, project, cycle, cycle_issue):
        response = session_client.get(
            _export_url(workspace.slug, project.id, cycle.id, fields="identifier,name,description,priority")
        )

        rows = list(csv.reader(StringIO(response.content.decode("utf-8"))))
        assert rows[0] == ["Identifier", "Name", "Description", "Priority"]
        assert rows[1][3] == "none"

    def test_unknown_field_is_rejected(self, session_client, workspace, project, cycle):
        response = session_client.get(_export_url(workspace.slug, project.id, cycle.id, fields="not_a_real_field"))
        assert response.status_code == 400

    def test_unknown_format_is_rejected(self, session_client, workspace, project, cycle):
        response = session_client.get(_export_url(workspace.slug, project.id, cycle.id, export_format="xlsx"))
        assert response.status_code == 400

    def test_missing_cycle_returns_404(self, session_client, workspace, project):
        response = session_client.get(
            _export_url(workspace.slug, project.id, "00000000-0000-0000-0000-000000000000")
        )
        assert response.status_code == 404

    def test_draft_issues_are_excluded(self, session_client, workspace, project, cycle, cycle_issue, create_user):
        draft = Issue.objects.create(
            name="Draft issue",
            project=project,
            workspace=project.workspace,
            created_by=create_user,
            is_draft=True,
        )
        CycleIssue.objects.create(issue=draft, cycle=cycle, project=project, workspace=project.workspace)

        response = session_client.get(_export_url(workspace.slug, project.id, cycle.id))
        content = response.content.decode("utf-8")
        assert "Draft issue" not in content

    def test_csv_formula_value_is_sanitized(self, session_client, workspace, project, cycle, create_user):
        issue = Issue.objects.create(
            name="=cmd|'/c calc'!A0",
            project=project,
            workspace=project.workspace,
            created_by=create_user,
        )
        CycleIssue.objects.create(issue=issue, cycle=cycle, project=project, workspace=project.workspace)

        response = session_client.get(_export_url(workspace.slug, project.id, cycle.id))
        rows = list(csv.reader(StringIO(response.content.decode("utf-8"))))
        [row] = [r for r in rows[1:] if "cmd" in r[1]]
        assert row[1].startswith("'=")

    def test_requires_project_membership(self, api_client, workspace, project, cycle):
        from plane.db.models import User

        outsider = User.objects.create(email="outsider@plane.so", username="outsider")
        outsider.set_password("outsider@123")
        outsider.save()
        api_client.force_authenticate(user=outsider)

        response = api_client.get(_export_url(workspace.slug, project.id, cycle.id))
        assert response.status_code in (403, 404)
