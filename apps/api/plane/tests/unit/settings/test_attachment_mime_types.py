# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest

from plane.db.models import FileAsset
from plane.settings.common import ATTACHMENT_MIME_TYPES
from plane.utils.asset_validation import get_allowed_mime_types

# MIME types whose content can execute script when served with an "inline"
# Content-Disposition. Attachments (ATTACHMENT_MIME_TYPES) are always served
# with "attachment" -- see GenericAssetEndpoint.get / IssueAttachmentV2Endpoint.get
# -- so it's fine for the attachment list to include them. But
# get_allowed_mime_types() also governs avatars/covers/logos, which are served
# by StaticFileAssetEndpoint: AllowAny + inline by default. None of these types
# may ever appear there.
_SCRIPT_EXECUTING_MIME_TYPES = {
    "text/html",
    "application/xhtml+xml",
    "image/svg+xml",
    "text/xml",
    "application/xml",
}


@pytest.mark.unit
def test_new_text_and_heic_types_are_attachable():
    """Regression guard for the reported bug: these types must stay in the
    attachment allowlist so csv/txt/css/json/har/html/heic uploads succeed."""
    for mime_type in [
        "text/csv",
        "text/plain",
        "text/css",
        "application/json",
        "text/html",
        "image/heic",
        "image/heif",
    ]:
        assert mime_type in ATTACHMENT_MIME_TYPES, f"{mime_type} must be attachable"


@pytest.mark.unit
def test_attachment_mime_types_has_no_duplicates():
    assert len(ATTACHMENT_MIME_TYPES) == len(set(ATTACHMENT_MIME_TYPES))


@pytest.mark.unit
def test_get_allowed_mime_types_never_allows_script_executing_types():
    """The security invariant: no entity type resolved by get_allowed_mime_types()
    (avatars, covers, logos, and editor-embedded content -- all of which can be
    served inline, some via an AllowAny endpoint) may include a type that can
    execute script when rendered. Prevents a future edit from turning
    get_allowed_mime_types() into a second attachment-style allowlist and
    reopening an unauthenticated stored-XSS hole."""
    for entity_type in FileAsset.EntityTypeContext.values:
        allowed = get_allowed_mime_types(entity_type)
        leaked = _SCRIPT_EXECUTING_MIME_TYPES & set(allowed)
        assert not leaked, f"{entity_type} allows script-executing type(s): {leaked}"
