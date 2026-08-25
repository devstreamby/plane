# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest

from plane.utils.html_to_markdown import html_to_markdown


@pytest.mark.unit
class TestHtmlToMarkdown:
    def test_empty_description_returns_empty_string(self):
        assert html_to_markdown("") == ""
        assert html_to_markdown(None) == ""
        assert html_to_markdown("<p></p>") == ""

    def test_bold_and_paragraph(self):
        assert html_to_markdown("<p>Users could not <strong>log in</strong>.</p>") == "Users could not **log in**."

    def test_list_items(self):
        result = html_to_markdown("<ul><li>First</li><li>Second</li></ul>")
        assert "* First" in result
        assert "* Second" in result

    def test_link(self):
        result = html_to_markdown('<p><a href="https://plane.so">Plane</a></p>')
        assert result == "[Plane](https://plane.so)"

    def test_heading_uses_atx_style(self):
        assert html_to_markdown("<h2>Section</h2>") == "## Section"

    def test_image_component_becomes_placeholder(self):
        result = html_to_markdown('<p>See below.</p><image-component src="abc123"></image-component>')
        assert "[image]" in result
        assert "abc123" not in result

    def test_video_and_mention_components_become_placeholders(self):
        result = html_to_markdown(
            '<video-component source="upload" src="abc"></video-component>'
            '<mention-component entity_name="user_mention" entity_identifier="xyz"></mention-component>'
        )
        assert "[video]" in result
        assert "[mention]" in result
