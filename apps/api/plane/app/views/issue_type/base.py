# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.db import transaction
from django.db.models import F

# Third party imports
from rest_framework.response import Response
from rest_framework import status

# Module imports
from .. import BaseViewSet
from plane.app.serializers import IssueTypeSerializer
from plane.app.permissions import ROLE, allow_permission
from plane.db.models import Issue, IssueType, Project, ProjectIssueType, Workspace
from plane.utils.issue_type import ensure_default_issue_types


class IssueTypeViewSet(BaseViewSet):
    serializer_class = IssueTypeSerializer
    model = IssueType

    def get_queryset(self):
        return self.filter_queryset(
            super()
            .get_queryset()
            .filter(workspace__slug=self.kwargs.get("slug"))
            .filter(
                project_issue_types__project_id=self.kwargs.get("project_id"),
                project_issue_types__deleted_at__isnull=True,
            )
            .filter(
                project_issue_types__project__project_projectmember__member=self.request.user,
                project_issue_types__project__project_projectmember__is_active=True,
                project_issue_types__project__archived_at__isnull=True,
            )
            .annotate(pit_is_default=F("project_issue_types__is_default"))
            .annotate(pit_level=F("project_issue_types__level"))
            .distinct()
        )

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def list(self, request, slug, project_id):
        queryset = self.get_queryset()
        if not queryset.exists():
            project = Project.objects.filter(pk=project_id, workspace__slug=slug, is_issue_type_enabled=True).first()
            if project is not None:
                ensure_default_issue_types(project)
                queryset = self.get_queryset()

        serializer = IssueTypeSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def retrieve(self, request, slug, project_id, pk):
        issue_type = self.get_queryset().get(pk=pk)
        serializer = IssueTypeSerializer(issue_type)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @allow_permission([ROLE.ADMIN])
    def create(self, request, slug, project_id):
        workspace_id = Workspace.objects.only("id").get(slug=slug).id
        serializer = IssueTypeSerializer(data=request.data, context={"workspace_id": workspace_id})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            issue_type = IssueType.objects.create(
                workspace_id=workspace_id,
                name=serializer.validated_data["name"],
                description=serializer.validated_data.get("description", ""),
                logo_props=serializer.validated_data.get("logo_props", {}),
                is_active=serializer.validated_data.get("is_active", True),
            )
            next_level = ProjectIssueType.objects.filter(project_id=project_id).count()
            ProjectIssueType.objects.create(
                project_id=project_id, issue_type=issue_type, level=next_level, is_default=False
            )

        issue_type = self.get_queryset().get(pk=issue_type.pk)
        return Response(IssueTypeSerializer(issue_type).data, status=status.HTTP_201_CREATED)

    @allow_permission([ROLE.ADMIN])
    def partial_update(self, request, slug, project_id, pk):
        workspace_id = Workspace.objects.only("id").get(slug=slug).id
        issue_type = self.get_queryset().get(pk=pk)
        serializer = IssueTypeSerializer(
            issue_type, data=request.data, partial=True, context={"workspace_id": workspace_id}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()

        issue_type = self.get_queryset().get(pk=pk)
        return Response(IssueTypeSerializer(issue_type).data, status=status.HTTP_200_OK)

    @allow_permission([ROLE.ADMIN])
    def destroy(self, request, slug, project_id, pk):
        issue_type = self.get_queryset().get(pk=pk)

        if issue_type.pit_is_default:
            return Response(
                {"error": "Невозможно удалить тип рабочего элемента, установленный по умолчанию для этого проекта."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        issues_count = Issue.objects.filter(project_id=project_id, type_id=pk).count()
        if issues_count:
            return Response(
                {
                    "error": "Тип используется в задачах и не может быть удалён.",
                    "issues_count": issues_count,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        issue_type.is_active = False
        issue_type.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @allow_permission([ROLE.ADMIN])
    def mark_as_default(self, request, slug, project_id, pk):
        issue_type = self.get_queryset().get(pk=pk)

        if not issue_type.is_active:
            return Response(
                {"error": "Активируйте этот тип перед установкой по умолчанию."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            ProjectIssueType.objects.filter(project_id=project_id, is_default=True).update(is_default=False)
            ProjectIssueType.objects.filter(project_id=project_id, issue_type_id=pk).update(is_default=True)

        issue_type = self.get_queryset().get(pk=pk)
        return Response(IssueTypeSerializer(issue_type).data, status=status.HTTP_200_OK)
