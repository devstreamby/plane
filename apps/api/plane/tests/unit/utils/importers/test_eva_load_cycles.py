# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from datetime import date
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from plane.db.models import Cycle, CycleIssue, Module, Project, State
from plane.utils.importers.eva.load import EvaLoader, release_cycle_dates
from plane.utils.importers.eva.transform import EvaTransformer


@pytest.fixture
def eva_project(create_user, workspace):
    project = Project.objects.create(
        name="Cycles Project",
        identifier="CYC",
        workspace=workspace,
        created_by=create_user,
    )
    State.objects.create(
        name="Todo",
        color="#000000",
        project=project,
        workspace=workspace,
        group="unstarted",
        default=True,
        created_by=create_user,
    )
    return project


def _build_loader(*, importer, workspace, project, actor, config):
    return EvaLoader(
        importer=importer,
        workspace=workspace,
        project=project,
        testcase_project=project,
        actor=actor,
        config=config,
        data={"users": []},
    )


def _run(loader, extracted):
    with (
        patch.object(loader, "_import_description_media", side_effect=lambda html, **kwargs: html),
        patch("plane.utils.importers.eva.load.Importer.objects.filter") as importer_filter,
    ):
        importer_filter.return_value.update = MagicMock()
        loader.run(extracted)


def _make_importer():
    importer = MagicMock()
    importer.pk = uuid4()
    importer.metadata = {"url": "", "token": ""}
    importer.imported_data = None
    return importer


@pytest.mark.unit
@pytest.mark.django_db
def test_default_cycle_source_uses_sprints(create_user, workspace, eva_project):
    loader = _build_loader(
        importer=_make_importer(), workspace=workspace, project=eva_project, actor=create_user, config={}
    )
    extracted = {
        "tasks": [
            {
                "id": "task-1",
                "name": "Task 1",
                "lists": [{"code": "SPR-1", "name": "Sprint 1"}],
                "fix_versions": [{"code": "REL-1", "name": "1.0"}],
            }
        ],
        "cycle_lists": [],
        "testcases": [],
        "comments": [],
        "testcase_comments": [],
        "attachments": [],
        "documents": [],
    }

    _run(loader, extracted)

    assert Cycle.objects.filter(project=eva_project, external_id="SPR-1").exists()
    assert not Cycle.objects.filter(project=eva_project, external_id="REL-1").exists()
    cycle = Cycle.objects.get(project=eva_project, external_id="SPR-1")
    assert CycleIssue.objects.filter(cycle=cycle, issue__external_id="task-1").exists()


@pytest.mark.unit
@pytest.mark.django_db
def test_cycle_source_fix_versions_creates_cycles_from_releases(create_user, workspace, eva_project):
    loader = _build_loader(
        importer=_make_importer(),
        workspace=workspace,
        project=eva_project,
        actor=create_user,
        config={"cycle_source": "fix_versions"},
    )
    extracted = {
        "tasks": [
            {
                "id": "task-1",
                "name": "Task 1",
                "status_closed_at": "2026-01-10",
                "lists": [{"code": "SPR-1", "name": "Sprint 1"}],
                "fix_versions": [{"code": "REL-1", "name": "1.0"}],
            }
        ],
        "cycle_lists": [],
        "testcases": [],
        "comments": [],
        "testcase_comments": [],
        "attachments": [],
        "documents": [],
    }

    _run(loader, extracted)

    assert not Cycle.objects.filter(project=eva_project, external_id="SPR-1").exists()
    cycle = Cycle.objects.get(project=eva_project, external_id="REL-1")
    assert cycle.end_date.date() == date(2026, 1, 10)
    assert CycleIssue.objects.filter(cycle=cycle, issue__external_id="task-1").exists()


@pytest.mark.unit
@pytest.mark.django_db
def test_cycle_source_none_creates_no_cycles(create_user, workspace, eva_project):
    loader = _build_loader(
        importer=_make_importer(),
        workspace=workspace,
        project=eva_project,
        actor=create_user,
        config={"cycle_source": "none"},
    )
    extracted = {
        "tasks": [{"id": "task-1", "name": "Task 1", "lists": [{"code": "SPR-1", "name": "Sprint 1"}]}],
        "cycle_lists": [],
        "testcases": [],
        "comments": [],
        "testcase_comments": [],
        "attachments": [],
        "documents": [],
    }

    _run(loader, extracted)

    assert not Cycle.objects.filter(project=eva_project).exists()


@pytest.mark.unit
@pytest.mark.django_db
def test_module_source_none_creates_no_modules(create_user, workspace, eva_project):
    loader = _build_loader(
        importer=_make_importer(),
        workspace=workspace,
        project=eva_project,
        actor=create_user,
        config={"module_source": "none"},
    )
    extracted = {
        "tasks": [{"id": "task-1", "name": "Task 1", "fix_versions": [{"code": "REL-1", "name": "1.0"}]}],
        "cycle_lists": [],
        "testcases": [],
        "comments": [],
        "testcase_comments": [],
        "attachments": [],
        "documents": [],
    }

    _run(loader, extracted)

    assert not Module.objects.filter(project=eva_project).exists()


@pytest.mark.unit
@pytest.mark.django_db
def test_manual_cycle_name_collision_is_skipped_and_not_linked(create_user, workspace, eva_project):
    manual_cycle = Cycle.objects.create(
        name="29.26",
        project=eva_project,
        workspace=workspace,
        owned_by=create_user,
        created_by=create_user,
    )
    loader = _build_loader(
        importer=_make_importer(),
        workspace=workspace,
        project=eva_project,
        actor=create_user,
        config={"cycle_source": "fix_versions"},
    )
    extracted = {
        "tasks": [
            {
                "id": "task-1",
                "name": "Task 1",
                "status_closed_at": "2026-07-31",
                "fix_versions": [{"code": "REL-145", "name": "29.26"}],
            }
        ],
        "cycle_lists": [],
        "testcases": [],
        "comments": [],
        "testcase_comments": [],
        "attachments": [],
        "documents": [],
    }

    _run(loader, extracted)

    assert not Cycle.objects.filter(project=eva_project, external_id="REL-145").exists()
    assert Cycle.objects.filter(project=eva_project).count() == 1
    assert not CycleIssue.objects.filter(cycle=manual_cycle).exists()
    assert any("REL-145" in warning for warning in loader.warnings)


@pytest.mark.unit
@pytest.mark.django_db
def test_release_cycle_dates_chains_from_median_close_dates():
    transformer = EvaTransformer(base_url="")
    tasks = [
        {"id": "t1", "status_closed_at": "2026-01-05", "fix_versions": [{"code": "REL-1"}]},
        {"id": "t2", "status_closed_at": "2026-01-06", "fix_versions": [{"code": "REL-1"}]},
        {"id": "t3", "status_closed_at": "2026-01-07", "fix_versions": [{"code": "REL-1"}]},
        {"id": "t4", "status_closed_at": "2026-01-20", "fix_versions": [{"code": "REL-2"}]},
        {"id": "t5", "fix_versions": [{"code": "REL-3"}]},
    ]

    dates = release_cycle_dates(tasks, transformer)

    assert dates["REL-1"]["end_date"] == date(2026, 1, 6)
    assert dates["REL-1"]["start_date"] == date(2025, 12, 30)
    assert dates["REL-2"]["end_date"] == date(2026, 1, 20)
    assert dates["REL-2"]["start_date"] == date(2026, 1, 7)
    assert "REL-3" not in dates


@pytest.mark.unit
@pytest.mark.django_db
def test_release_cycle_dates_collapses_when_medians_tie():
    transformer = EvaTransformer(base_url="")
    tasks = [
        {"id": "t1", "status_closed_at": "2026-04-22", "fix_versions": [{"code": "REL-1"}]},
        {"id": "t2", "status_closed_at": "2026-04-22", "fix_versions": [{"code": "REL-2"}]},
    ]

    dates = release_cycle_dates(tasks, transformer)

    assert dates["REL-1"]["end_date"] == date(2026, 4, 22)
    assert dates["REL-2"]["start_date"] == date(2026, 4, 22)
    assert dates["REL-2"]["end_date"] == date(2026, 4, 22)
