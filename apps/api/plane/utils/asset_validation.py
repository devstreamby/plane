# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from plane.db.models import FileAsset

# Image types accepted everywhere an asset can be uploaded (avatars, covers,
# logos, attachments, and editor-embedded content).
IMAGE_MIME_TYPES = ["image/jpeg", "image/png", "image/webp", "image/jpg", "image/gif"]

# Video types accepted only for editor-embedded content (work item
# descriptions, comments, pages). Restricted to formats browsers can play
# back natively via <video> without transcoding.
EDITOR_VIDEO_MIME_TYPES = ["video/mp4", "video/webm", "video/ogg"]

# Entity types that represent rich-text editor content, where video embeds
# are allowed in addition to images. Avatars/covers/logos are intentionally
# excluded — those stay image-only.
_EDITOR_CONTENT_ENTITY_TYPES = {
    FileAsset.EntityTypeContext.ISSUE_DESCRIPTION,
    FileAsset.EntityTypeContext.COMMENT_DESCRIPTION,
    FileAsset.EntityTypeContext.PAGE_DESCRIPTION,
    FileAsset.EntityTypeContext.DRAFT_ISSUE_DESCRIPTION,
}


def get_allowed_mime_types(entity_type: str) -> list[str]:
    """Return the list of MIME types allowed for a given FileAsset entity type."""
    if entity_type in _EDITOR_CONTENT_ENTITY_TYPES:
        return IMAGE_MIME_TYPES + EDITOR_VIDEO_MIME_TYPES
    return IMAGE_MIME_TYPES
