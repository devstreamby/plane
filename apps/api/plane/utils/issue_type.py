# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import transaction

from plane.db.models import IssueType, Project, ProjectIssueType


def _work_item_type_icon(name: str, color: str) -> dict:
    return {
        "in_use": "icon",
        "icon": {"name": name, "color": color, "package": "work-item-type"},
    }


# (name, is_default, is_epic, logo_props)
# The custom work item type icons are rendered as fixed-color SVGs. The package
# marker keeps the JSON self-describing for every <Logo> render site.
# Epic is seeded with is_epic=False on purpose: apps/api/plane/app/views/issue/archive.py:99
# excludes is_epic=True issues from the archive view, and this fork treats Epic as an
# ordinary work item type rather than a special entity.
DEFAULT_ISSUE_TYPES = [
    ("Task", True, False, _work_item_type_icon("Task", "#2563EB")),
    ("Story", False, False, _work_item_type_icon("Story", "#059669")),
    ("Subtask", False, False, _work_item_type_icon("Subtask", "#4F46E5")),
    ("Epic", False, False, _work_item_type_icon("Epic", "#7C3AED")),
    ("Bug", False, False, _work_item_type_icon("Bug", "#E11D48")),
    ("Spike", False, False, _work_item_type_icon("Spike", "#F59E0B")),
]


def ensure_default_issue_types(project: Project) -> None:
    """
    Idempotently create the six default work item types for a
    workspace and link them to the given project. Safe to call repeatedly.
    """
    # Both get_or_create calls rely on a unique constraint to stay atomic: this
    # function runs concurrently (project PATCH + type-list fetch), and without a
    # constraint backing the SELECT-then-INSERT both callers insert their own row.
    with transaction.atomic():
        for name, is_default, is_epic, logo_props in DEFAULT_ISSUE_TYPES:
            issue_type, _ = IssueType.objects.get_or_create(
                workspace_id=project.workspace_id,
                name=name,
                defaults={"is_active": True, "is_epic": is_epic, "logo_props": logo_props},
            )

            ProjectIssueType.objects.get_or_create(
                project=project, issue_type=issue_type, defaults={"is_default": is_default}
            )
