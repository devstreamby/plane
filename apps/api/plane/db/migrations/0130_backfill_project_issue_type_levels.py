# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.db import migrations

# The order `ensure_default_issue_types()` seeds the defaults in. Kept as a literal
# so a later edit to that list cannot retroactively change this migration.
DEFAULT_ORDER = ["Task", "Story", "Subtask", "Epic", "Bug", "Spike"]


def backfill_levels(apps, schema_editor):
    """
    Give every project's work item type links a distinct level.

    `ensure_default_issue_types()` used to leave `level` at its default of 0 for all
    six seeded types, so ordering and grouping by work item type had no meaningful
    order to follow. Projects where a level was already set are left untouched.
    """
    # Historical models carry no custom managers, so `objects` is not guaranteed to
    # exist; `_base_manager` always does and is unfiltered.
    ProjectIssueType = apps.get_model("db", "ProjectIssueType")

    project_ids = (
        ProjectIssueType._base_manager.filter(deleted_at__isnull=True).values_list("project_id", flat=True).distinct()
    )

    for project_id in project_ids:
        links = list(
            ProjectIssueType._base_manager.filter(project_id=project_id, deleted_at__isnull=True).select_related(
                "issue_type"
            )
        )
        # Renumber only when levels are actually degenerate. More than one link
        # sitting at level 0 means nothing ever ordered them -- which is the state
        # the old seeder left every project in. A project whose links already have
        # distinct levels is left exactly as it is.
        if sum(1 for link in links if link.level == 0) <= 1:
            continue

        def sort_key(link):
            name = link.issue_type.name
            if name in DEFAULT_ORDER:
                return (0, DEFAULT_ORDER.index(name), link.created_at, str(link.id))
            # Custom types keep their creation order, after the defaults.
            return (1, 0, link.created_at, str(link.id))

        for level, link in enumerate(sorted(links, key=sort_key)):
            link.level = level
            link.save(update_fields=["level"])


def noop(apps, schema_editor):
    """Levels carry no information worth restoring; leave them as backfilled."""


class Migration(migrations.Migration):
    dependencies = [("db", "0129_issuetype_unique_workspace_name")]

    operations = [migrations.RunPython(backfill_levels, noop)]
