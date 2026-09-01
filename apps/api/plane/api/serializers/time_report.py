# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third party imports
from rest_framework import serializers


class TimeLogReportEntrySerializer(serializers.Serializer):
    """One user's logged seconds on one work item on one workspace-local day."""

    user_id = serializers.UUIDField(allow_null=True)
    issue_id = serializers.UUIDField()
    project_id = serializers.UUIDField()
    date = serializers.DateField()
    duration_seconds = serializers.IntegerField()


class TimeLogReportIssueSerializer(serializers.Serializer):
    """Work item referenced by the report entries."""

    name = serializers.CharField()
    sequence_id = serializers.IntegerField()
    project_id = serializers.UUIDField()
    project_identifier = serializers.CharField()
    state_name = serializers.CharField(allow_null=True)
    archived = serializers.BooleanField()


class TimeLogReportUserSerializer(serializers.Serializer):
    """User referenced by the report entries."""

    display_name = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    avatar_url = serializers.CharField(allow_null=True)


class TimeLogReportSerializer(serializers.Serializer):
    """Aggregated time log report. Documentation-only: the view returns a plain dict."""

    start_date = serializers.DateField()
    end_date = serializers.DateField()
    can_view_others = serializers.BooleanField()
    restricted_project_ids = serializers.ListField(child=serializers.UUIDField())
    unavailable_project_ids = serializers.ListField(child=serializers.UUIDField())
    entries = TimeLogReportEntrySerializer(many=True)
    issues = serializers.DictField(child=TimeLogReportIssueSerializer())
    users = serializers.DictField(child=TimeLogReportUserSerializer())
