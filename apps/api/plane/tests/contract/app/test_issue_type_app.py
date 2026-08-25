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

    @staticmethod
    def issue_url(workspace_slug, project_id, issue_id):
        return f"/api/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/"

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
        response = session_client.post(self.list_url(workspace.slug, ctx["project"].id), {"name": "Bug"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_duplicate_inactive_name_rejected(self, session_client, workspace, type_context):
        """A deactivated type still holds its name, so reusing it must 400, not 500."""
        ctx = type_context
        ctx["bug_type"].is_active = False
        ctx["bug_type"].save(update_fields=["is_active"])

        response = session_client.post(self.list_url(workspace.slug, ctx["project"].id), {"name": "Bug"}, format="json")
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
    def test_delete_unused_non_default_type_removes_it_from_the_list(self, session_client, workspace, type_context):
        ctx = type_context
        response = session_client.delete(self.detail_url(workspace.slug, ctx["project"].id, ctx["bug_type"].id))
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # The project link is soft-deleted, and with no other project using the type
        # the workspace-level row goes too.
        assert not ProjectIssueType.objects.filter(project=ctx["project"], issue_type=ctx["bug_type"]).exists()
        assert not IssueType.objects.filter(pk=ctx["bug_type"].id).exists()

        listed = session_client.get(self.list_url(workspace.slug, ctx["project"].id))
        assert {row["name"] for row in listed.data} == {"Task"}

    @pytest.mark.django_db
    def test_delete_only_unlinks_the_current_project(self, session_client, workspace, type_context, create_user):
        """Types are workspace-scoped and shared, so a delete must not touch siblings."""
        ctx = type_context
        other_project = Project.objects.create(name="Other project", identifier="OTH", workspace=workspace)
        ProjectMember.objects.create(project=other_project, member=create_user, role=20)
        ProjectIssueType.objects.create(project=other_project, issue_type=ctx["bug_type"], is_default=False)

        response = session_client.delete(self.detail_url(workspace.slug, ctx["project"].id, ctx["bug_type"].id))
        assert response.status_code == status.HTTP_204_NO_CONTENT

        assert not ProjectIssueType.objects.filter(project=ctx["project"], issue_type=ctx["bug_type"]).exists()
        assert ProjectIssueType.objects.filter(project=other_project, issue_type=ctx["bug_type"]).exists()
        assert IssueType.objects.filter(pk=ctx["bug_type"].id).exists()

    @pytest.mark.django_db
    def test_deleted_name_can_be_created_again(self, session_client, workspace, type_context):
        ctx = type_context
        assert (
            session_client.delete(self.detail_url(workspace.slug, ctx["project"].id, ctx["bug_type"].id)).status_code
            == status.HTTP_204_NO_CONTENT
        )

        response = session_client.post(self.list_url(workspace.slug, ctx["project"].id), {"name": "Bug"}, format="json")
        assert response.status_code == status.HTTP_201_CREATED, response.data

    @pytest.mark.django_db
    def test_enabling_the_feature_seeds_the_defaults_once(self, session_client, workspace, create_user):
        project = Project.objects.create(name="Fresh project", identifier="FRSH", workspace=workspace)
        ProjectMember.objects.create(project=project, member=create_user, role=20)
        url = f"/api/workspaces/{workspace.slug}/projects/{project.id}/"

        assert (
            session_client.patch(url, {"is_issue_type_enabled": True}, format="json").status_code == status.HTTP_200_OK
        )
        assert ProjectIssueType.objects.filter(project=project).count() == 6

        # A second fetch used to race the enabling PATCH and seed a duplicate set.
        assert session_client.get(self.list_url(workspace.slug, project.id)).status_code == status.HTTP_200_OK
        assert IssueType.objects.filter(workspace=workspace).count() == 6
        assert ProjectIssueType.objects.filter(project=project).count() == 6

    @pytest.mark.django_db
    def test_project_save_does_not_resurrect_a_deleted_type(self, session_client, workspace, create_user):
        project = Project.objects.create(name="Fresh project", identifier="FRSH", workspace=workspace)
        ProjectMember.objects.create(project=project, member=create_user, role=20)
        url = f"/api/workspaces/{workspace.slug}/projects/{project.id}/"
        session_client.patch(url, {"is_issue_type_enabled": True}, format="json")

        spike = IssueType.objects.get(workspace=workspace, name="Spike")
        assert (
            session_client.delete(self.detail_url(workspace.slug, project.id, spike.id)).status_code
            == status.HTTP_204_NO_CONTENT
        )

        # The defaults are seeded on the off -> on transition only, so an unrelated
        # settings save must not bring Spike back.
        assert session_client.patch(url, {"name": "Renamed project"}, format="json").status_code == status.HTTP_200_OK

        listed = session_client.get(self.list_url(workspace.slug, project.id))
        assert "Spike" not in {row["name"] for row in listed.data}

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

    @pytest.mark.django_db
    def test_update_work_item_type_changes_type(self, session_client, workspace, type_context, create_user):
        ctx = type_context
        issue = Issue.objects.create(
            name="Typed issue",
            project=ctx["project"],
            workspace=workspace,
            type=ctx["task_type"],
            created_by=create_user,
        )

        response = session_client.patch(
            self.issue_url(workspace.slug, ctx["project"].id, issue.id),
            {"type_id": str(ctx["bug_type"].id)},
            format="json",
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT, response.data
        issue.refresh_from_db()
        assert issue.type_id == ctx["bug_type"].id

    @pytest.mark.django_db
    def test_update_work_item_type_rejects_type_not_in_project(
        self, session_client, workspace, type_context, create_user
    ):
        ctx = type_context
        issue = Issue.objects.create(
            name="Typed issue",
            project=ctx["project"],
            workspace=workspace,
            type=ctx["task_type"],
            created_by=create_user,
        )
        foreign_type = IssueType.objects.create(workspace=workspace, name="Foreign", is_active=True)

        response = session_client.patch(
            self.issue_url(workspace.slug, ctx["project"].id, issue.id),
            {"type_id": str(foreign_type.id)},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        issue.refresh_from_db()
        assert issue.type_id == ctx["task_type"].id

    @pytest.mark.django_db
    def test_guest_cannot_update_work_item_type(self, session_client, workspace, type_context, create_user):
        ctx = type_context
        issue = Issue.objects.create(
            name="Typed issue",
            project=ctx["project"],
            workspace=workspace,
            type=ctx["task_type"],
            created_by=create_user,
        )
        session_client.force_authenticate(user=ctx["guest"])

        response = session_client.patch(
            self.issue_url(workspace.slug, ctx["project"].id, issue.id),
            {"type_id": str(ctx["bug_type"].id)},
            format="json",
        )

        assert response.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED)
        issue.refresh_from_db()
        assert issue.type_id == ctx["task_type"].id
