# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import path


from plane.app.views import (
    StateViewSet,
    IntakeStateEndpoint,
    StateTransitionEndpoint,
    BoardColumnViewSet,
)


urlpatterns = [
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/states/",
        StateViewSet.as_view({"get": "list", "post": "create"}),
        name="project-states",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/states/<uuid:pk>/",
        StateViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}),
        name="project-state",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/state-transitions/",
        StateTransitionEndpoint.as_view(),
        name="project-state-transitions",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/board-columns/",
        BoardColumnViewSet.as_view({"get": "list", "post": "create"}),
        name="project-board-columns",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/board-columns/<uuid:pk>/",
        BoardColumnViewSet.as_view({"patch": "partial_update", "delete": "destroy"}),
        name="project-board-column",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/intake-state/",
        IntakeStateEndpoint.as_view(),
        name="intake-state",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/states/<uuid:pk>/mark-default/",
        StateViewSet.as_view({"post": "mark_as_default"}),
        name="project-state",
    ),
]
