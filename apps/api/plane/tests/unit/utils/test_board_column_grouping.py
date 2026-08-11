# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest
from django.http import QueryDict

from plane.db.models import BoardColumn, Issue, Project, ProjectMember, State, StateGroup
from plane.utils.filters.filterset import IssueFilterSet
from plane.utils.grouper import BOARD_COLUMN_FIELD, issue_group_values
from plane.utils.issue_filters import issue_filters


@pytest.mark.unit
class TestBoardColumnGroupValues:
    @pytest.fixture
    def board_context(self, workspace, create_user):
        project = Project.objects.create(name="Board project", identifier="BRD", workspace=workspace)
        ProjectMember.objects.create(project=project, member=create_user, role=20)
        other_project = Project.objects.create(name="Other board", identifier="OTB", workspace=workspace)

        return {
            "project": project,
            "other_project": other_project,
            "first": BoardColumn.objects.create(name="First", project=project, workspace=workspace, sequence=100),
            "second": BoardColumn.objects.create(name="Second", project=project, workspace=workspace, sequence=200),
            "foreign": BoardColumn.objects.create(
                name="Foreign", project=other_project, workspace=workspace, sequence=100
            ),
        }

    @pytest.mark.django_db
    def test_project_scoped_values_include_unmapped_group(self, workspace, board_context):
        values = issue_group_values(
            field=BOARD_COLUMN_FIELD, slug=workspace.slug, project_id=board_context["project"].id
        )

        assert set(values) == {board_context["first"].id, board_context["second"].id, "None"}

    @pytest.mark.django_db
    def test_workspace_scoped_values_span_projects(self, workspace, board_context):
        values = issue_group_values(field=BOARD_COLUMN_FIELD, slug=workspace.slug)

        assert board_context["foreign"].id in values
        assert "None" in values


@pytest.mark.unit
class TestBoardColumnFilter:
    @pytest.mark.django_db
    def test_filters_by_column_ids(self, workspace, create_user):
        project = Project.objects.create(name="Filter project", identifier="FLT", workspace=workspace)
        ProjectMember.objects.create(project=project, member=create_user, role=20)
        column = BoardColumn.objects.create(name="Column", project=project, workspace=workspace)

        filters = issue_filters({"board_column": str(column.id)}, "GET")

        assert filters == {"state__board_column__in": [column.id]}

    def test_none_selects_unmapped_states(self):
        assert issue_filters({"board_column": "None"}, "GET") == {"state__board_column__isnull": True}

    def test_ignores_empty_value(self):
        assert issue_filters({"board_column": "null"}, "GET") == {}

    @pytest.mark.django_db
    def test_rich_filter_selects_issues_by_column_id(self, workspace, create_user):
        project = Project.objects.create(name="Rich filter project", identifier="RCH", workspace=workspace)
        ProjectMember.objects.create(project=project, member=create_user, role=20)
        column = BoardColumn.objects.create(name="Column", project=project, workspace=workspace)
        state = State.objects.create(
            name="Todo",
            color="#000000",
            group=StateGroup.UNSTARTED.value,
            project=project,
            workspace=workspace,
            board_column=column,
        )
        unmapped_state = State.objects.create(
            name="Backlog",
            color="#000000",
            group=StateGroup.BACKLOG.value,
            project=project,
            workspace=workspace,
        )
        matching_issue = Issue.objects.create(name="Matching", project=project, workspace=workspace, state=state)
        Issue.objects.create(name="Unmapped", project=project, workspace=workspace, state=unmapped_state)

        filter_data = QueryDict(mutable=True)
        filter_data["board_column_id__in"] = str(column.id)
        filter_set = IssueFilterSet(data=filter_data, queryset=Issue.objects.all())
        assert filter_set.is_valid(), filter_set.errors
        combined_filter = filter_set.build_combined_q()
        filtered_issues = Issue.objects.filter(combined_filter)

        assert list(filtered_issues) == [matching_issue]


@pytest.mark.unit
class TestBoardColumnSequencing:
    @pytest.mark.django_db
    def test_new_columns_are_appended(self, workspace, create_user):
        project = Project.objects.create(name="Sequence project", identifier="SEQ", workspace=workspace)
        ProjectMember.objects.create(project=project, member=create_user, role=20)

        first = BoardColumn.objects.create(name="First", project=project, workspace=workspace)
        second = BoardColumn.objects.create(name="Second", project=project, workspace=workspace)

        assert second.sequence > first.sequence

    @pytest.mark.django_db
    def test_explicit_sequence_survives_an_update(self, workspace, create_user):
        project = Project.objects.create(name="Reorder project", identifier="RDR", workspace=workspace)
        ProjectMember.objects.create(project=project, member=create_user, role=20)

        first = BoardColumn.objects.create(name="First", project=project, workspace=workspace)
        second = BoardColumn.objects.create(name="Second", project=project, workspace=workspace)

        # Only creation auto-appends, reordering an existing column keeps the sequence it is given.
        second.sequence = first.sequence - 100
        second.save()
        second.refresh_from_db()

        assert second.sequence < first.sequence
        assert list(BoardColumn.objects.filter(project=project).values_list("id", flat=True)) == [
            second.id,
            first.id,
        ]

    @pytest.mark.django_db
    def test_soft_deleted_column_keeps_its_states(self, workspace, create_user):
        """Columns are soft-deleted, so `SET_NULL` never fires and the endpoint unmaps the states itself."""
        project = Project.objects.create(name="Delete project", identifier="DEL", workspace=workspace)
        ProjectMember.objects.create(project=project, member=create_user, role=20)
        column = BoardColumn.objects.create(name="Column", project=project, workspace=workspace)
        state = State.objects.create(
            name="Todo",
            color="#000000",
            group=StateGroup.UNSTARTED.value,
            project=project,
            workspace=workspace,
            board_column=column,
        )

        column.delete()

        assert State.objects.filter(id=state.id).exists()
        assert not BoardColumn.objects.filter(id=column.id).exists()
