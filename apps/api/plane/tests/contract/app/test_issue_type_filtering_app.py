# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import json

import pytest
from rest_framework import status

from plane.db.models import (
    Issue,
    IssueType,
    Project,
    ProjectIssueType,
    ProjectMember,
    State,
)


@pytest.mark.contract
class TestIssueTypeFilterGroupOrder:
    """
    Contract coverage for filtering, grouping and ordering work items by their type.

    The three paths are deliberately separate on the backend: rich-filters go
    through IssueFilterSet, pagination within one group goes through the legacy
    flat `issue_type` param, and ordering goes through ISSUE_ORDER_BY_ALLOWLIST.
    """

    @pytest.fixture
    def typed_project(self, workspace, create_user):
        project = Project.objects.create(
            name="Typed project", identifier="TYPF", workspace=workspace, is_issue_type_enabled=True
        )
        ProjectMember.objects.create(project=project, member=create_user, role=20)
        state = State.objects.create(name="Backlog", group="backlog", project=project, workspace=workspace)

        # Levels are set explicitly: ordering must follow the link's level, not
        # the order the types happened to be created in.
        types = {}
        for level, name in enumerate(["Task", "Bug", "Spike"]):
            issue_type = IssueType.objects.create(workspace=workspace, name=name, is_active=True)
            ProjectIssueType.objects.create(
                project=project, issue_type=issue_type, level=level, is_default=(name == "Task")
            )
            types[name] = issue_type

        for name, issue_type in [
            ("A task", types["Task"]),
            ("A bug", types["Bug"]),
            ("A spike", types["Spike"]),
            ("No type", None),
        ]:
            Issue.objects.create(
                name=name,
                project=project,
                workspace=workspace,
                state=state,
                type=issue_type,
                created_by=create_user,
            )

        return {"project": project, "types": types}

    @staticmethod
    def issues_url(workspace_slug, project_id):
        return f"/api/workspaces/{workspace_slug}/projects/{project_id}/issues/"

    def get_issues(self, session_client, workspace, project, **params):
        response = session_client.get(self.issues_url(workspace.slug, project.id), params)
        assert response.status_code == status.HTTP_200_OK, response.data
        return response.data

    @pytest.mark.django_db
    def test_rich_filter_narrows_to_one_type(self, session_client, workspace, typed_project):
        ctx = typed_project
        data = self.get_issues(
            session_client,
            workspace,
            ctx["project"],
            filters=json.dumps({"type_id__in": [str(ctx["types"]["Bug"].id)]}),
        )

        assert [row["name"] for row in data["results"]] == ["A bug"]

    @pytest.mark.django_db
    def test_rich_filter_accepts_several_types(self, session_client, workspace, typed_project):
        ctx = typed_project
        data = self.get_issues(
            session_client,
            workspace,
            ctx["project"],
            filters=json.dumps({"type_id__in": f"{ctx['types']['Bug'].id},{ctx['types']['Spike'].id}"}),
        )

        assert {row["name"] for row in data["results"]} == {"A bug", "A spike"}

    @pytest.mark.django_db
    def test_rich_filter_accepts_several_types_as_a_json_array(self, session_client, workspace, typed_project):
        """The shape the frontend actually sends: multi-select serialises to an array."""
        ctx = typed_project
        data = self.get_issues(
            session_client,
            workspace,
            ctx["project"],
            filters=json.dumps({"type_id__in": [str(ctx["types"]["Bug"].id), str(ctx["types"]["Spike"].id)]}),
        )

        assert {row["name"] for row in data["results"]} == {"A bug", "A spike"}

    @pytest.mark.django_db
    def test_legacy_param_narrows_to_one_type(self, session_client, workspace, typed_project):
        """The in-group pagination path uses this flat param, not rich-filters."""
        ctx = typed_project
        data = self.get_issues(session_client, workspace, ctx["project"], issue_type=str(ctx["types"]["Bug"].id))

        assert [row["name"] for row in data["results"]] == ["A bug"]

    @pytest.mark.django_db
    def test_legacy_param_accepts_several_types(self, session_client, workspace, typed_project):
        ctx = typed_project
        data = self.get_issues(
            session_client,
            workspace,
            ctx["project"],
            issue_type=f"{ctx['types']['Bug'].id},{ctx['types']['Spike'].id}",
        )

        assert {row["name"] for row in data["results"]} == {"A bug", "A spike"}

    @pytest.mark.django_db
    def test_legacy_param_none_returns_untyped_work_items(self, session_client, workspace, typed_project):
        ctx = typed_project
        data = self.get_issues(session_client, workspace, ctx["project"], issue_type="None")

        assert [row["name"] for row in data["results"]] == ["No type"]

    @pytest.mark.django_db
    def test_group_by_type_lists_every_project_type_plus_none(self, session_client, workspace, typed_project):
        ctx = typed_project
        data = self.get_issues(session_client, workspace, ctx["project"], group_by="type_id", per_page="100")

        # Groups arrive in the project's configured type order, with untyped last.
        expected = [str(ctx["types"][name].id) for name in ["Task", "Bug", "Spike"]] + ["None"]
        assert list(data["results"].keys()) == expected

        bug_group = data["results"][str(ctx["types"]["Bug"].id)]
        assert [row["name"] for row in bug_group["results"]] == ["A bug"]
        assert bug_group["total_results"] == 1
        assert [row["name"] for row in data["results"]["None"]["results"]] == ["No type"]

    @pytest.mark.django_db
    def test_group_by_type_includes_types_with_no_work_items(self, session_client, workspace, typed_project):
        """Empty columns still have to render, so the group must come back empty, not missing."""
        ctx = typed_project
        extra = IssueType.objects.create(workspace=workspace, name="Chore", is_active=True)
        ProjectIssueType.objects.create(project=ctx["project"], issue_type=extra, level=3)

        data = self.get_issues(session_client, workspace, ctx["project"], group_by="type_id", per_page="100")

        assert str(extra.id) in data["results"]
        assert data["results"][str(extra.id)]["results"] == []

    @pytest.mark.django_db
    def test_order_by_type_level_follows_project_settings(self, session_client, workspace, typed_project):
        data = self.get_issues(
            session_client, workspace, typed_project["project"], order_by="type__level", per_page="100"
        )

        # Task(0), Bug(1), Spike(2), then the untyped work item.
        assert [row["name"] for row in data["results"]] == ["A task", "A bug", "A spike", "No type"]

    @pytest.mark.django_db
    def test_order_by_type_level_descending_still_puts_untyped_last(self, session_client, workspace, typed_project):
        data = self.get_issues(
            session_client, workspace, typed_project["project"], order_by="-type__level", per_page="100"
        )

        assert [row["name"] for row in data["results"]] == ["A spike", "A bug", "A task", "No type"]

    @pytest.mark.django_db
    def test_order_by_follows_the_link_level_not_creation_order(self, session_client, workspace, typed_project):
        """Reordering types in project settings must reorder the work items."""
        ctx = typed_project
        ProjectIssueType.objects.filter(project=ctx["project"], issue_type=ctx["types"]["Spike"]).update(level=0)
        ProjectIssueType.objects.filter(project=ctx["project"], issue_type=ctx["types"]["Task"]).update(level=2)

        data = self.get_issues(session_client, workspace, ctx["project"], order_by="type__level", per_page="100")

        assert [row["name"] for row in data["results"]] == ["A spike", "A bug", "A task", "No type"]
