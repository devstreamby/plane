# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Module imports
from .base import BaseSerializer
from rest_framework import serializers

from plane.db.models import BoardColumn, State, StateGroup


class StateSerializer(BaseSerializer):
    order = serializers.FloatField(required=False)

    class Meta:
        model = State
        fields = [
            "id",
            "project_id",
            "workspace_id",
            "name",
            "color",
            "group",
            "default",
            "description",
            "sequence",
            "order",
            "allow_any_transition",
        ]
        read_only_fields = ["workspace", "project"]

    def validate(self, attrs):
        if attrs.get("group") == StateGroup.TRIAGE.value:
            raise serializers.ValidationError("Cannot create triage state")
        return attrs


class StateLiteSerializer(BaseSerializer):
    class Meta:
        model = State
        fields = ["id", "name", "color", "group"]
        read_only_fields = fields


class BoardColumnSerializer(BaseSerializer):
    state_ids = serializers.SerializerMethodField()

    class Meta:
        model = BoardColumn
        fields = ["id", "project_id", "workspace_id", "name", "sequence", "state_ids"]
        read_only_fields = ["workspace", "project", "state_ids"]

    def get_state_ids(self, obj) -> list:
        return [str(state.id) for state in obj.states.all()]
