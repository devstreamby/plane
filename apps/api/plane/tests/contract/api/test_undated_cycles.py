# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from plane.db.models import Cycle, Project, ProjectMember, WorkspaceMember
from plane.utils.cycle_status import cycle_status_expression, get_cycle_status

pytestmark = [pytest.mark.contract, pytest.mark.django_db]


@pytest.fixture
def project(workspace, create_user):
    project = Project.objects.create(name="Manual cycles", identifier="MC", workspace=workspace, cycle_view=True)
    ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
    return project


@pytest.fixture
def cycle(project, create_user):
    return Cycle.objects.create(name="No dates", project=project, workspace=project.workspace, owned_by=create_user)


def url(project, suffix="", public=False):
    prefix = "/api/v1" if public else "/api"
    return f"{prefix}/workspaces/{project.workspace.slug}/projects/{project.id}/cycles/{suffix}"


@patch("plane.app.views.cycle.base.model_activity.delay")
def test_create_start_complete_and_archive(_activity, session_client, project):
    created = session_client.post(url(project), {"name": "Manual"}, format="json")
    assert created.status_code == 201, created.data
    pk = created.data["id"]
    assert created.data["status"] == "DRAFT"
    for action, expected in [("start", "CURRENT"), ("complete", "COMPLETED")]:
        response = session_client.post(url(project, f"{pk}/{action}/"), {}, format="json")
        assert response.status_code == 200, response.data
        assert response.data["status"] == expected
        assert response.data["start_date"] is None
        assert response.data["end_date"] is None
        assert session_client.post(url(project, f"{pk}/{action}/")).status_code == 400
        listing = session_client.get(url(project), {"cycle_view": "current"})
        assert (str(pk) in [str(c["id"]) for c in listing.data]) == (expected == "CURRENT")
    assert session_client.post(url(project, f"{pk}/archive/")).status_code == 200
    assert session_client.delete(url(project, f"{pk}/archive/")).status_code == 204
    cycle = Cycle.objects.get(pk=pk)
    assert get_cycle_status(cycle) == "COMPLETED"
    assert cycle.start_date is None and cycle.end_date is None


@pytest.mark.parametrize("state,action", [("DRAFT", "complete"), ("COMPLETED", "start"), ("COMPLETED", "complete")])
def test_invalid_transitions(session_client, project, cycle, state, action):
    cycle.manual_status = state
    cycle.save()
    assert session_client.post(url(project, f"{cycle.id}/{action}/")).status_code == 400
    cycle.refresh_from_db()
    assert cycle.manual_status == state


@pytest.mark.parametrize("role", [5, 10])
def test_viewers_cannot_start(session_client, project, cycle, role):
    ProjectMember.objects.filter(project=project).update(role=role)
    WorkspaceMember.objects.filter(workspace=project.workspace).update(role=role)
    assert session_client.post(url(project, f"{cycle.id}/start/")).status_code == 403
    cycle.refresh_from_db()
    assert cycle.manual_status == "DRAFT"


@pytest.mark.parametrize("state", ["DRAFT", "CURRENT", "COMPLETED"])
def test_public_filters_match_manual_status(api_key_client, project, cycle, state):
    cycle.manual_status = state
    cycle.save()
    for bucket in ["draft", "current", "completed"]:
        response = api_key_client.get(url(project, public=True), {"cycle_view": bucket})
        assert response.status_code == 200, response.data
        data = response.data if isinstance(response.data, list) else response.data["results"]
        assert (str(cycle.id) in [str(item["id"]) for item in data]) == (bucket == state.lower())


@patch("plane.app.views.cycle.base.model_activity.delay")
def test_manual_status_cannot_be_patched_or_dates_added(_activity, session_client, project, cycle):
    response = session_client.patch(url(project, f"{cycle.id}/"), {"manual_status": "COMPLETED"}, format="json")
    assert response.status_code == 200
    cycle.refresh_from_db()
    assert cycle.manual_status == "DRAFT"
    assert session_client.post(url(project, f"{cycle.id}/start/")).status_code == 200
    response = session_client.patch(
        url(project, f"{cycle.id}/"),
        {
            "start_date": timezone.now().isoformat(),
            "end_date": (timezone.now() + timedelta(days=3)).isoformat(),
        },
        format="json",
    )
    assert response.status_code == 400


def test_scheduled_status_unchanged_and_cannot_start_manually(session_client, project, cycle):
    now = timezone.now()
    for start, end, expected in [(1, 5, "UPCOMING"), (-1, 1, "CURRENT"), (-5, -1, "COMPLETED")]:
        cycle.start_date = now + timedelta(days=start)
        cycle.end_date = now + timedelta(days=end)
        cycle.save()
        assert get_cycle_status(cycle) == expected
        assert Cycle.objects.annotate(status=cycle_status_expression()).get(pk=cycle.pk).status == expected
        assert session_client.post(url(project, f"{cycle.id}/start/")).status_code == 400


def test_undated_analytics(session_client, project, cycle):
    response = session_client.get(url(project, f"{cycle.id}/analytics/"), {"type": "issues"})
    assert response.status_code == 200, response.data
    assert response.data["completion_chart"] == {}


@patch("plane.app.views.cycle.base.model_activity.delay")
@patch("plane.utils.cycle_transfer_issues.issue_activity.delay")
def test_completion_preserves_tasks_and_transfer_moves_only_unfinished(
    _issue_activity, _activity, session_client, project, cycle, create_user
):
    from plane.db.models import CycleIssue, Issue, State

    issues = {}
    for group in ["unstarted", "completed", "cancelled"]:
        state = State.objects.create(name=group, group=group, project=project, workspace=project.workspace)
        issue = Issue.objects.create(name=group, state=state, project=project, workspace=project.workspace)
        CycleIssue.objects.create(cycle=cycle, issue=issue, project=project, workspace=project.workspace)
        issues[group] = issue.id
    assert session_client.post(url(project, f"{cycle.id}/start/")).status_code == 200
    assert session_client.post(url(project, f"{cycle.id}/complete/")).status_code == 200
    assert set(CycleIssue.objects.filter(cycle=cycle).values_list("issue_id", flat=True)) == set(issues.values())
    target = Cycle.objects.create(name="Next", project=project, workspace=project.workspace, owned_by=create_user)
    response = session_client.post(
        url(project, f"{cycle.id}/transfer-issues/"), {"new_cycle_id": str(target.id)}, format="json"
    )
    assert response.status_code == 200, response.data
    assert set(CycleIssue.objects.filter(cycle=target).values_list("issue_id", flat=True)) == {issues["unstarted"]}
    assert set(CycleIssue.objects.filter(cycle=cycle).values_list("issue_id", flat=True)) == {
        issues["completed"],
        issues["cancelled"],
    }


def test_cannot_archive_before_completion_or_edit_after_completion(session_client, project, cycle):
    for state in ["DRAFT", "CURRENT"]:
        cycle.manual_status = state
        cycle.save()
        assert session_client.post(url(project, f"{cycle.id}/archive/")).status_code == 400
    cycle.manual_status = "COMPLETED"
    cycle.save()
    response = session_client.patch(url(project, f"{cycle.id}/"), {"name": "Changed"}, format="json")
    assert response.status_code == 400
