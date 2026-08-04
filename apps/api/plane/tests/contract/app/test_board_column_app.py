# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest
from rest_framework import status

from plane.db.models import (
    BoardColumn,
    Project,
    ProjectMember,
    State,
    StateGroup,
    User,
    WorkspaceMember,
)


@pytest.mark.contract
class TestBoardColumnEndpoint:
    """Contract coverage for the project board-columns endpoints."""

    @pytest.fixture
    def board_context(self, workspace, create_user):
        project = Project.objects.create(name="Board project", identifier="BRD", workspace=workspace)
        ProjectMember.objects.create(project=project, member=create_user, role=20)

        member = User.objects.create_user(email="board-member@plane.so", username="board_member")
        WorkspaceMember.objects.create(workspace=workspace, member=member, role=15)
        ProjectMember.objects.create(project=project, member=member, role=15)

        def make_state(name, group=StateGroup.UNSTARTED.value):
            return State.objects.create(name=name, color="#000000", group=group, project=project, workspace=workspace)

        return {
            "project": project,
            "member": member,
            "todo": make_state("Todo"),
            "in_progress": make_state("In Progress", StateGroup.STARTED.value),
            "in_review": make_state("In Review", StateGroup.STARTED.value),
            "done": make_state("Done", StateGroup.COMPLETED.value),
        }

    @staticmethod
    def list_url(workspace_slug, project_id):
        return f"/api/workspaces/{workspace_slug}/projects/{project_id}/board-columns/"

    @staticmethod
    def detail_url(workspace_slug, project_id, column_id):
        return f"/api/workspaces/{workspace_slug}/projects/{project_id}/board-columns/{column_id}/"

    @pytest.mark.django_db
    def test_create_with_states(self, session_client, workspace, board_context):
        ctx = board_context
        response = session_client.post(
            self.list_url(workspace.slug, ctx["project"].id),
            {"name": "In flight", "state_ids": [str(ctx["in_progress"].id), str(ctx["in_review"].id)]},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert response.data["name"] == "In flight"
        assert set(response.data["state_ids"]) == {str(ctx["in_progress"].id), str(ctx["in_review"].id)}

    @pytest.mark.django_db
    def test_list_returns_columns_in_sequence_order(self, session_client, workspace, board_context):
        ctx = board_context
        # New columns are appended, so the second one starts to the right of the first.
        first = BoardColumn.objects.create(name="First", project=ctx["project"], workspace=workspace)
        second = BoardColumn.objects.create(name="Second", project=ctx["project"], workspace=workspace)

        response = session_client.get(self.list_url(workspace.slug, ctx["project"].id))
        assert response.status_code == status.HTTP_200_OK
        assert [str(column["id"]) for column in response.data] == [str(first.id), str(second.id)]

        # Moving the second column to the front reorders the list
        response = session_client.patch(
            self.detail_url(workspace.slug, ctx["project"].id, second.id),
            {"sequence": first.sequence - 100},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK, response.data

        response = session_client.get(self.list_url(workspace.slug, ctx["project"].id))
        assert [str(column["id"]) for column in response.data] == [str(second.id), str(first.id)]

    @pytest.mark.django_db
    def test_state_ids_bulk_replace_moves_state_between_columns(self, session_client, workspace, board_context):
        ctx = board_context
        source = BoardColumn.objects.create(name="Source", project=ctx["project"], workspace=workspace)
        target = BoardColumn.objects.create(name="Target", project=ctx["project"], workspace=workspace)
        State.objects.filter(id=ctx["todo"].id).update(board_column=source)

        response = session_client.patch(
            self.detail_url(workspace.slug, ctx["project"].id, target.id),
            {"state_ids": [str(ctx["todo"].id)]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["state_ids"] == [str(ctx["todo"].id)]
        ctx["todo"].refresh_from_db()
        assert ctx["todo"].board_column_id == target.id

        # The state left the source column
        assert not State.objects.filter(board_column=source).exists()

    @pytest.mark.django_db
    def test_state_ids_bulk_replace_unmaps_dropped_states(self, session_client, workspace, board_context):
        ctx = board_context
        column = BoardColumn.objects.create(name="Column", project=ctx["project"], workspace=workspace)
        State.objects.filter(id__in=[ctx["todo"].id, ctx["done"].id]).update(board_column=column)

        response = session_client.patch(
            self.detail_url(workspace.slug, ctx["project"].id, column.id),
            {"state_ids": [str(ctx["todo"].id)]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        ctx["done"].refresh_from_db()
        assert ctx["done"].board_column_id is None

    @pytest.mark.django_db
    def test_rejects_foreign_state(self, session_client, workspace, board_context):
        ctx = board_context
        other_project = Project.objects.create(name="Other board", identifier="OTB", workspace=workspace)
        foreign_state = State.objects.create(
            name="Foreign", color="#000000", project=other_project, workspace=workspace
        )
        column = BoardColumn.objects.create(name="Column", project=ctx["project"], workspace=workspace)

        response = session_client.patch(
            self.detail_url(workspace.slug, ctx["project"].id, column.id),
            {"state_ids": [str(foreign_state.id)]},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_delete_keeps_states_and_unmaps_them(self, session_client, workspace, board_context):
        ctx = board_context
        column = BoardColumn.objects.create(name="Column", project=ctx["project"], workspace=workspace)
        State.objects.filter(id=ctx["todo"].id).update(board_column=column)

        response = session_client.delete(self.detail_url(workspace.slug, ctx["project"].id, column.id))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        ctx["todo"].refresh_from_db()
        assert ctx["todo"].board_column_id is None

    @pytest.mark.django_db
    def test_member_can_read_but_not_write(self, session_client, workspace, board_context):
        ctx = board_context
        session_client.force_authenticate(user=ctx["member"])

        assert session_client.get(self.list_url(workspace.slug, ctx["project"].id)).status_code == status.HTTP_200_OK

        response = session_client.post(
            self.list_url(workspace.slug, ctx["project"].id), {"name": "Nope"}, format="json"
        )
        assert response.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED)
