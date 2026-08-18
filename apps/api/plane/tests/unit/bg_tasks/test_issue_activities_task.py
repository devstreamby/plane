# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import uuid

import pytest

from plane.bgtasks.issue_activities_task import track_issue_type
from plane.db.models import IssueType, Project, ProjectMember


@pytest.mark.unit
class TestTrackIssueType:
    @pytest.fixture
    def project(self, workspace, create_user):
        project = Project.objects.create(name="Typed project", identifier="TRK", workspace=workspace)
        ProjectMember.objects.create(project=project, member=create_user, role=20)
        return project

    @pytest.fixture
    def types(self, workspace):
        task_type = IssueType.objects.create(workspace=workspace, name="Task", is_active=True)
        bug_type = IssueType.objects.create(workspace=workspace, name="Bug", is_active=True)
        return task_type, bug_type

    @staticmethod
    def _track(current_type_id, requested_type_id, project_id, workspace_id):
        issue_activities = []
        track_issue_type(
            requested_data={"type_id": requested_type_id},
            current_instance={"type_id": current_type_id},
            issue_id=str(uuid.uuid4()),
            project_id=project_id,
            workspace_id=workspace_id,
            actor_id=str(uuid.uuid4()),
            issue_activities=issue_activities,
            epoch=0,
        )
        return issue_activities

    @pytest.mark.django_db
    def test_records_activity_on_type_change(self, workspace, project, types):
        task_type, bug_type = types

        activities = self._track(str(task_type.id), str(bug_type.id), project.id, workspace.id)

        assert len(activities) == 1
        activity = activities[0]
        assert activity.field == "type"
        assert activity.verb == "updated"
        assert activity.old_value == "Task"
        assert activity.new_value == "Bug"
        assert activity.old_identifier == task_type.id
        assert activity.new_identifier == bug_type.id

    @pytest.mark.django_db
    def test_records_activity_when_type_set_from_none(self, workspace, project, types):
        _task_type, bug_type = types

        activities = self._track(None, str(bug_type.id), project.id, workspace.id)

        assert len(activities) == 1
        activity = activities[0]
        assert activity.old_value is None
        assert activity.new_value == "Bug"
        assert activity.old_identifier is None
        assert activity.new_identifier == bug_type.id

    @pytest.mark.django_db
    def test_no_activity_when_type_unchanged(self, workspace, project, types):
        task_type, _bug_type = types

        activities = self._track(str(task_type.id), str(task_type.id), project.id, workspace.id)

        assert activities == []

    @pytest.mark.django_db
    def test_no_activity_when_both_absent(self, workspace, project):
        activities = self._track(None, None, project.id, workspace.id)

        assert activities == []
