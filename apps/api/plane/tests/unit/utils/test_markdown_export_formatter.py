# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest

from plane.utils.porters.formatters import MarkdownFormatter


@pytest.mark.unit
class TestMarkdownFormatter:
    def test_empty_data_returns_empty_string(self):
        assert MarkdownFormatter().encode([]) == ""

    def test_heading_and_description_body(self):
        content = MarkdownFormatter().encode([{"identifier": "TP-1", "name": "Fix bug", "description": "It **broke**."}])
        assert content.startswith("### TP-1 — Fix bug\n\nIt **broke**.")

    def test_metadata_line_included_for_extra_fields(self):
        content = MarkdownFormatter().encode(
            [{"identifier": "TP-1", "name": "Fix bug", "description": "", "state_name": "Done", "priority": "high"}]
        )
        assert "_State Name: Done · Priority: high_" in content

    def test_empty_extra_field_omitted_from_metadata(self):
        content = MarkdownFormatter().encode([{"identifier": "TP-1", "name": "Fix bug", "description": "", "priority": ""}])
        assert "_" not in content

    def test_missing_identifier_falls_back_to_name_only(self):
        content = MarkdownFormatter().encode([{"name": "Fix bug", "description": ""}])
        assert content.startswith("### Fix bug")

    def test_multiple_rows_are_separated(self):
        content = MarkdownFormatter().encode(
            [
                {"identifier": "TP-1", "name": "First", "description": ""},
                {"identifier": "TP-2", "name": "Second", "description": ""},
            ]
        )
        assert "### TP-1 — First" in content
        assert "### TP-2 — Second" in content
        assert "\n\n---\n\n" in content

    def test_extension_is_md(self):
        assert MarkdownFormatter().extension == "md"

    def test_decode_is_not_supported(self):
        with pytest.raises(NotImplementedError):
            MarkdownFormatter().decode("### TP-1 — Fix bug")
