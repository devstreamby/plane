# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third party imports
from rest_framework import status
from rest_framework.response import Response
from drf_spectacular.utils import OpenApiResponse

# Module imports
from plane.api.serializers import TimeLogReportSerializer
from plane.app.permissions import ProjectEntityPermission, WorkspaceEntityPermission
from plane.utils.openapi import (
    time_report_docs,
    PROJECT_ID_PARAMETER,
    REPORT_START_DATE_PARAMETER,
    REPORT_END_DATE_PARAMETER,
    REPORT_PROJECT_IDS_PARAMETER,
    REPORT_USER_IDS_PARAMETER,
    REPORT_STRICT_PARAMETER,
    INVALID_REQUEST_RESPONSE,
)
from plane.utils.time_report import build_time_log_report, split_ids
from .base import BaseAPIView


STRICT_PARAMETER_VALUES = {"true", "1", "yes"}

REPORT_DESCRIPTION = """
Return every time log of the period in one response, aggregated per user, work item and
workspace-local day.

Hours are selected straight from the time logs, so work items that are archived, in draft or
in triage are **always** part of the report — an archived work item is marked with
`issues.<id>.archived`. Each log is split across the workspace-local calendar dates its
`started_at`–`stopped_at` interval spans; timers that are still running are not reported.

Access follows the token owner's roles: other members' logs are only returned for projects
where the owner is a project admin, or for every project when they are a workspace admin.
Otherwise only the owner's own logs come back and `can_view_others` is `false`. Projects that
were reported with own logs only are listed in `restricted_project_ids`, and projects the
owner cannot access at all in `unavailable_project_ids` — check both, or pass `strict=true`
to get a 403 instead of a quietly incomplete report.
""".strip()


class TimeLogReportMixin:
    """Shared response building for the workspace and project scoped report endpoints."""

    use_read_replica = True

    def build_response(self, request, slug, project_ids):
        try:
            report = build_time_log_report(
                slug=slug,
                user=request.user,
                start_date_str=request.GET.get("start_date"),
                end_date_str=request.GET.get("end_date"),
                project_ids=project_ids,
                user_ids=split_ids(request.GET.get("user_ids")),
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if request.GET.get("strict", "").lower() in STRICT_PARAMETER_VALUES and (
            report["restricted_project_ids"] or report["unavailable_project_ids"]
        ):
            return Response(
                {
                    "error": "The report would be incomplete for the requested projects.",
                    "restricted_project_ids": report["restricted_project_ids"],
                    "unavailable_project_ids": report["unavailable_project_ids"],
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(report, status=status.HTTP_200_OK)


class WorkspaceTimeLogReportAPIEndpoint(TimeLogReportMixin, BaseAPIView):
    """Workspace Time Log Report Endpoint"""

    serializer_class = TimeLogReportSerializer
    permission_classes = [WorkspaceEntityPermission]

    @time_report_docs(
        operation_id="retrieve_workspace_time_log_report",
        summary="Retrieve workspace time log report",
        description=REPORT_DESCRIPTION,
        parameters=[
            REPORT_START_DATE_PARAMETER,
            REPORT_END_DATE_PARAMETER,
            REPORT_PROJECT_IDS_PARAMETER,
            REPORT_USER_IDS_PARAMETER,
            REPORT_STRICT_PARAMETER,
        ],
        responses={
            200: OpenApiResponse(
                description="Time log report retrieved",
                response=TimeLogReportSerializer,
            ),
            400: INVALID_REQUEST_RESPONSE,
        },
    )
    def get(self, request, slug):
        """Retrieve workspace time log report

        Return every time log of the period across the workspace, aggregated per user,
        work item and workspace-local day. Archived work items are included.
        """
        return self.build_response(request, slug, project_ids=split_ids(request.GET.get("project_ids")))


class ProjectTimeLogReportAPIEndpoint(TimeLogReportMixin, BaseAPIView):
    """Project Time Log Report Endpoint"""

    serializer_class = TimeLogReportSerializer
    permission_classes = [ProjectEntityPermission]

    @time_report_docs(
        operation_id="retrieve_project_time_log_report",
        summary="Retrieve project time log report",
        description=REPORT_DESCRIPTION,
        parameters=[
            PROJECT_ID_PARAMETER,
            REPORT_START_DATE_PARAMETER,
            REPORT_END_DATE_PARAMETER,
            REPORT_USER_IDS_PARAMETER,
            REPORT_STRICT_PARAMETER,
        ],
        responses={
            200: OpenApiResponse(
                description="Time log report retrieved",
                response=TimeLogReportSerializer,
            ),
            400: INVALID_REQUEST_RESPONSE,
        },
    )
    def get(self, request, slug, project_id):
        """Retrieve project time log report

        Return every time log of the period for one project, aggregated per user,
        work item and workspace-local day. Archived work items are included.
        """
        return self.build_response(request, slug, project_ids=[str(project_id)])
