# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import re
import unicodedata

# Django imports
from django.db.models import F, Func, OuterRef, Prefetch
from django.http import HttpResponse
from django.utils import timezone

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from .. import BaseAPIView
from plane.app.permissions import allow_permission, ROLE
from plane.db.models import Cycle, FileAsset, Issue, IssueComment, IssueLink, IssueRelation, IssueSubscriber
from plane.utils.porters.exporter import DataExporter
from plane.utils.porters.serializers.issue import IssueExportSerializer

DEFAULT_EXPORT_FIELDS = ["identifier", "name", "description"]

# All columns a caller may request, in the order they should appear in the export.
# "identifier", "name" and "description" are always included by default; the rest
# are opt-in extras a user can add for a richer export.
ALLOWED_EXPORT_FIELDS = [
    "identifier",
    "name",
    "description",
    "state_name",
    "priority",
    "assignees",
    "subscribers",
    "labels",
    "cycles",
    "modules",
    "estimate",
    "start_date",
    "target_date",
    "completed_at",
    "created_at",
    "updated_at",
    "created_by_name",
    "parent",
    "links",
    "relations",
    "comments",
    "sub_issues_count",
    "link_count",
    "attachment_count",
]

ALLOWED_EXPORT_FORMATS = {"csv": "text/csv", "markdown": "text/markdown"}

# Extra select_related/prefetch_related/annotate needed per column, applied only when
# that column is actually requested so the default (identifier, name, description)
# export doesn't pay for joins nobody asked for.
_EXPORT_FIELD_REQUIREMENTS = {
    "state_name": {"select_related": ("state",)},
    "estimate": {"select_related": ("estimate_point",)},
    "created_by_name": {"select_related": ("created_by",)},
    "parent": {"select_related": ("parent", "parent__project")},
    "assignees": {"prefetch_related": ("assignees",)},
    "subscribers": {
        "prefetch_related": (Prefetch("issue_subscribers", queryset=IssueSubscriber.objects.select_related("subscriber")),)
    },
    "labels": {"prefetch_related": ("label_issue__label",)},
    "cycles": {"prefetch_related": ("issue_cycle__cycle",)},
    "modules": {"prefetch_related": ("issue_module__module",)},
    "links": {"prefetch_related": ("issue_link",)},
    "relations": {
        "prefetch_related": (
            Prefetch("issue_relation", queryset=IssueRelation.objects.select_related("related_issue", "related_issue__project")),
            Prefetch("issue_related", queryset=IssueRelation.objects.select_related("issue", "issue__project")),
        )
    },
    "comments": {
        "prefetch_related": (
            Prefetch("issue_comments", queryset=IssueComment.objects.select_related("actor").order_by("created_at")),
        )
    },
    "sub_issues_count": {
        "annotate": {
            "sub_issues_count": Issue.issue_objects.filter(parent=OuterRef("id"))
            .order_by()
            .annotate(count=Func(F("id"), function="Count"))
            .values("count")
        }
    },
    "link_count": {
        "annotate": {
            "link_count": IssueLink.objects.filter(issue=OuterRef("id"))
            .order_by()
            .annotate(count=Func(F("id"), function="Count"))
            .values("count")
        }
    },
    "attachment_count": {
        "annotate": {
            "attachment_count": FileAsset.objects.filter(
                issue_id=OuterRef("id"), entity_type=FileAsset.EntityTypeContext.ISSUE_ATTACHMENT
            )
            .order_by()
            .annotate(count=Func(F("id"), function="Count"))
            .values("count")
        }
    },
}


def _slugify_for_filename(value: str) -> str:
    """Best-effort ASCII slug for a Content-Disposition filename (non-ASCII names are dropped, not encoded)."""
    ascii_value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^A-Za-z0-9]+", "-", ascii_value).strip("-").lower()
    return slug


def _export_filename_base(cycle) -> str:
    parts = [
        cycle.project.identifier if cycle.project_id else "",
        _slugify_for_filename(cycle.name) or "cycle",
        timezone.now().date().isoformat(),
    ]
    return "-".join(p for p in parts if p)


class CycleIssueExportEndpoint(BaseAPIView):
    """
    Synchronous export of a single cycle's issues, meant for quick release-notes
    style downloads. Unlike the workspace-level exporter, this returns the file
    directly in the response instead of going through Celery/S3.
    """

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def get(self, request, slug, project_id, cycle_id):
        # NB: "export_format" (not "format") to avoid colliding with DRF's
        # URL_FORMAT_OVERRIDE, which intercepts a "format" query param for
        # content negotiation before this view ever runs.
        export_format = request.GET.get("export_format", "csv")
        if export_format not in ALLOWED_EXPORT_FORMATS:
            return Response(
                {"error": f"format must be one of {sorted(ALLOWED_EXPORT_FORMATS)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        raw_fields = request.GET.get("fields")
        fields = [f.strip() for f in raw_fields.split(",") if f.strip()] if raw_fields else list(DEFAULT_EXPORT_FIELDS)
        invalid_fields = [f for f in fields if f not in ALLOWED_EXPORT_FIELDS]
        if invalid_fields:
            return Response(
                {"error": f"Unknown field(s): {', '.join(invalid_fields)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cycle = Cycle.objects.filter(workspace__slug=slug, project_id=project_id, id=cycle_id).select_related("project").first()
        if not cycle:
            return Response({"error": "Cycle not found"}, status=status.HTTP_404_NOT_FOUND)

        issues = (
            Issue.issue_objects.filter(
                workspace__slug=slug,
                project_id=project_id,
                issue_cycle__cycle_id=cycle_id,
                issue_cycle__deleted_at__isnull=True,
            )
            .select_related("project")
            .order_by("sequence_id")
        )

        select_related, prefetch_related, annotate_kwargs = set(), [], {}
        for field in fields:
            requirement = _EXPORT_FIELD_REQUIREMENTS.get(field, {})
            select_related.update(requirement.get("select_related", ()))
            prefetch_related.extend(requirement.get("prefetch_related", ()))
            annotate_kwargs.update(requirement.get("annotate", {}))

        if select_related:
            issues = issues.select_related(*select_related)
        if prefetch_related:
            issues = issues.prefetch_related(*prefetch_related)
        if annotate_kwargs:
            issues = issues.annotate(**annotate_kwargs)

        exporter = DataExporter(IssueExportSerializer, format_type=export_format, fields=fields)
        filename, content = exporter.export(_export_filename_base(cycle), issues)

        response = HttpResponse(content, content_type=f"{ALLOWED_EXPORT_FORMATS[export_format]}; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
