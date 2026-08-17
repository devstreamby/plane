# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest
from rest_framework import status

from plane.db.models import (
    Issue,
    IssueType,
    Project,
    ProjectIssueType,
    ProjectMember,
    User,
    WorkspaceMember,
)


@pytest.mark.contract
class TestIssueTypeEndpoint:
    """Contract coverage for the project work-item-types endpoints."""

    @pytest.fixture
    def type_context(self, workspace, create_user):
        project = Project.objects.create(name="Typed project", identifier="TYP", workspace=workspace)
        ProjectMember.objects.create(project=project, member=create_user, role=20)

        member = User.objects.create_user(email="type-member@plane.so", username="type_member")
        WorkspaceMember.objects.create(workspace=workspace, member=member, role=15)
        ProjectMember.objects.create(project=project, member=member, role=15)

        guest = User.objects.create_user(email="type-guest@plane.so", username="type_guest")
        WorkspaceMember.objects.create(workspace=workspace, member=guest, role=5)
        ProjectMember.objects.create(project=project, member=guest, role=5)

        task_type = IssueType.objects.create(workspace=workspace, name="Task", is_active=True)
        ProjectIssueType.objects.create(project=project, issue_type=task_type, is_default=True)

        bug_type = IssueType.objects.create(workspace=workspace, name="Bug", is_active=True)
        ProjectIssueType.objects.create(project=project, issue_type=bug_type, is_default=False)

        return {
            "project": project,
            "member": member,
            "guest": guest,
            "task_type": task_type,
            "bug_type": bug_type,
        }

    @staticmethod
    def list_url(workspace_slug, project_id):
        return f"/api/workspaces/{workspace_slug}/projects/{project_id}/issue-types/"

    @staticmethod
    def detail_url(workspace_slug, project_id, type_id):
        return f"/api/workspaces/{workspace_slug}/projects/{project_id}/issue-types/{type_id}/"

    @staticmethod
    def mark_default_url(workspace_slug, project_id, type_id):
        return f"/api/workspaces/{workspace_slug}/projects/{project_id}/issue-types/{type_id}/mark-default/"

    @pytest.mark.django_db
    def test_list_returns_seeded_types(self, session_client, workspace, type_context):
        ctx = type_context
        response = session_client.get(self.list_url(workspace.slug, ctx["project"].id))

        assert response.status_code == status.HTTP_200_OK
        names = {row["name"] for row in response.data}
        assert names == {"Task", "Bug"}
        task_row = next(row for row in response.data if row["name"] == "Task")
        assert task_row["is_default"] is True
        bug_row = next(row for row in response.data if row["name"] == "Bug")
        assert bug_row["is_default"] is False

    @pytest.mark.django_db
    def test_create_type_makes_both_rows(self, session_client, workspace, type_context):
        ctx = type_context
        response = session_client.post(
            self.list_url(workspace.slug, ctx["project"].id),
            {"name": "Story", "description": "A user story"},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert response.data["name"] == "Story"
        assert response.data["is_default"] is False

        issue_type = IssueType.objects.get(workspace=workspace, name="Story")
        assert ProjectIssueType.objects.filter(project=ctx["project"], issue_type=issue_type).exists()

    @pytest.mark.django_db
    def test_duplicate_active_name_rejected(self, session_client, workspace, type_context):
        ctx = type_context
        response = session_client.post(
            self.list_url(workspace.slug, ctx["project"].id), {"name": "Bug"}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_delete_default_type_rejected(self, session_client, workspace, type_context):
        ctx = type_context
        response = session_client.delete(self.detail_url(workspace.slug, ctx["project"].id, ctx["task_type"].id))
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        ctx["task_type"].refresh_from_db()
        assert ctx["task_type"].is_active is True

    @pytest.mark.django_db
    def test_delete_in_use_type_rejected(self, session_client, workspace, type_context, create_user):
        ctx = type_context
        Issue.objects.create(
            name="Typed issue",
            project=ctx["project"],
            workspace=workspace,
            type=ctx["bug_type"],
            created_by=create_user,
        )

        response = session_client.delete(self.detail_url(workspace.slug, ctx["project"].id, ctx["bug_type"].id))
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["issues_count"] == 1

    @pytest.mark.django_db
    def test_delete_unused_non_default_type_deactivates(self, session_client, workspace, type_context):
        ctx = type_context
        response = session_client.delete(self.detail_url(workspace.slug, ctx["project"].id, ctx["bug_type"].id))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        ctx["bug_type"].refresh_from_db()
        assert ctx["bug_type"].is_active is False

    @pytest.mark.django_db
    def test_mark_as_default_moves_flag(self, session_client, workspace, type_context):
        ctx = type_context
        response = session_client.post(self.mark_default_url(workspace.slug, ctx["project"].id, ctx["bug_type"].id))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_default"] is True

        assert not ProjectIssueType.objects.get(project=ctx["project"], issue_type=ctx["task_type"]).is_default
        assert ProjectIssueType.objects.get(project=ctx["project"], issue_type=ctx["bug_type"]).is_default

    @pytest.mark.django_db
    def test_mark_as_default_rejects_inactive_type(self, session_client, workspace, type_context):
        ctx = type_context
        ctx["bug_type"].is_active = False
        ctx["bug_type"].save(update_fields=["is_active"])

        response = session_client.post(self.mark_default_url(workspace.slug, ctx["project"].id, ctx["bug_type"].id))
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_member_can_read_but_not_write(self, session_client, workspace, type_context):
        ctx = type_context
        session_client.force_authenticate(user=ctx["member"])

        assert session_client.get(self.list_url(workspace.slug, ctx["project"].id)).status_code == status.HTTP_200_OK

        response = session_client.post(
            self.list_url(workspace.slug, ctx["project"].id), {"name": "Nope"}, format="json"
        )
        assert response.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED)

    @pytest.mark.django_db
    def test_guest_can_read(self, session_client, workspace, type_context):
        ctx = type_context
        session_client.force_authenticate(user=ctx["guest"])

        response = session_client.get(self.list_url(workspace.slug, ctx["project"].id))
        assert response.status_code == status.HTTP_200_OK
