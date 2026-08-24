# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""End-to-end coverage for the reported bug: uploading csv/html/txt/css/heic/
json/har attachments to a work item was rejected with "Invalid file type.",
because the client was sending an empty MIME type for text files that have no
binary signature to sniff -- these types were already allowed server-side,
they just never reached the allowlist check with a non-empty type.
"""

from unittest import mock

import pytest
from rest_framework import status

from plane.db.models import FileAsset, Issue, Project, ProjectMember


@pytest.fixture
def attachment_context(workspace, create_user):
    project = Project.objects.create(name="Attachment project", identifier="ATT", workspace=workspace)
    ProjectMember.objects.create(project=project, member=create_user, role=20)
    issue = Issue.objects.create(name="Issue with attachments", project=project, workspace=workspace)
    return {"project": project, "issue": issue}


@pytest.mark.contract
class TestIssueAttachmentMimeTypes:
    @staticmethod
    def url(workspace_slug, project_id, issue_id):
        return f"/api/assets/v2/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/attachments/"

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "mime_type",
        [
            "text/csv",
            "text/plain",
            "text/css",
            "application/json",
            "text/html",
            "image/heic",
            "image/heif",
        ],
    )
    def test_previously_rejected_types_are_now_accepted(self, session_client, workspace, attachment_context, mime_type):
        payload = {"name": "notes.dat", "type": mime_type, "size": 1024}

        with mock.patch("plane.app.views.issue.attachment.S3Storage") as mock_storage:
            mock_storage.return_value.generate_presigned_post.return_value = {"url": "https://signed.example", "fields": {}}
            response = session_client.post(
                self.url(workspace.slug, attachment_context["project"].id, attachment_context["issue"].id),
                payload,
                format="json",
            )

        assert response.status_code == status.HTTP_200_OK, f"Got {response.status_code}: {response.data!r}"
        asset = FileAsset.objects.get(id=response.data["asset_id"])
        assert asset.attributes["type"] == mime_type

    @pytest.mark.django_db
    @pytest.mark.parametrize("mime_type", ["", "application/x-msdownload"])
    def test_still_rejects_empty_and_unsupported_types(self, session_client, workspace, attachment_context, mime_type):
        payload = {"name": "evil.dat", "type": mime_type, "size": 1024}

        response = session_client.post(
            self.url(workspace.slug, attachment_context["project"].id, attachment_context["issue"].id),
            payload,
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST, f"Got {response.status_code}: {response.data!r}"
        assert response.data["error"] == "Invalid file type."
