# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.http import HttpRequest
from rest_framework import status
from rest_framework.response import Response

from plane.app.permissions import ROLE, allow_permission
from plane.app.views.base import BaseAPIView
from plane.utils.time_calendar import (
    TimeLogCalendarBadRequest,
    TimeLogCalendarForbidden,
    TimeLogCalendarNotFound,
    build_time_log_calendar,
)
from plane.utils.time_report import TimeLogReportValidationError, report_validation_message


class WorkspaceTimeLogsEndpoint(BaseAPIView):
    """List one member's time logs for a date window, for the week calendar."""

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def get(self, request: HttpRequest, slug: str) -> Response:
        try:
            payload = build_time_log_calendar(
                slug=slug,
                user=request.user,
                start_date_str=request.GET.get("start_date"),
                end_date_str=request.GET.get("end_date"),
                target_user_id=request.GET.get("user_id"),
            )
        except TimeLogReportValidationError as exc:
            return Response({"error": report_validation_message(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except TimeLogCalendarBadRequest:
            return Response({"error": "user_id must be a UUID."}, status=status.HTTP_400_BAD_REQUEST)
        except TimeLogCalendarForbidden:
            return Response(
                {
                    "code": "forbidden",
                    "error": "You can only view your own time logs unless you administer a project.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        except TimeLogCalendarNotFound:
            return Response(
                {"error": "User was not found in this workspace."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(payload, status=status.HTTP_200_OK)
