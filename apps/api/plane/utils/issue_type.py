# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import transaction

from plane.db.models import IssueType, Project, ProjectIssueType


def _phosphor_icon(name: str, color: str) -> dict:
    return {
        "in_use": "icon",
        "icon": {"name": name, "color": color, "package": "phosphor"},
    }


# (name, is_default, is_epic, logo_props)
# Phosphor icons are rendered as SVGs, so they do not depend on the Material Symbols
# webfont being loaded. The package marker keeps the JSON self-describing for every
# <Logo> render site.
# Epic is seeded with is_epic=False on purpose: apps/api/plane/app/views/issue/archive.py:99
# excludes is_epic=True issues from the archive view, and this fork treats Epic as an
# ordinary work item type rather than a special entity.
DEFAULT_ISSUE_TYPES = [
    ("Task", True, False, _phosphor_icon("CheckSquare", "#5e6ad2")),
    ("Bug", False, False, _phosphor_icon("Bug", "#e5484d")),
    ("Story", False, False, _phosphor_icon("BookOpenText", "#02a594")),
    ("Epic", False, False, _phosphor_icon("Lightning", "#8e4ec6")),
]


def ensure_default_issue_types(project: Project) -> None:
    """
    Idempotently create the default work item types (Task/Bug/Story/Epic) for a
    workspace and link them to the given project. Safe to call repeatedly.
    """
    with transaction.atomic():
        for name, is_default, is_epic, logo_props in DEFAULT_ISSUE_TYPES:
            issue_type, _ = IssueType.objects.get_or_create(
                workspace_id=project.workspace_id,
                name=name,
                defaults={"is_active": True, "is_epic": is_epic, "logo_props": logo_props},
            )

            project_issue_type = ProjectIssueType.objects.filter(
                project=project, issue_type=issue_type, deleted_at__isnull=True
            ).first()
            if project_issue_type is None:
                ProjectIssueType.objects.create(project=project, issue_type=issue_type, is_default=is_default)
