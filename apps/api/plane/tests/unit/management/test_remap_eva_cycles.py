# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import json
from unittest.mock import patch

import pytest
from django.core.management import call_command

from plane.db.models import APIToken, Cycle, CycleIssue, Importer, Issue, Module, ModuleIssue, Project


@pytest.fixture
def remap_fixture(create_user, workspace, tmp_path):
    project = Project.objects.create(
        name="Remap Project",
        identifier="RMP",
        workspace=workspace,
        created_by=create_user,
    )

    manual_cycle = Cycle.objects.create(
        name="29.26",
        project=project,
        workspace=workspace,
        owned_by=create_user,
        created_by=create_user,
    )

    sprint_cycle = Cycle.objects.create(
        name="Sprint 1",
        project=project,
        workspace=workspace,
        owned_by=create_user,
        created_by=create_user,
        external_source="eva",
        external_id="SPR-1",
    )

    release_module = Module.objects.create(
        name="10.26",
        project=project,
        workspace=workspace,
        created_by=create_user,
        external_source="eva",
        external_id="REL-10",
    )

    issue_a = Issue.objects.create(
        name="Task A",
        project=project,
        workspace=workspace,
        created_by=create_user,
        external_source="eva",
        external_id="CmfTask:a",
    )
    issue_b = Issue.objects.create(
        name="Task B",
        project=project,
        workspace=workspace,
        created_by=create_user,
        external_source="eva",
        external_id="CmfTask:b",
    )
    issue_c = Issue.objects.create(
        name="Task C (goes to the 29.26 release, but collides with a manual cycle)",
        project=project,
        workspace=workspace,
        created_by=create_user,
        external_source="eva",
        external_id="CmfTask:c",
    )

    sprint_cycle_issue = CycleIssue.objects.create(
        cycle=sprint_cycle, issue=issue_a, project=project, workspace=workspace, created_by=create_user
    )
    ModuleIssue.objects.create(
        module=release_module, issue=issue_a, project=project, workspace=workspace, created_by=create_user
    )

    token = APIToken.objects.create(user=create_user, workspace=workspace)
    Importer.objects.create(
        project=project,
        workspace=workspace,
        service="eva",
        status="completed",
        initiated_by=create_user,
        created_by=create_user,
        metadata={"url": "https://eva.example.com", "token": "secret", "eva_project_id": "CmfProject:1"},
        token=token,
    )

    eva_tasks = [
        {
            "id": "CmfTask:a",
            "status_closed_at": "2026-02-01",
            "fix_versions": [{"code": "REL-20", "name": "20.26"}],
        },
        {
            "id": "CmfTask:b",
            "status_closed_at": "2026-02-03",
            "fix_versions": [{"code": "REL-20", "name": "20.26"}],
        },
        {
            "id": "CmfTask:c",
            "status_closed_at": "2026-02-10",
            "fix_versions": [{"code": "REL-30", "name": "29.26"}],
        },
    ]

    return {
        "project": project,
        "manual_cycle": manual_cycle,
        "sprint_cycle": sprint_cycle,
        "sprint_cycle_issue": sprint_cycle_issue,
        "release_module": release_module,
        "issue_a": issue_a,
        "issue_b": issue_b,
        "issue_c": issue_c,
        "eva_tasks": eva_tasks,
        "backup_path": str(tmp_path / "backup.json"),
    }


@pytest.mark.unit
@pytest.mark.django_db
def test_remap_creates_release_cycles_and_skips_manual_collision(remap_fixture):
    fx = remap_fixture

    with patch("plane.utils.importers.eva.extract.EvaExtractor.list_tasks", return_value=fx["eva_tasks"]):
        call_command(
            "remap_eva_cycles",
            project=str(fx["project"].id),
            backup=fx["backup_path"],
            drop_modules=True,
        )

    # Sprint cycle is soft-deleted, its issue link too.
    assert not Cycle.objects.filter(id=fx["sprint_cycle"].id).exists()
    assert Cycle.all_objects.get(id=fx["sprint_cycle"].id).deleted_at is not None
    assert not CycleIssue.objects.filter(id=fx["sprint_cycle_issue"].id).exists()

    # Release module is soft-deleted (--drop-modules).
    assert not Module.objects.filter(id=fx["release_module"].id).exists()

    # New cycle created from REL-20, linked to both its tasks.
    new_cycle = Cycle.objects.get(project=fx["project"], external_id="REL-20")
    assert {ci.issue_id for ci in CycleIssue.objects.filter(cycle=new_cycle)} == {
        fx["issue_a"].id,
        fx["issue_b"].id,
    }

    # REL-30 collides by name with the manual "29.26" cycle: skipped entirely.
    assert not Cycle.objects.filter(project=fx["project"], external_id="REL-30").exists()
    assert not CycleIssue.objects.filter(cycle=fx["manual_cycle"]).exists()

    # The manual cycle itself is untouched.
    fx["manual_cycle"].refresh_from_db()
    assert fx["manual_cycle"].deleted_at is None


@pytest.mark.unit
@pytest.mark.django_db
def test_remap_rollback_restores_original_state(remap_fixture):
    fx = remap_fixture

    with patch("plane.utils.importers.eva.extract.EvaExtractor.list_tasks", return_value=fx["eva_tasks"]):
        call_command(
            "remap_eva_cycles",
            project=str(fx["project"].id),
            backup=fx["backup_path"],
            drop_modules=True,
        )

    with open(fx["backup_path"]) as backup_file:
        manifest = json.load(backup_file)
    assert manifest["actions"]["created_cycle_ids"]

    call_command("remap_eva_cycles", project=str(fx["project"].id), rollback=fx["backup_path"])

    # The release cycle created by the remap is gone again.
    assert not Cycle.objects.filter(project=fx["project"], external_id="REL-20").exists()

    # The sprint cycle and its issue link are back.
    fx["sprint_cycle"].refresh_from_db()
    assert fx["sprint_cycle"].deleted_at is None
    fx["sprint_cycle_issue"].refresh_from_db()
    assert fx["sprint_cycle_issue"].deleted_at is None

    # The release module is back.
    fx["release_module"].refresh_from_db()
    assert fx["release_module"].deleted_at is None

    # The manual cycle was never touched by either step.
    fx["manual_cycle"].refresh_from_db()
    assert fx["manual_cycle"].deleted_at is None


@pytest.mark.unit
@pytest.mark.django_db
def test_remap_dry_run_makes_no_changes(remap_fixture):
    fx = remap_fixture

    with patch("plane.utils.importers.eva.extract.EvaExtractor.list_tasks", return_value=fx["eva_tasks"]):
        call_command("remap_eva_cycles", project=str(fx["project"].id), dry_run=True)

    assert Cycle.objects.filter(id=fx["sprint_cycle"].id).exists()
    assert not Cycle.objects.filter(project=fx["project"], external_id="REL-20").exists()
    assert Module.objects.filter(id=fx["release_module"].id).exists()
