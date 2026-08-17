# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest

from plane.db.models import IssueType, Project, ProjectIssueType, ProjectMember
from plane.utils.issue_type import ensure_default_issue_types


@pytest.mark.unit
class TestEnsureDefaultIssueTypes:
    @pytest.fixture
    def project(self, workspace, create_user):
        project = Project.objects.create(
            name="Seed project", identifier="SEED", workspace=workspace, is_issue_type_enabled=True
        )
        ProjectMember.objects.create(project=project, member=create_user, role=20)
        return project

    @pytest.mark.django_db
    def test_creates_four_default_types(self, workspace, project):
        ensure_default_issue_types(project)

        names = set(IssueType.objects.filter(workspace=workspace).values_list("name", flat=True))
        assert names == {"Task", "Bug", "Story", "Epic"}
        assert ProjectIssueType.objects.filter(project=project).count() == 4

    @pytest.mark.django_db
    def test_exactly_one_default(self, project):
        ensure_default_issue_types(project)

        defaults = ProjectIssueType.objects.filter(project=project, is_default=True)
        assert defaults.count() == 1
        assert defaults.first().issue_type.name == "Task"

    @pytest.mark.django_db
    def test_epic_is_seeded_with_is_epic_false(self, workspace, project):
        ensure_default_issue_types(project)

        epic = IssueType.objects.get(workspace=workspace, name="Epic")
        assert epic.is_epic is False

    @pytest.mark.django_db
    def test_idempotent_on_repeated_calls(self, workspace, project):
        ensure_default_issue_types(project)
        ensure_default_issue_types(project)
        ensure_default_issue_types(project)

        assert IssueType.objects.filter(workspace=workspace).count() == 4
        assert ProjectIssueType.objects.filter(project=project).count() == 4

    @pytest.mark.django_db
    def test_reuses_workspace_type_across_projects(self, workspace, project, create_user):
        other_project = Project.objects.create(
            name="Seed project 2", identifier="SEED2", workspace=workspace, is_issue_type_enabled=True
        )
        ProjectMember.objects.create(project=other_project, member=create_user, role=20)

        ensure_default_issue_types(project)
        ensure_default_issue_types(other_project)

        # Same workspace-level IssueType rows are linked to both projects, not duplicated.
        assert IssueType.objects.filter(workspace=workspace, name="Task").count() == 1
        assert ProjectIssueType.objects.filter(issue_type__name="Task").count() == 2
