# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import path

from plane.api.views import (
    WorkspaceTimeLogReportAPIEndpoint,
    ProjectTimeLogReportAPIEndpoint,
)

urlpatterns = [
    path(
        "workspaces/<str:slug>/time-logs-report/",
        WorkspaceTimeLogReportAPIEndpoint.as_view(http_method_names=["get"]),
        name="workspace-time-logs-report",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/time-logs-report/",
        ProjectTimeLogReportAPIEndpoint.as_view(http_method_names=["get"]),
        name="project-time-logs-report",
    ),
]
