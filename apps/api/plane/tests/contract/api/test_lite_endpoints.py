# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Contract tests for the read-only `-lite` list endpoints.

These four routes exist so the official plane-mcp-server (>= 0.2.10) can talk to
this deployment: its `project list`, `member list_workspace`, `cycle list` and
`module list` actions call `-lite` paths exclusively and 404'd against us before.

The shape assertions below mirror what the Plane SDK's pydantic models require,
so a regression here shows up as a broken MCP tool rather than a failing test in
some unrelated suite.
"""

from datetime import timedelta
from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework import status

from plane.db.models import APIToken, Cycle, Module, Project, ProjectMember, User, Workspace, WorkspaceMember

PAGINATION_KEYS = {
    "results",
    "total_count",
    "next_cursor",
    "prev_cursor",
    "next_page_results",
    "prev_page_results",
    "count",
    "total_pages",
    "total_results",
}


@pytest.fixture
def project(db, workspace, create_user):
    """A project with the token's user as an active admin member."""
    project = Project.objects.create(
        name="Test Project",
        identifier="TP",
        workspace=workspace,
        created_by=create_user,
        cycle_view=True,
        module_view=True,
    )
    ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
    return project


@pytest.fixture
def archived_project(db, workspace, create_user):
    """An archived project the user is a member of."""
    project = Project.objects.create(
        name="Archived Project",
        identifier="AP",
        workspace=workspace,
        created_by=create_user,
        archived_at=timezone.now(),
    )
    ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
    return project


@pytest.fixture
def non_admin_client(api_client, db, workspace):
    """An API-key client for a workspace member with the plain Member role (15)."""
    unique_id = uuid4().hex[:8]
    member = User.objects.create(
        email=f"member-{unique_id}@plane.so",
        username=f"member_{unique_id}",
        first_name="Plain",
        last_name="Member",
    )
    member.set_password("test-password")
    member.save()
    WorkspaceMember.objects.create(workspace=workspace, member=member, role=15, is_active=True)

    token = APIToken.objects.create(user=member, label="Member token", token=f"member-token-{unique_id}")
    api_client.credentials(HTTP_X_API_KEY=token.token)
    return api_client


@pytest.fixture
def outsider_client(api_client, db):
    """An API-key client for a user who belongs to no workspace under test."""
    unique_id = uuid4().hex[:8]
    outsider = User.objects.create(
        email=f"outsider-{unique_id}@plane.so",
        username=f"outsider_{unique_id}",
        first_name="Out",
        last_name="Sider",
    )
    outsider.set_password("test-password")
    outsider.save()
    # Give them a workspace of their own so the token has somewhere to live.
    Workspace.objects.create(name="Other", owner=outsider, slug=f"other-{unique_id}")

    token = APIToken.objects.create(user=outsider, label="Outsider token", token=f"outsider-token-{unique_id}")
    api_client.credentials(HTTP_X_API_KEY=token.token)
    return api_client


def result_ids(payload):
    """Ids as strings.

    `response.data` holds native Python values (UUIDs here), not the rendered JSON,
    so compare stringified ids rather than the raw objects.
    """
    return [str(row["id"]) for row in payload["results"]]


def assert_paginated_envelope(payload):
    """The SDK's PaginatedResponse model requires every one of these keys."""
    assert isinstance(payload, dict), f"expected the paginated envelope, got a bare {type(payload).__name__}"
    missing = PAGINATION_KEYS - set(payload)
    assert not missing, f"envelope is missing {sorted(missing)}"
    assert isinstance(payload["results"], list)


@pytest.mark.contract
class TestProjectsLite:
    """GET /api/v1/workspaces/{slug}/projects-lite/"""

    def get_url(self, slug):
        return f"/api/v1/workspaces/{slug}/projects-lite/"

    @pytest.mark.django_db
    def test_returns_paginated_lite_projects(self, api_key_client, workspace, project):
        response = api_key_client.get(self.get_url(workspace.slug))

        assert response.status_code == status.HTTP_200_OK
        assert_paginated_envelope(response.data)

        assert str(project.id) in result_ids(response.data)

        row = next(r for r in response.data["results"] if str(r["id"]) == str(project.id))
        # identifier and name are non-optional in the SDK's ProjectLite model.
        assert row["identifier"] == "TP"
        assert row["name"] == "Test Project"
        assert "archived_at" in row

    @pytest.mark.django_db
    def test_archived_projects_hidden_by_default(self, api_key_client, workspace, project, archived_project):
        response = api_key_client.get(self.get_url(workspace.slug))

        assert response.status_code == status.HTTP_200_OK
        ids = result_ids(response.data)
        assert str(project.id) in ids
        assert str(archived_project.id) not in ids

    @pytest.mark.django_db
    def test_archived_projects_included_on_request(self, api_key_client, workspace, project, archived_project):
        response = api_key_client.get(self.get_url(workspace.slug), {"include_archived": "true"})

        assert response.status_code == status.HTTP_200_OK
        assert str(archived_project.id) in result_ids(response.data)

    @pytest.mark.django_db
    def test_outsider_cannot_list(self, outsider_client, workspace, project):
        response = outsider_client.get(self.get_url(workspace.slug))

        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@pytest.mark.contract
class TestMembersLite:
    """GET /api/v1/workspaces/{slug}/members-lite/"""

    def get_url(self, slug):
        return f"/api/v1/workspaces/{slug}/members-lite/"

    @pytest.mark.django_db
    def test_returns_paginated_envelope_not_bare_list(self, api_key_client, workspace, create_user):
        response = api_key_client.get(self.get_url(workspace.slug))

        assert response.status_code == status.HTTP_200_OK
        # The non-lite /members/ route answers with a bare array; this one must not.
        assert_paginated_envelope(response.data)

        emails = [row["email"] for row in response.data["results"]]
        assert create_user.email in emails

    @pytest.mark.django_db
    def test_each_row_carries_role(self, api_key_client, workspace, create_user):
        response = api_key_client.get(self.get_url(workspace.slug))

        assert response.status_code == status.HTTP_200_OK
        row = next(r for r in response.data["results"] if r["email"] == create_user.email)
        assert row["role"] == 20

    @pytest.mark.django_db
    def test_non_admin_member_can_list(self, non_admin_client, workspace):
        """The deliberate difference from /members/, which is admin-only.

        Resolving assignees is an everyday lookup, so a plain Member must get 200
        here. This test fails if the view is switched to WorkSpaceAdminPermission.
        """
        response = non_admin_client.get(self.get_url(workspace.slug))

        assert response.status_code == status.HTTP_200_OK
        assert_paginated_envelope(response.data)

    @pytest.mark.django_db
    def test_outsider_cannot_list(self, outsider_client, workspace):
        response = outsider_client.get(self.get_url(workspace.slug))

        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@pytest.mark.contract
class TestCyclesLite:
    """GET /api/v1/workspaces/{slug}/projects/{project_id}/cycles-lite/"""

    def get_url(self, slug, project_id):
        return f"/api/v1/workspaces/{slug}/projects/{project_id}/cycles-lite/"

    @pytest.fixture
    def current_cycle(self, db, project, create_user):
        return Cycle.objects.create(
            name="Current Cycle",
            start_date=timezone.now() - timedelta(days=1),
            end_date=timezone.now() + timedelta(days=6),
            project=project,
            workspace=project.workspace,
            owned_by=create_user,
        )

    @pytest.fixture
    def upcoming_cycle(self, db, project, create_user):
        return Cycle.objects.create(
            name="Upcoming Cycle",
            start_date=timezone.now() + timedelta(days=10),
            end_date=timezone.now() + timedelta(days=20),
            project=project,
            workspace=project.workspace,
            owned_by=create_user,
        )

    @pytest.mark.django_db
    def test_returns_paginated_lite_cycles(self, api_key_client, workspace, project, current_cycle):
        response = api_key_client.get(self.get_url(workspace.slug, project.id))

        assert response.status_code == status.HTTP_200_OK
        assert_paginated_envelope(response.data)
        assert [row["name"] for row in response.data["results"]] == ["Current Cycle"]

    @pytest.mark.django_db
    def test_status_current_still_paginates(self, api_key_client, workspace, project, current_cycle, upcoming_cycle):
        """The full cycle list returns a bare array for `current`; this one must not.

        The SDK documents the lite route as always paginating, so copying that
        quirk here would break `cycle list` for exactly one status value.
        """
        response = api_key_client.get(self.get_url(workspace.slug, project.id), {"status": "current"})

        assert response.status_code == status.HTTP_200_OK
        assert_paginated_envelope(response.data)
        assert [row["name"] for row in response.data["results"]] == ["Current Cycle"]

    @pytest.mark.django_db
    def test_status_upcoming_filters(self, api_key_client, workspace, project, current_cycle, upcoming_cycle):
        response = api_key_client.get(self.get_url(workspace.slug, project.id), {"status": "upcoming"})

        assert response.status_code == status.HTTP_200_OK
        assert [row["name"] for row in response.data["results"]] == ["Upcoming Cycle"]

    @pytest.mark.django_db
    def test_unknown_status_returns_all(self, api_key_client, workspace, project, current_cycle, upcoming_cycle):
        response = api_key_client.get(self.get_url(workspace.slug, project.id), {"status": "nonsense"})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 2


@pytest.mark.contract
class TestModulesLite:
    """GET /api/v1/workspaces/{slug}/projects/{project_id}/modules-lite/"""

    def get_url(self, slug, project_id):
        return f"/api/v1/workspaces/{slug}/projects/{project_id}/modules-lite/"

    @pytest.fixture
    def module(self, db, project, create_user):
        return Module.objects.create(
            name="Test Module",
            project=project,
            workspace=project.workspace,
            created_by=create_user,
        )

    @pytest.mark.django_db
    def test_returns_paginated_lite_modules(self, api_key_client, workspace, project, module):
        response = api_key_client.get(self.get_url(workspace.slug, project.id))

        assert response.status_code == status.HTTP_200_OK
        assert_paginated_envelope(response.data)
        assert [row["name"] for row in response.data["results"]] == ["Test Module"]

    @pytest.mark.django_db
    def test_empty_project_returns_empty_envelope(self, api_key_client, workspace, project):
        response = api_key_client.get(self.get_url(workspace.slug, project.id))

        assert response.status_code == status.HTTP_200_OK
        assert_paginated_envelope(response.data)
        assert response.data["results"] == []
