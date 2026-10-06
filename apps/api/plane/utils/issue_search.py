# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import re

# Django imports
from django.db.models import Q

# A pasted paragraph must not turn into dozens of joins/conditions.
MAX_SEARCH_TERMS = 8
MAX_SEARCH_TERM_LENGTH = 100
# Longer queries are free text, so digits in them are not work item numbers.
MAX_SEQUENCE_QUERY_LENGTH = 20

# Text fields every search term is looked up in. The description is included because work
# items imported from EVA keep most of their searchable text (the EVA task key, the original
# wording) there rather than in the title.
SEARCH_TEXT_FIELDS = ("name", "description_stripped", "project__identifier")


def split_search_terms(query):
    """Split a free text query into unique, case-insensitive terms."""
    terms = []
    seen = set()
    for term in (query or "").split():
        term = term[:MAX_SEARCH_TERM_LENGTH]
        key = term.casefold()
        if key in seen:
            continue
        seen.add(key)
        terms.append(term)
        if len(terms) == MAX_SEARCH_TERMS:
            break
    return terms


def build_issue_search_q(query):
    """Build the Q used by every work item search.

    Every whitespace separated term has to occur (case-insensitive substring) in the name,
    the description or the project identifier, in any order, so ``"report time"`` finds
    "Time logs report". A short query that contains whole numbers also matches the work
    items with that sequence id.

    An empty query yields an empty ``Q`` (no filtering).
    """
    terms = split_search_terms(query)
    if not terms:
        return Q()

    text_q = Q()
    for term in terms:
        term_q = Q()
        for field in SEARCH_TEXT_FIELDS:
            term_q |= Q(**{f"{field}__icontains": term})
        text_q &= term_q

    if len(query) <= MAX_SEQUENCE_QUERY_LENGTH:
        # Match whole integers only (exclude decimal numbers)
        for sequence_id in re.findall(r"\b\d+\b", query):
            text_q |= Q(sequence_id=sequence_id)

    return text_q


def search_issues(query, queryset):
    return queryset.filter(build_issue_search_q(query)).distinct()
