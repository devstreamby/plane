# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from plane.db.models import Cycle, CycleIssue, Importer, Issue, Module, ModuleIssue, Project, UserFavorite
from plane.utils.importers.eva.client import EvaApiClient
from plane.utils.importers.eva.constants import EVA_EXTERNAL_SOURCE
from plane.utils.importers.eva.extract import EvaExtractor
from plane.utils.importers.eva.load import release_cycle_dates
from plane.utils.importers.eva.transform import EvaTransformer


def _json_default(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


class Command(BaseCommand):
    help = (
        "One-off remap of a project's EVA-imported cycles from sprints (SPR-*) to releases "
        "(REL-*). Cycles/modules that were created manually (external_source is null) are "
        "never touched. Writes a JSON backup manifest before making any change; that manifest "
        "can be replayed with --rollback to undo the remap."
    )

    def add_arguments(self, parser):
        parser.add_argument("--project", required=True, help="Plane project UUID")
        parser.add_argument("--backup", help="Path to write the JSON backup manifest before mutating anything")
        parser.add_argument(
            "--drop-modules",
            action="store_true",
            help="Also soft-delete EVA release modules (external_id starting with REL-) after cycles are created",
        )
        parser.add_argument("--dry-run", action="store_true", help="Print the plan; make no changes")
        parser.add_argument("--rollback", help="Path to a backup manifest written by a previous run; undoes it")

    def handle(self, *args, **options):
        try:
            project = Project.objects.get(pk=options["project"])
        except Project.DoesNotExist as error:
            raise CommandError(f"No project with id {options['project']}") from error

        if options["rollback"]:
            self._rollback(project, options["rollback"])
            return

        dry_run = options["dry_run"]
        if not dry_run and not options["backup"]:
            raise CommandError("--backup is required unless --dry-run is set")

        importer = (
            Importer.objects.filter(project=project, service="eva", status="completed")
            .order_by("-created_at")
            .select_related("initiated_by")
            .first()
        )
        if not importer:
            raise CommandError(f"No completed EVA importer found for project '{project.name}'")

        metadata = importer.metadata or {}
        url, token, eva_project_id = metadata.get("url"), metadata.get("token"), metadata.get("eva_project_id")
        if not url or not token or not eva_project_id:
            raise CommandError(f"Importer {importer.id} metadata is missing url/token/eva_project_id")

        client = EvaApiClient(url, token)
        extractor = EvaExtractor(client)
        transformer = EvaTransformer(base_url=url)

        self.stdout.write(f"Fetching tasks for EVA project {eva_project_id}...")
        tasks = extractor.list_tasks(eva_project_id)
        dates_by_code = release_cycle_dates(tasks, transformer)

        releases: dict[str, dict[str, Any]] = {}
        for task in tasks:
            external_id = task.get("id")
            if not external_id:
                continue
            for item in task.get("fix_versions") or []:
                code = item.get("code")
                if not code:
                    continue
                bucket = releases.setdefault(code, {"name": item.get("name") or code, "task_external_ids": []})
                bucket["task_external_ids"].append(external_id)

        manual_cycle_names = set(
            Cycle.objects.filter(project=project, external_source__isnull=True, deleted_at__isnull=True).values_list(
                "name", flat=True
            )
        )

        old_cycles = Cycle.objects.filter(
            project=project,
            external_source=EVA_EXTERNAL_SOURCE,
            external_id__startswith="SPR-",
            deleted_at__isnull=True,
        )
        old_modules = Module.objects.filter(
            project=project,
            external_source=EVA_EXTERNAL_SOURCE,
            external_id__startswith="REL-",
            deleted_at__isnull=True,
        )

        self._print_plan(
            project=project,
            releases=releases,
            dates_by_code=dates_by_code,
            manual_cycle_names=manual_cycle_names,
            old_cycles=old_cycles,
            old_modules=old_modules if options["drop_modules"] else None,
        )

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run: no changes made."))
            return

        manifest = self._build_manifest(project)

        with transaction.atomic():
            removed_cycle_issue_ids = list(
                CycleIssue.objects.filter(cycle__in=old_cycles, deleted_at__isnull=True).values_list("id", flat=True)
            )
            CycleIssue.objects.filter(id__in=removed_cycle_issue_ids).delete()
            removed_cycle_ids = list(old_cycles.values_list("id", flat=True))
            Cycle.objects.filter(id__in=removed_cycle_ids).delete()

            removed_module_ids: list[Any] = []
            removed_module_issue_ids: list[Any] = []
            if options["drop_modules"]:
                removed_module_issue_ids = list(
                    ModuleIssue.objects.filter(module__in=old_modules, deleted_at__isnull=True).values_list(
                        "id", flat=True
                    )
                )
                ModuleIssue.objects.filter(id__in=removed_module_issue_ids).delete()
                removed_module_ids = list(old_modules.values_list("id", flat=True))
                Module.objects.filter(id__in=removed_module_ids).delete()

            created_cycle_ids, created_cycle_issue_ids = self._create_release_cycles(
                project=project,
                actor=importer.initiated_by,
                releases=releases,
                dates_by_code=dates_by_code,
                manual_cycle_names=manual_cycle_names,
            )

            manifest["actions"] = {
                "soft_deleted_cycle_ids": [str(i) for i in removed_cycle_ids],
                "soft_deleted_cycle_issue_ids": [str(i) for i in removed_cycle_issue_ids],
                "soft_deleted_module_ids": [str(i) for i in removed_module_ids],
                "soft_deleted_module_issue_ids": [str(i) for i in removed_module_issue_ids],
                "created_cycle_ids": created_cycle_ids,
                "created_cycle_issue_ids": created_cycle_issue_ids,
            }

        with open(options["backup"], "w") as backup_file:
            json.dump(manifest, backup_file, indent=2, default=_json_default)
        self.stdout.write(self.style.SUCCESS(f"Backup manifest written to {options['backup']}"))
        self.stdout.write(
            self.style.SUCCESS(
                f"Removed {len(removed_cycle_ids)} sprint cycles, created {len(created_cycle_ids)} release cycles "
                f"({len(created_cycle_issue_ids)} issue links)"
                + (f", removed {len(removed_module_ids)} release modules" if options["drop_modules"] else "")
            )
        )

    def _print_plan(self, *, project, releases, dates_by_code, manual_cycle_names, old_cycles, old_modules):
        self.stdout.write(f"Project: {project.name} ({project.id})")
        self.stdout.write(f"Releases found in EVA: {len(releases)}")

        to_create = []
        skipped = []
        for code, bucket in releases.items():
            if bucket["name"] in manual_cycle_names:
                skipped.append((code, bucket["name"]))
            else:
                to_create.append((code, bucket))

        if skipped:
            self.stdout.write(f"Skipped (name collides with a manually created cycle): {len(skipped)}")
            for code, name in skipped:
                self.stdout.write(f"  - {code} '{name}'")

        self.stdout.write(f"Cycles to create/reconcile: {len(to_create)}")

        def sort_key(entry):
            code, _bucket = entry
            dates = dates_by_code.get(code) or {}
            return dates.get("end_date") or date.max

        for code, bucket in sorted(to_create, key=sort_key):
            dates = dates_by_code.get(code) or {}
            self.stdout.write(
                f"  - {code} '{bucket['name']}': start={dates.get('start_date')} end={dates.get('end_date')} "
                f"tasks={len(bucket['task_external_ids'])}"
            )

        self.stdout.write(f"Sprint cycles to remove: {old_cycles.count()}")
        for cycle in old_cycles:
            issue_count = CycleIssue.objects.filter(cycle=cycle, deleted_at__isnull=True).count()
            self.stdout.write(f"  - {cycle.external_id} '{cycle.name}' ({issue_count} issues)")

        if old_modules is not None:
            self.stdout.write(f"Release modules to remove: {old_modules.count()}")
            for module in old_modules:
                self.stdout.write(f"  - {module.external_id} '{module.name}'")

    def _create_release_cycles(self, *, project, actor, releases, dates_by_code, manual_cycle_names):
        created_cycle_ids: list[str] = []
        created_cycle_issue_ids: list[str] = []
        issue_by_external_id = {
            issue.external_id: issue
            for issue in Issue.objects.filter(
                project=project, external_source=EVA_EXTERNAL_SOURCE, deleted_at__isnull=True
            )
        }

        for code, bucket in releases.items():
            if bucket["name"] in manual_cycle_names:
                continue
            cycle = Cycle.objects.filter(
                project=project, external_source=EVA_EXTERNAL_SOURCE, external_id=code, deleted_at__isnull=True
            ).first()
            if not cycle:
                cycle = Cycle.objects.create(
                    name=bucket["name"],
                    project=project,
                    workspace=project.workspace,
                    owned_by=actor,
                    created_by=actor,
                    external_source=EVA_EXTERNAL_SOURCE,
                    external_id=code,
                    **(dates_by_code.get(code) or {}),
                )
                created_cycle_ids.append(str(cycle.id))
            for external_id in bucket["task_external_ids"]:
                issue = issue_by_external_id.get(external_id)
                if not issue:
                    continue
                cycle_issue, created = CycleIssue.objects.get_or_create(
                    issue=issue,
                    cycle=cycle,
                    project=project,
                    workspace=project.workspace,
                    defaults={"created_by": actor},
                )
                if created:
                    created_cycle_issue_ids.append(str(cycle_issue.id))
        return created_cycle_ids, created_cycle_issue_ids

    def _build_manifest(self, project: Project) -> dict[str, Any]:
        cycles = list(Cycle.objects.filter(project=project, deleted_at__isnull=True))
        cycle_ids = [cycle.id for cycle in cycles]
        modules = list(Module.objects.filter(project=project, deleted_at__isnull=True))
        module_ids = [module.id for module in modules]

        return {
            "project_id": str(project.id),
            "cycles": [
                {
                    "id": str(c.id),
                    "name": c.name,
                    "external_source": c.external_source,
                    "external_id": c.external_id,
                    "start_date": c.start_date,
                    "end_date": c.end_date,
                }
                for c in cycles
            ],
            "cycle_issues": [
                {"id": str(ci.id), "cycle_id": str(ci.cycle_id), "issue_id": str(ci.issue_id)}
                for ci in CycleIssue.objects.filter(cycle_id__in=cycle_ids, deleted_at__isnull=True)
            ],
            "modules": [
                {
                    "id": str(m.id),
                    "name": m.name,
                    "external_source": m.external_source,
                    "external_id": m.external_id,
                }
                for m in modules
            ],
            "module_issues": [
                {"id": str(mi.id), "module_id": str(mi.module_id), "issue_id": str(mi.issue_id)}
                for mi in ModuleIssue.objects.filter(module_id__in=module_ids, deleted_at__isnull=True)
            ],
            "favorites": [
                {"id": str(f.id), "entity_type": f.entity_type, "entity_identifier": str(f.entity_identifier)}
                for f in UserFavorite.objects.filter(
                    entity_type__in=["cycle", "module"],
                    entity_identifier__in=cycle_ids + module_ids,
                    deleted_at__isnull=True,
                )
            ],
        }

    def _rollback(self, project: Project, manifest_path: str) -> None:
        with open(manifest_path) as manifest_file:
            manifest = json.load(manifest_file)

        if manifest.get("project_id") != str(project.id):
            raise CommandError(
                f"Manifest project_id {manifest.get('project_id')} does not match --project {project.id}"
            )

        actions = manifest.get("actions")
        if not actions:
            raise CommandError("Manifest has no 'actions' block; nothing to roll back")

        with transaction.atomic():
            # all_objects is a plain models.Manager (mixins.py), so .delete() here is already
            # a real hard delete -- no soft= kwarg to pass (that only exists on the
            # SoftDeletionQuerySet returned by the default .objects manager).
            CycleIssue.all_objects.filter(id__in=actions["created_cycle_issue_ids"]).delete()
            Cycle.all_objects.filter(id__in=actions["created_cycle_ids"]).delete()

            Cycle.all_objects.filter(id__in=actions["soft_deleted_cycle_ids"]).update(deleted_at=None)
            CycleIssue.all_objects.filter(id__in=actions["soft_deleted_cycle_issue_ids"]).update(deleted_at=None)
            Module.all_objects.filter(id__in=actions["soft_deleted_module_ids"]).update(deleted_at=None)
            ModuleIssue.all_objects.filter(id__in=actions["soft_deleted_module_issue_ids"]).update(deleted_at=None)

        self.stdout.write(
            self.style.SUCCESS(
                f"Rolled back: removed {len(actions['created_cycle_ids'])} created cycles, "
                f"restored {len(actions['soft_deleted_cycle_ids'])} cycles and "
                f"{len(actions['soft_deleted_module_ids'])} modules."
            )
        )
