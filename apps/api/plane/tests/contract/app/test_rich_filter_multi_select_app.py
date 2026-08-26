# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import json

import pytest
from rest_framework import status

from plane.db.models import (
    Issue,
    IssueLabel,
    Label,
    Project,
    ProjectMember,
    State,
)


@pytest.mark.contract
class TestRichFilterMultiSelect:
    """
    Multi-select rich filters must apply every selected value.

    The frontend serialises a whole filter expression with `JSON.stringify`, so a
    multi-select condition arrives as a JSON array. `_build_leaf_q` used to load
    those into a QueryDict with `setlist`, but the `__in` filters are django-filter
    CSV filters whose widget reads the raw value with `data.get()` -- which returns
    only the last entry of a multi-value QueryDict key. Every multi-select filter
    silently applied one value.
    """

    @pytest.fixture
    def filter_context(self, workspace, create_user):
        project = Project.objects.create(name="Filter project", identifier="FLT", workspace=workspace)
        ProjectMember.objects.create(project=project, member=create_user, role=20)

        states = {
            name: State.objects.create(name=name, group=group, project=project, workspace=workspace)
            for name, group in [("Backlog", "backlog"), ("Started", "started"), ("Done", "completed")]
        }
        labels = {
            name: Label.objects.create(name=name, project=project, workspace=workspace)
            for name in ["Frontend", "Backend", "Infra"]
        }

        issues = {}
        for issue_name, state_name, label_name, priority in [
            ("first", "Backlog", "Frontend", "urgent"),
            ("second", "Started", "Backend", "high"),
            ("third", "Done", "Infra", "low"),
        ]:
            issue = Issue.objects.create(
                name=issue_name,
                project=project,
                workspace=workspace,
                state=states[state_name],
                priority=priority,
                created_by=create_user,
            )
            IssueLabel.objects.create(issue=issue, label=labels[label_name], project=project, workspace=workspace)
            issues[issue_name] = issue

        return {"project": project, "states": states, "labels": labels, "issues": issues}

    def get_names(self, session_client, workspace, project, filter_expression):
        response = session_client.get(
            f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/",
            {"filters": json.dumps(filter_expression)},
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        return {row["name"] for row in response.data["results"]}

    @pytest.mark.django_db
    def test_state_id_in_applies_every_value(self, session_client, workspace, filter_context):
        ctx = filter_context
        names = self.get_names(
            session_client,
            workspace,
            ctx["project"],
            {"state_id__in": [str(ctx["states"]["Backlog"].id), str(ctx["states"]["Started"].id)]},
        )

        assert names == {"first", "second"}

    @pytest.mark.django_db
    def test_label_id_in_applies_every_value(self, session_client, workspace, filter_context):
        ctx = filter_context
        names = self.get_names(
            session_client,
            workspace,
            ctx["project"],
            {"label_id__in": [str(ctx["labels"]["Frontend"].id), str(ctx["labels"]["Infra"].id)]},
        )

        assert names == {"first", "third"}

    @pytest.mark.django_db
    def test_priority_in_applies_every_value(self, session_client, workspace, filter_context):
        names = self.get_names(
            session_client, workspace, filter_context["project"], {"priority__in": ["urgent", "low"]}
        )

        assert names == {"first", "third"}

    @pytest.mark.django_db
    def test_single_value_filters_are_unaffected(self, session_client, workspace, filter_context):
        ctx = filter_context
        names = self.get_names(session_client, workspace, ctx["project"], {"state_id": str(ctx["states"]["Done"].id)})

        assert names == {"third"}
