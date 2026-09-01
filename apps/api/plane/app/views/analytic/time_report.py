# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.http import HttpRequest
from rest_framework import status
from rest_framework.response import Response

from plane.app.permissions import ROLE, allow_permission
from plane.app.views.base import BaseAPIView
from plane.utils.time_report import build_time_log_report, split_ids


class WorkspaceTimeLogReportEndpoint(BaseAPIView):
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def get(self, request: HttpRequest, slug: str) -> Response:
        try:
            report = build_time_log_report(
                slug=slug,
                user=request.user,
                start_date_str=request.GET.get("start_date"),
                end_date_str=request.GET.get("end_date"),
                project_ids=split_ids(request.GET.get("project_ids")),
                user_ids=split_ids(request.GET.get("user_ids")),
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(report, status=status.HTTP_200_OK)


class ProjectTimeLogReportEndpoint(BaseAPIView):
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def get(self, request: HttpRequest, slug: str, project_id: str) -> Response:
        try:
            report = build_time_log_report(
                slug=slug,
                user=request.user,
                start_date_str=request.GET.get("start_date"),
                end_date_str=request.GET.get("end_date"),
                project_ids=[str(project_id)],
                user_ids=split_ids(request.GET.get("user_ids")),
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(report, status=status.HTTP_200_OK)
