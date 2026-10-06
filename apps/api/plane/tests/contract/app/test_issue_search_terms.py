# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest

from plane.db.models import Issue, Project, ProjectMember
from plane.utils.issue_search import MAX_SEARCH_TERMS, build_issue_search_q, search_issues, split_search_terms

pytestmark = [pytest.mark.contract, pytest.mark.django_db]


@pytest.fixture
def project(workspace, create_user):
    project = Project.objects.create(name="Search", identifier="SRCH", workspace=workspace)
    ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
    return project


@pytest.fixture
def issues(project):
    def make(name, description=""):
        return Issue.objects.create(
            name=name,
            project=project,
            workspace=project.workspace,
            description_html=f"<p>{description}</p>" if description else "<p></p>",
        )

    return {
        "report": make("Time logs report for the month"),
        "eva": make("Login page broken", "Перенесено из EVA: DOC-000529, не открывается форма"),
        "other": make("Unrelated work item"),
    }


def names(queryset):
    return {issue.name for issue in queryset}


@pytest.mark.parametrize(
    "query",
    [
        "Time logs report",  # whole phrase, as before
        "report logs",  # other order
        "rep tim",  # partial words
        "REPORT   month",  # case and extra spaces
    ],
)
def test_terms_match_name_in_any_order_and_partially(issues, query):
    assert names(search_issues(query, Issue.objects.all())) == {issues["report"].name}


def test_every_term_must_match(issues):
    assert not search_issues("report nonexistent", Issue.objects.all())


def test_description_is_searched(issues):
    assert names(search_issues("DOC-000529", Issue.objects.all())) == {issues["eva"].name}
    # words may be split between the title and the description
    assert names(search_issues("login форма", Issue.objects.all())) == {issues["eva"].name}


def test_project_identifier_and_sequence_still_work(issues):
    assert names(search_issues("SRCH", Issue.objects.all())) == {issue.name for issue in issues.values()}
    sequence = issues["other"].sequence_id
    assert issues["other"].name in names(search_issues(f"{sequence}", Issue.objects.all()))


def test_numbers_in_long_free_text_are_not_sequence_ids(issues):
    sequence = issues["other"].sequence_id
    query = f"nonexistent phrase with a number {sequence} inside"
    assert not search_issues(query, Issue.objects.all())


def test_empty_query_does_not_filter(issues):
    assert str(build_issue_search_q("   ")) == "(AND: )"
    assert search_issues("", Issue.objects.all()).count() == 3


def test_terms_are_deduplicated_and_capped():
    assert split_search_terms("Foo foo FOO bar") == ["Foo", "bar"]
    assert len(split_search_terms(" ".join(f"w{i}" for i in range(50)))) == MAX_SEARCH_TERMS


def test_global_search_endpoint_uses_terms(session_client, project, issues):
    response = session_client.get(
        f"/api/workspaces/{project.workspace.slug}/search/",
        {"search": "logs report", "workspace_search": "true"},
    )
    assert response.status_code == 200
    assert [i["name"] for i in response.data["results"]["issue"]] == [issues["report"].name]


def test_project_issue_search_endpoint_finds_by_description(session_client, project, issues):
    response = session_client.get(
        f"/api/workspaces/{project.workspace.slug}/projects/{project.id}/search-issues/",
        {"search": "EVA DOC-000529"},
    )
    assert response.status_code == 200
    assert [i["name"] for i in response.data] == [issues["eva"].name]


def test_public_work_item_search_uses_terms(api_key_client, project, issues):
    response = api_key_client.get(
        f"/api/v1/workspaces/{project.workspace.slug}/work-items/search/",
        {"search": "month report", "workspace_search": "true"},
    )
    assert response.status_code == 200, response.data
    assert [i["name"] for i in response.data["issues"]] == [issues["report"].name]
