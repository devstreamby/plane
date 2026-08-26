# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import importlib

import pytest
from django.apps import apps as django_apps

from plane.db.models import IssueType, Project, ProjectIssueType, ProjectMember

backfill_levels = importlib.import_module("plane.db.migrations.0130_backfill_project_issue_type_levels").backfill_levels


@pytest.mark.unit
@pytest.mark.django_db
class TestBackfillProjectIssueTypeLevels:
    """Covers the data step of migration 0130."""

    @pytest.fixture
    def project(self, workspace, create_user):
        project = Project.objects.create(
            name="Level project", identifier="LVL", workspace=workspace, is_issue_type_enabled=True
        )
        ProjectMember.objects.create(project=project, member=create_user, role=20)
        return project

    @staticmethod
    def link(project, workspace, name, level=0):
        issue_type = IssueType.objects.create(workspace=workspace, name=name)
        return ProjectIssueType.objects.create(project=project, issue_type=issue_type, level=level)

    @staticmethod
    def levels(project):
        return list(
            ProjectIssueType.objects.filter(project=project).order_by("level").values_list("issue_type__name", "level")
        )

    @staticmethod
    def backfill():
        backfill_levels(django_apps, None)

    def test_assigns_the_seed_order_to_all_zero_levels(self, workspace, project):
        for name in ["Bug", "Task", "Spike", "Story", "Epic", "Subtask"]:
            self.link(project, workspace, name)

        self.backfill()

        assert self.levels(project) == [
            ("Task", 0),
            ("Story", 1),
            ("Subtask", 2),
            ("Epic", 3),
            ("Bug", 4),
            ("Spike", 5),
        ]

    def test_puts_custom_types_after_the_defaults(self, workspace, project):
        for name in ["Bug", "Task", "Chore"]:
            self.link(project, workspace, name)

        self.backfill()

        assert self.levels(project) == [("Task", 0), ("Bug", 1), ("Chore", 2)]

    def test_leaves_a_project_with_distinct_levels_alone(self, workspace, project):
        self.link(project, workspace, "Bug", level=0)
        self.link(project, workspace, "Task", level=7)

        self.backfill()

        assert self.levels(project) == [("Bug", 0), ("Task", 7)]

    def test_renumbers_when_only_some_links_have_a_level(self, workspace, project):
        """
        A single stray level must not shield the tied ones.

        Creating a custom type assigns it a level, so a real project can end up with
        its six seeded types tied at 0 and one custom type above them.
        """
        for name in ["Task", "Bug", "Story"]:
            self.link(project, workspace, name)
        self.link(project, workspace, "Chore", level=3)

        self.backfill()

        assert self.levels(project) == [("Task", 0), ("Story", 1), ("Bug", 2), ("Chore", 3)]

    def test_ignores_soft_deleted_links(self, workspace, project):
        self.link(project, workspace, "Task")
        dropped = self.link(project, workspace, "Bug")
        ProjectIssueType.objects.filter(pk=dropped.pk).delete()

        self.backfill()

        assert self.levels(project) == [("Task", 0)]

    def test_scopes_levels_per_project(self, workspace, project, create_user):
        other = Project.objects.create(
            name="Level project 2", identifier="LVL2", workspace=workspace, is_issue_type_enabled=True
        )
        ProjectMember.objects.create(project=other, member=create_user, role=20)
        task = IssueType.objects.create(workspace=workspace, name="Task")
        bug = IssueType.objects.create(workspace=workspace, name="Bug")
        for target in (project, other):
            ProjectIssueType.objects.create(project=target, issue_type=task, level=0)
            ProjectIssueType.objects.create(project=target, issue_type=bug, level=0)

        self.backfill()

        assert self.levels(project) == [("Task", 0), ("Bug", 1)]
        assert self.levels(other) == [("Task", 0), ("Bug", 1)]
