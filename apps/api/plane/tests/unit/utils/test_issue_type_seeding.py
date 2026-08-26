# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest
from django.db import IntegrityError, transaction

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
    def test_creates_six_default_types(self, workspace, project):
        ensure_default_issue_types(project)

        names = set(IssueType.objects.filter(workspace=workspace).values_list("name", flat=True))
        assert names == {"Task", "Bug", "Story", "Subtask", "Epic", "Spike"}
        assert ProjectIssueType.objects.filter(project=project).count() == 6

        for issue_type in IssueType.objects.filter(workspace=workspace):
            assert issue_type.logo_props["icon"]["name"] == issue_type.name
            assert issue_type.logo_props["icon"]["package"] == "work-item-type"

    @pytest.mark.django_db
    def test_levels_follow_the_seed_order(self, project):
        """Group-by columns and order-by both read this level, so it must be distinct."""
        ensure_default_issue_types(project)

        ordered = (
            ProjectIssueType.objects.filter(project=project).order_by("level").values_list("issue_type__name", "level")
        )
        assert list(ordered) == [
            ("Task", 0),
            ("Story", 1),
            ("Subtask", 2),
            ("Epic", 3),
            ("Bug", 4),
            ("Spike", 5),
        ]

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

        assert IssueType.objects.filter(workspace=workspace).count() == 6
        assert ProjectIssueType.objects.filter(project=project).count() == 6

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

    @pytest.mark.django_db
    def test_workspace_name_pair_is_unique(self, workspace, project):
        """The constraint is what makes get_or_create above atomic under a race."""
        ensure_default_issue_types(project)

        with pytest.raises(IntegrityError), transaction.atomic():
            IssueType.objects.create(workspace=workspace, name="Task")

    @pytest.mark.django_db
    def test_soft_deleted_name_can_be_reused(self, workspace, project):
        ensure_default_issue_types(project)

        bug = IssueType.objects.get(workspace=workspace, name="Bug")
        IssueType.objects.filter(pk=bug.pk).update(deleted_at="2026-08-19T08:05:32Z")

        # The constraint is scoped to live rows, so the freed name is available again.
        recreated = IssueType.objects.create(workspace=workspace, name="Bug")
        assert recreated.pk != bug.pk

    @pytest.mark.django_db
    def test_relinks_a_type_the_project_had_unlinked(self, workspace, project):
        """Re-enabling the feature must reuse the existing workspace type row."""
        ensure_default_issue_types(project)
        bug = IssueType.objects.get(workspace=workspace, name="Bug")
        ProjectIssueType.objects.filter(project=project, issue_type=bug).delete()

        ensure_default_issue_types(project)

        assert IssueType.objects.filter(workspace=workspace, name="Bug").count() == 1
        assert ProjectIssueType.objects.filter(project=project, issue_type=bug).exists()
