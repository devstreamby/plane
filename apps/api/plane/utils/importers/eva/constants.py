# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import os

EVA_EXTERNAL_SOURCE = "eva"

# EVA models sprints and releases as the same CmfList entity, distinguished only by task field
# ("lists" vs "fix_versions") and code prefix (SPR-* vs REL-*). Which one becomes a Plane cycle
# vs module is a per-import choice.
CYCLE_SOURCE_LISTS = "lists"
CYCLE_SOURCE_FIX_VERSIONS = "fix_versions"
CYCLE_SOURCE_NONE = "none"
CYCLE_SOURCE_CHOICES = (CYCLE_SOURCE_LISTS, CYCLE_SOURCE_FIX_VERSIONS, CYCLE_SOURCE_NONE)
DEFAULT_CYCLE_SOURCE = CYCLE_SOURCE_LISTS

MODULE_SOURCE_FIX_VERSIONS = "fix_versions"
MODULE_SOURCE_LISTS = "lists"
MODULE_SOURCE_NONE = "none"
MODULE_SOURCE_CHOICES = (MODULE_SOURCE_FIX_VERSIONS, MODULE_SOURCE_LISTS, MODULE_SOURCE_NONE)
DEFAULT_MODULE_SOURCE = MODULE_SOURCE_FIX_VERSIONS

# Server-side EVA import bypasses the browser upload cap; screen recordings are often 10–200 MiB.
EVA_IMPORT_VIDEO_SIZE_LIMIT = int(os.environ.get("EVA_IMPORT_VIDEO_SIZE_LIMIT", 209715200))
EVA_IMPORT_DOWNLOAD_TIMEOUT = int(os.environ.get("EVA_IMPORT_DOWNLOAD_TIMEOUT", 300))

EVA_STATUS_TO_STATE_GROUP = {
    "OPEN": "unstarted",
    "IN_PROGRESS": "started",
    "IN_REVIEW": "started",
    "CLOSED": "completed",
}

EVA_PRIORITY_TO_PLANE = {
    -1: "low",
    0: "none",
    1: "low",
    2: "medium",
    3: "high",
    4: "urgent",
    5: "urgent",
}

EVA_RELATION_TO_PLANE = {
    "system.link": "relates_to",
    "blocks": "blocked_by",
    "blocked_by": "blocked_by",
    "duplicate": "duplicate",
    "relates_to": "relates_to",
}

TASK_FIELDS = [
    "code",
    "name",
    "text",
    "status",
    "cache_status_type",
    "priority",
    "responsible.name",
    "responsible.login",
    "cmf_author.name",
    "cmf_author.login",
    "cmf_created_at",
    "status_closed_at",
    "deadline",
    "alarm_date",
    "op_gantt_task.sched_start_date",
    "op_gantt_task.sched_finish_date",
    "tags",
    "request_type.name",
    "lists",
    "fix_versions",
    "parent_task",
    "parent_task_id",
    "cache_child_tasks_count",
    "out_tasks.code",
    "out_tasks.relation_type",
    "in_tasks.code",
    "in_tasks.relation_type",
]

COMMENT_FIELDS = [
    "text",
    "parent_id",
    "cmf_author.name",
    "cmf_author.login",
    "cmf_created_at",
    "private",
]

ATTACHMENT_FIELDS = [
    "name",
    "parent_id",
    "code",
    "url",
    "download_url",
]

DOCUMENT_FIELDS = [
    "code",
    "name",
    "text",
    "cmf_author.login",
    "cmf_created_at",
]

TESTCASE_FIELDS = [
    "code",
    "name",
    "text",
    "precondition",
    "expected_result",
    "parent_id",
    "parent_task",
    "cache_status_type",
    "priority",
    "responsible.login",
    "cmf_author.login",
    "cmf_created_at",
    "steps.code",
    "steps.name",
    "steps.text",
    "steps.expected_result",
    "steps.comment",
]

CHUNK_SIZE = 100
