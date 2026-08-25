# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.db import migrations, models
from django.db.models import Count
from django.utils import timezone


def merge_duplicate_issue_types(apps, schema_editor):
    """
    Collapse work item types that share a (workspace, name) pair so the unique
    constraint added below can be applied.

    Duplicates were produced by `ensure_default_issue_types()` racing itself:
    it ran both inside the project PATCH that flips `is_issue_type_enabled` and
    inside the type-list endpoint, and `get_or_create` is not atomic without a
    DB constraint to back it. The surviving row keeps every reference; the
    others are soft-deleted.
    """
    # Historical models carry no custom managers, so `objects` is not guaranteed to
    # exist; `_base_manager` always does and is unfiltered, which suits the explicit
    # deleted_at filters below.
    IssueType = apps.get_model("db", "IssueType")
    ProjectIssueType = apps.get_model("db", "ProjectIssueType")
    Issue = apps.get_model("db", "Issue")
    DraftIssue = apps.get_model("db", "DraftIssue")

    duplicate_keys = (
        IssueType._base_manager.filter(deleted_at__isnull=True)
        .values("workspace_id", "name")
        .annotate(row_count=Count("id"))
        .filter(row_count__gt=1)
    )

    for key in duplicate_keys:
        # Keep the active copy: work items are repointed either way, but a surviving
        # deactivated type cannot be set as a project default. Rows with work items
        # attached, then older rows, win the remaining ties.
        rows = list(
            IssueType._base_manager.filter(workspace_id=key["workspace_id"], name=key["name"], deleted_at__isnull=True)
            .annotate(issue_count=Count("issue_type"))
            .order_by("-is_active", "-issue_count", "created_at", "id")
        )
        canonical, duplicates = rows[0], rows[1:]

        for duplicate in duplicates:
            Issue._base_manager.filter(type_id=duplicate.id).update(type_id=canonical.id)
            DraftIssue._base_manager.filter(type_id=duplicate.id).update(type_id=canonical.id)

            for link in ProjectIssueType._base_manager.filter(issue_type_id=duplicate.id, deleted_at__isnull=True):
                canonical_link = ProjectIssueType._base_manager.filter(
                    project_id=link.project_id, issue_type_id=canonical.id, deleted_at__isnull=True
                ).first()
                if canonical_link is None:
                    link.issue_type_id = canonical.id
                    link.save(update_fields=["issue_type"])
                    continue

                # Repointing would collide with ProjectIssueType's own unique
                # constraint, so drop the redundant link — but not the project's
                # only "default type" marker along with it.
                if link.is_default and not canonical_link.is_default:
                    canonical_link.is_default = True
                    canonical_link.save(update_fields=["is_default"])
                link.deleted_at = timezone.now()
                link.save(update_fields=["deleted_at"])

            duplicate.deleted_at = timezone.now()
            duplicate.save(update_fields=["deleted_at"])


def noop(apps, schema_editor):
    """Merging duplicates is not reversible; dropping the constraint is enough."""


class Migration(migrations.Migration):
    dependencies = [("db", "0128_merge_board_column_gitlab")]

    operations = [
        migrations.RunPython(merge_duplicate_issue_types, noop),
        migrations.AddConstraint(
            model_name="issuetype",
            constraint=models.UniqueConstraint(
                condition=models.Q(("deleted_at__isnull", True)),
                fields=("workspace", "name"),
                name="issue_type_unique_workspace_name_when_deleted_at_null",
            ),
        ),
    ]
