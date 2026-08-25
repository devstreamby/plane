# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from bs4 import BeautifulSoup
from markdownify import ATX, markdownify

# Editor content with no real body serializes to this exact string
_EMPTY_DESCRIPTION_HTML = frozenset(("", "<p></p>"))

# The rich text editor renders embeds (images, videos, mentions) as custom tags
# (e.g. <image-component src="...">) that markdownify doesn't know how to convert
# and would otherwise drop silently. Resolving them to real links would need
# authenticated asset lookups, so we swap in a visible placeholder instead —
# the reader at least knows something was here.
_PLACEHOLDER_TAGS = {
    "image-component": "[image]",
    "video-component": "[video]",
    "mention-component": "[mention]",
}


def html_to_markdown(html: str | None) -> str:
    """Convert issue description HTML to Markdown for release-notes style exports."""
    if not html or html in _EMPTY_DESCRIPTION_HTML:
        return ""

    soup = BeautifulSoup(html, "html.parser")
    for tag_name, placeholder in _PLACEHOLDER_TAGS.items():
        for tag in soup.find_all(tag_name):
            tag.replace_with(placeholder)

    return markdownify(str(soup), heading_style=ATX).strip()
