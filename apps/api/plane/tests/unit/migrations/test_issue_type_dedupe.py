# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import importlib

import pytest
from django.apps import apps as django_apps
from django.db import connection
from django.db.models import Count

from plane.db.models import (
    DraftIssue,
    Issue,
    IssueType,
    Project,
    ProjectIssueType,
    ProjectMember,
)

merge_duplicate_issue_types = importlib.import_module(
    "plane.db.migrations.0129_issuetype_unique_workspace_name"
).merge_duplicate_issue_types

UNIQUE_CONSTRAINT = IssueType._meta.constraints[0]


@pytest.fixture
def without_unique_constraint():
    """
    Drop the (workspace, name) unique constraint for the duration of a test.

    Migration 0129 exists to clean up data created *before* that constraint, which
    cannot otherwise be written. Postgres DDL is transactional, so pytest-django's
    per-test rollback puts the constraint back.
    """
    with connection.schema_editor(atomic=False) as editor:
        editor.remove_constraint(IssueType, UNIQUE_CONSTRAINT)
    yield


def assert_constraint_would_hold():
    """
    Assert the merge left data the unique constraint accepts.

    Re-adding the real constraint would be the stronger check, but Postgres refuses
    CREATE INDEX inside a transaction that has pending trigger events, which every
    test here does.
    """
    duplicates = (
        IssueType.objects.values("workspace_id", "name").annotate(row_count=Count("id")).filter(row_count__gt=1)
    )
    assert not list(duplicates)


@pytest.mark.unit
@pytest.mark.django_db
class TestMergeDuplicateIssueTypes:
    """Covers the data step of migration 0129."""

    @pytest.fixture
    def project(self, workspace, create_user):
        project = Project.objects.create(
            name="Dedupe project", identifier="DEDUP", workspace=workspace, is_issue_type_enabled=True
        )
        ProjectMember.objects.create(project=project, member=create_user, role=20)
        return project

    @staticmethod
    def merge():
        merge_duplicate_issue_types(django_apps, None)

    def test_keeps_the_active_row_and_repoints_work_items(
        self, without_unique_constraint, workspace, project, create_user
    ):
        """
        Prod duplicates came as one active + one inactive row, because someone had
        already tried the trash icon on the extra copy.
        """
        kept = IssueType.objects.create(workspace=workspace, name="Bug", is_active=True)
        ProjectIssueType.objects.create(project=project, issue_type=kept, is_default=False)
        dropped = IssueType.objects.create(workspace=workspace, name="Bug", is_active=False)

        issue = Issue.objects.create(
            name="Typed issue", project=project, workspace=workspace, type=dropped, created_by=create_user
        )
        draft = DraftIssue.objects.create(
            name="Typed draft", project=project, workspace=workspace, type=dropped, created_by=create_user
        )

        self.merge()

        assert list(IssueType.objects.filter(workspace=workspace, name="Bug")) == [kept]
        issue.refresh_from_db()
        draft.refresh_from_db()
        assert issue.type_id == kept.id
        assert draft.type_id == kept.id
        assert_constraint_would_hold()

    def test_prefers_the_row_work_items_point_at_when_both_are_active(
        self, without_unique_constraint, workspace, project, create_user
    ):
        unused = IssueType.objects.create(workspace=workspace, name="Story", is_active=True)
        used = IssueType.objects.create(workspace=workspace, name="Story", is_active=True)
        Issue.objects.create(
            name="Typed issue", project=project, workspace=workspace, type=used, created_by=create_user
        )

        self.merge()

        assert list(IssueType.objects.filter(workspace=workspace, name="Story")) == [used]
        assert not IssueType.objects.filter(pk=unused.pk).exists()
        assert_constraint_would_hold()

    def test_drops_the_redundant_project_link(self, without_unique_constraint, workspace, project):
        """Repointing a link the survivor already has would break ProjectIssueType's own constraint."""
        kept = IssueType.objects.create(workspace=workspace, name="Spike")
        ProjectIssueType.objects.create(project=project, issue_type=kept, is_default=False)
        dropped = IssueType.objects.create(workspace=workspace, name="Spike")
        ProjectIssueType.objects.create(project=project, issue_type=dropped, is_default=False)

        self.merge()

        links = ProjectIssueType.objects.filter(project=project)
        assert [link.issue_type_id for link in links] == [kept.id]
        assert_constraint_would_hold()

    def test_keeps_the_project_default_when_dropping_its_link(self, without_unique_constraint, workspace, project):
        """The project must not be left without a default type."""
        kept = IssueType.objects.create(workspace=workspace, name="Task", is_active=True)
        ProjectIssueType.objects.create(project=project, issue_type=kept, is_default=False)
        dropped = IssueType.objects.create(workspace=workspace, name="Task", is_active=False)
        ProjectIssueType.objects.create(project=project, issue_type=dropped, is_default=True)

        self.merge()

        link = ProjectIssueType.objects.get(project=project)
        assert link.issue_type_id == kept.id
        assert link.is_default is True
        assert_constraint_would_hold()

    def test_moves_a_link_the_survivor_does_not_have(
        self, without_unique_constraint, workspace, project, create_user
    ):
        other_project = Project.objects.create(
            name="Dedupe project 2", identifier="DEDUP2", workspace=workspace, is_issue_type_enabled=True
        )
        ProjectMember.objects.create(project=other_project, member=create_user, role=20)

        kept = IssueType.objects.create(workspace=workspace, name="Epic")
        ProjectIssueType.objects.create(project=project, issue_type=kept, is_default=False)
        dropped = IssueType.objects.create(workspace=workspace, name="Epic")
        ProjectIssueType.objects.create(project=other_project, issue_type=dropped, is_default=False)

        self.merge()

        assert ProjectIssueType.objects.get(project=other_project).issue_type_id == kept.id
        assert_constraint_would_hold()

    def test_collapses_three_way_duplicates(self, without_unique_constraint, workspace):
        for _ in range(3):
            IssueType.objects.create(workspace=workspace, name="Subtask")

        self.merge()

        assert IssueType.objects.filter(workspace=workspace, name="Subtask").count() == 1
        assert_constraint_would_hold()

    def test_leaves_clean_data_alone(self, without_unique_constraint, workspace, project):
        task = IssueType.objects.create(workspace=workspace, name="Task")
        bug = IssueType.objects.create(workspace=workspace, name="Bug")
        ProjectIssueType.objects.create(project=project, issue_type=task, is_default=True)
        ProjectIssueType.objects.create(project=project, issue_type=bug, is_default=False)

        self.merge()

        assert IssueType.objects.filter(workspace=workspace).count() == 2
        assert ProjectIssueType.objects.filter(project=project).count() == 2
        assert_constraint_would_hold()
