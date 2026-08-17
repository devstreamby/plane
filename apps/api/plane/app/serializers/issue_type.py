# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Module imports
from .base import BaseSerializer
from rest_framework import serializers

from plane.db.models import IssueType


class IssueTypeSerializer(BaseSerializer):
    is_default = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()

    class Meta:
        model = IssueType
        fields = [
            "id",
            "workspace_id",
            "name",
            "description",
            "logo_props",
            "is_active",
            "is_epic",
            "is_default",
            "level",
        ]
        read_only_fields = ["workspace", "is_epic", "is_default", "level"]

    def get_is_default(self, obj) -> bool:
        return bool(getattr(obj, "pit_is_default", False))

    def get_level(self, obj) -> float:
        return getattr(obj, "pit_level", 0)

    def validate_name(self, value):
        workspace_id = self.context.get("workspace_id")
        queryset = IssueType.objects.filter(workspace_id=workspace_id, name__iexact=value, is_active=True)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("An active work item type with this name already exists.")
        return value


class IssueTypeLiteSerializer(BaseSerializer):
    class Meta:
        model = IssueType
        fields = ["id", "name", "logo_props", "is_active", "is_epic"]
        read_only_fields = fields
