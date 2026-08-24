# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from __future__ import annotations

import re
import uuid
from typing import Any

from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand, CommandError

from plane.db.models import FileAsset, Issue, IssueComment, Page, Workspace

# Matches only the "description"-type asset URL shape
# (/api/assets/v2/workspaces/<slug>/projects/<project_id>/<asset_id>/), with an optional scheme+host
# prefix (plane_asset_href() prepends WEB_URL). Deliberately does NOT match the issue-attachment
# shape, which has extra /issues/<id>/attachments/ segments -- attachments are meant to stay as
# plain download links, not become inline video-components.
_DESCRIPTION_ASSET_HREF_RE = re.compile(
    r"^(?:https?://[^/]+)?/api/assets/v2/workspaces/[^/]+/projects/[0-9a-fA-F-]{36}/(?P<asset_id>[0-9a-fA-F-]{36})/?$"
)


def _extract_asset_id(href: str) -> str | None:
    match = _DESCRIPTION_ASSET_HREF_RE.match(href.strip())
    return match.group("asset_id") if match else None


def migrate_video_links_in_html(html: str, video_assets_by_id: dict[str, FileAsset]) -> tuple[str, int]:
    """Replaces any ``<a href="...">`` pointing at a known video FileAsset with a playable
    ``<video-component>`` node. Matches by the linked asset's id (looked up by the caller from its
    MIME type), not by the link's text -- the EVA importer always writes "Video: <filename>" but
    matching on MIME is robust to that text having been hand-edited since.

    Returns (possibly unchanged) html and how many links were replaced.
    """
    if not html or "/api/assets/v2/" not in html:
        return html, 0

    soup = BeautifulSoup(html, "html.parser")
    replaced = 0
    for link in soup.find_all("a", href=True):
        asset_id = _extract_asset_id(link["href"])
        if not asset_id or asset_id not in video_assets_by_id:
            continue

        component = soup.new_tag("video-component")
        component["id"] = str(uuid.uuid4())
        component["source"] = "upload"
        component["src"] = asset_id
        component["status"] = "uploaded"
        link.replace_with(component)
        replaced += 1

    if not replaced:
        return html, 0
    return str(soup), replaced


class Command(BaseCommand):
    help = (
        "One-off migration of already-imported EVA video links (plain download <a> tags) into "
        "playable video-component nodes, across issue descriptions, comments, and pages in a "
        "workspace. Matches candidates by the linked FileAsset's MIME type (video/*), not by the "
        "link's text, so it's robust to hand-edited link text."
    )

    def add_arguments(self, parser):
        parser.add_argument("--workspace", required=True, help="Workspace slug to scope the migration to")
        parser.add_argument("--dry-run", action="store_true", help="Print the plan; make no changes")
        parser.add_argument(
            "--batch-size", type=int, default=200, help="Rows to fetch per chunk when iterating (default 200)"
        )

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            workspace = Workspace.objects.get(slug=options["workspace"])
        except Workspace.DoesNotExist as error:
            raise CommandError(f"No workspace with slug '{options['workspace']}'") from error

        dry_run = options["dry_run"]
        batch_size = options["batch_size"]

        video_assets_by_id = {
            str(asset.id): asset
            for asset in FileAsset.objects.filter(
                workspace=workspace,
                is_deleted=False,
                is_uploaded=True,
                entity_type__in=[
                    FileAsset.EntityTypeContext.ISSUE_DESCRIPTION,
                    FileAsset.EntityTypeContext.COMMENT_DESCRIPTION,
                    FileAsset.EntityTypeContext.PAGE_DESCRIPTION,
                ],
            )
            if str((asset.attributes or {}).get("type", "")).startswith("video/")
        }

        self.stdout.write(f"Workspace: {workspace.name} ({workspace.slug})")
        self.stdout.write(f"Video description-assets found: {len(video_assets_by_id)}")

        if not video_assets_by_id:
            self.stdout.write(self.style.WARNING("Nothing to migrate."))
            return

        issues_changed = self._migrate_issues(workspace, video_assets_by_id, batch_size, dry_run)
        comments_changed = self._migrate_comments(workspace, video_assets_by_id, batch_size, dry_run)
        pages_changed = self._migrate_pages(workspace, video_assets_by_id, batch_size, dry_run)

        verb = "Would update" if dry_run else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb}: {issues_changed} issue description(s), {comments_changed} comment(s), {pages_changed} page(s)"
            )
        )
        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run: no changes made."))

    def _migrate_issues(
        self, workspace: Workspace, video_assets_by_id: dict[str, FileAsset], batch_size: int, dry_run: bool
    ) -> int:
        changed = 0
        queryset = (
            Issue.objects.filter(workspace=workspace)
            .select_related("project")
            .order_by("id")
            .iterator(chunk_size=batch_size)
        )
        for issue in queryset:
            new_html, replaced = migrate_video_links_in_html(issue.description_html, video_assets_by_id)
            if not replaced:
                continue
            changed += 1
            label = f"{issue.project.identifier}-{issue.sequence_id}" if issue.project else str(issue.id)
            self.stdout.write(f"  Issue {label}: {replaced} video link(s)")
            if dry_run:
                continue
            issue.description_html = new_html
            issue.save()
        return changed

    def _migrate_comments(
        self, workspace: Workspace, video_assets_by_id: dict[str, FileAsset], batch_size: int, dry_run: bool
    ) -> int:
        changed = 0
        queryset = IssueComment.objects.filter(workspace=workspace).order_by("id").iterator(chunk_size=batch_size)
        for comment in queryset:
            new_html, replaced = migrate_video_links_in_html(comment.comment_html, video_assets_by_id)
            if not replaced:
                continue
            changed += 1
            self.stdout.write(f"  Comment {comment.id}: {replaced} video link(s)")
            if dry_run:
                continue
            comment.comment_html = new_html
            comment.save()
        return changed

    def _migrate_pages(
        self, workspace: Workspace, video_assets_by_id: dict[str, FileAsset], batch_size: int, dry_run: bool
    ) -> int:
        changed = 0
        queryset = Page.objects.filter(workspace=workspace).order_by("id").iterator(chunk_size=batch_size)
        for page in queryset:
            new_html, replaced = migrate_video_links_in_html(page.description_html, video_assets_by_id)
            if not replaced:
                continue
            changed += 1
            self.stdout.write(f"  Page {page.id} '{page.name}': {replaced} video link(s)")
            if dry_run:
                continue
            page.description_html = new_html
            # Pages are collaborative (Yjs) -- invalidate the stored binary so the live server
            # regenerates it from description_html on next open, instead of the client seeing
            # stale content from the old binary. Same pattern as PageDuplicateEndpoint.
            page.description_binary = None
            page.save()
        return changed
