# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

# Module imports
from plane.db.models import Issue, IssueType, Project
from plane.utils.issue_type import ensure_default_issue_types


class Command(BaseCommand):
    help = (
        "Seed the default work item types (Task/Bug/Story/Epic) for a project that already has "
        "is_issue_type_enabled=True. Optionally backfill the Bug type onto existing untyped work "
        "items that carry a 'Bug' label or have 'Bug' in their name. Idempotent: only touches "
        "issues with type_id IS NULL, so re-running is always safe."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--project",
            required=True,
            help="Project id (uuid) to seed. Must have is_issue_type_enabled=True.",
        )
        parser.add_argument(
            "--backfill-bugs",
            action="store_true",
            help="Also assign the Bug type to untyped issues matching the Bug label/name rule.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=True,
            help="Report what would change without saving anything (default: on).",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Actually perform the writes. Without this flag the command only reports.",
        )

    def handle(self, *args, **options):
        project = Project.objects.filter(pk=options["project"]).first()
        if project is None:
            raise CommandError(f"Project {options['project']} not found")
        if not project.is_issue_type_enabled:
            raise CommandError(f"Project {project.name} does not have is_issue_type_enabled=True")

        apply_changes = options["apply"]
        dry_run = not apply_changes

        if dry_run:
            ensure_default_issue_types(project)
            self.stdout.write(self.style.WARNING("Seeded default types (this step always applies, it is idempotent)."))
        else:
            ensure_default_issue_types(project)
            self.stdout.write(self.style.SUCCESS(f"Ensured default work item types for {project.name}"))

        if not options["backfill_bugs"]:
            return

        bug_type = IssueType.objects.filter(workspace_id=project.workspace_id, name="Bug").first()
        if bug_type is None:
            raise CommandError("Bug type was not found after seeding — this should not happen")

        candidates = (
            Issue.issue_objects.filter(project_id=project.id, type_id__isnull=True)
            .filter(Q(name__icontains="bug") | Q(labels__name__iexact="bug"))
            .distinct()
        )

        count = candidates.count()
        self.stdout.write(f"{count} untyped issue(s) match the Bug rule (label 'Bug' or 'Bug' in name).")
        for issue in candidates[:10]:
            self.stdout.write(f"  - {issue.name}")
        if count > 10:
            self.stdout.write(f"  ... and {count - 10} more")

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run — nothing written. Re-run with --apply to backfill."))
            return

        updated = candidates.update(type_id=bug_type.id)
        self.stdout.write(self.style.SUCCESS(f"Assigned Bug type to {updated} issue(s)."))
