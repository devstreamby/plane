# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest
from django.core.management import call_command

from plane.db.models import FileAsset, Issue, IssueComment, Page, Project, ProjectPage, Workspace, WorkspaceMember


def _video_link_html(project_id, asset_id, filename="clip.mp4"):
    return (
        f'<p><a href="/api/assets/v2/workspaces/test-workspace/projects/{project_id}/{asset_id}/">'
        f"Video: {filename}</a></p>"
    )


@pytest.fixture
def migrate_fixture(create_user, workspace):
    project = Project.objects.create(
        name="Migrate Project",
        identifier="MIG",
        workspace=workspace,
        created_by=create_user,
    )

    video_asset = FileAsset.objects.create(
        attributes={"name": "clip.mp4", "type": "video/mp4", "size": 1024},
        asset=f"{workspace.id}/clip.mp4",
        size=1024,
        workspace=workspace,
        project=project,
        created_by=create_user,
        entity_type=FileAsset.EntityTypeContext.ISSUE_DESCRIPTION,
        is_uploaded=True,
    )

    image_asset = FileAsset.objects.create(
        attributes={"name": "photo.png", "type": "image/png", "size": 512},
        asset=f"{workspace.id}/photo.png",
        size=512,
        workspace=workspace,
        project=project,
        created_by=create_user,
        entity_type=FileAsset.EntityTypeContext.ISSUE_DESCRIPTION,
        is_uploaded=True,
    )

    attachment_video_asset = FileAsset.objects.create(
        attributes={"name": "attached.mp4", "type": "video/mp4", "size": 2048},
        asset=f"{workspace.id}/attached.mp4",
        size=2048,
        workspace=workspace,
        project=project,
        created_by=create_user,
        entity_type=FileAsset.EntityTypeContext.ISSUE_ATTACHMENT,
        is_uploaded=True,
    )

    issue = Issue.objects.create(
        name="Task with a video link",
        project=project,
        workspace=workspace,
        created_by=create_user,
        description_html=(
            _video_link_html(project.id, video_asset.id)
            + f'<p><a href="/api/assets/v2/workspaces/test-workspace/projects/{project.id}/'
            f'{image_asset.id}/">image</a></p>' + '<p><a href="https://example.com/unrelated">unrelated</a></p>'
        ),
    )

    comment = IssueComment.objects.create(
        issue=issue,
        project=project,
        workspace=workspace,
        created_by=create_user,
        actor=create_user,
        comment_html=_video_link_html(project.id, video_asset.id, "comment-clip.mp4"),
    )

    page = Page.objects.create(
        name="Doc with a video",
        workspace=workspace,
        owned_by=create_user,
        created_by=create_user,
        description_html=_video_link_html(project.id, video_asset.id, "page-clip.mp4"),
    )
    ProjectPage.objects.create(
        workspace=workspace,
        project=project,
        page=page,
        created_by=create_user,
    )

    return {
        "workspace": workspace,
        "project": project,
        "video_asset": video_asset,
        "image_asset": image_asset,
        "attachment_video_asset": attachment_video_asset,
        "issue": issue,
        "comment": comment,
        "page": page,
    }


@pytest.mark.unit
@pytest.mark.django_db
def test_migrate_replaces_video_links_and_leaves_others_alone(migrate_fixture):
    fx = migrate_fixture
    call_command("migrate_eva_videos", workspace=fx["workspace"].slug)

    fx["issue"].refresh_from_db()
    fx["comment"].refresh_from_db()
    fx["page"].refresh_from_db()

    issue_html = fx["issue"].description_html
    assert "<video-component" in issue_html
    assert f'src="{fx["video_asset"].id}"' in issue_html
    assert 'source="upload"' in issue_html
    assert 'status="uploaded"' in issue_html
    # the image link and the unrelated external link must survive untouched
    assert (
        f'href="/api/assets/v2/workspaces/test-workspace/projects/{fx["project"].id}/{fx["image_asset"].id}/"'
        in issue_html
    )
    assert 'href="https://example.com/unrelated"' in issue_html

    assert "<video-component" in fx["comment"].comment_html
    assert f'src="{fx["video_asset"].id}"' in fx["comment"].comment_html

    assert "<video-component" in fx["page"].description_html
    assert fx["page"].description_binary is None


@pytest.mark.unit
@pytest.mark.django_db
def test_migrate_does_not_touch_attachment_shaped_links(migrate_fixture):
    """Issue-attachment links (which have /issues/<id>/attachments/ in the path) must stay plain
    links even when they point at a video asset -- attachments are a deliberately different UI."""
    fx = migrate_fixture
    attachment_href = (
        f"/api/assets/v2/workspaces/test-workspace/projects/{fx['project'].id}/issues/"
        f"{fx['issue'].id}/attachments/{fx['attachment_video_asset'].id}/"
    )
    fx["issue"].description_html = f'<p><a href="{attachment_href}">Video: attached.mp4</a></p>'
    fx["issue"].save()

    call_command("migrate_eva_videos", workspace=fx["workspace"].slug)

    fx["issue"].refresh_from_db()
    assert "<video-component" not in fx["issue"].description_html
    assert attachment_href in fx["issue"].description_html


@pytest.mark.unit
@pytest.mark.django_db
def test_migrate_dry_run_makes_no_changes(migrate_fixture):
    fx = migrate_fixture
    original_html = fx["issue"].description_html

    call_command("migrate_eva_videos", workspace=fx["workspace"].slug, dry_run=True)

    fx["issue"].refresh_from_db()
    assert fx["issue"].description_html == original_html
    assert "<video-component" not in fx["issue"].description_html


@pytest.mark.unit
@pytest.mark.django_db
def test_migrate_is_idempotent(migrate_fixture):
    fx = migrate_fixture
    call_command("migrate_eva_videos", workspace=fx["workspace"].slug)
    fx["issue"].refresh_from_db()
    once = fx["issue"].description_html

    call_command("migrate_eva_videos", workspace=fx["workspace"].slug)
    fx["issue"].refresh_from_db()
    twice = fx["issue"].description_html

    assert once == twice


@pytest.mark.unit
@pytest.mark.django_db
def test_migrate_is_scoped_to_the_given_workspace(migrate_fixture, create_user):
    fx = migrate_fixture

    other_workspace = Workspace.objects.create(name="Other Workspace", owner=create_user, slug="other-workspace")
    WorkspaceMember.objects.create(workspace=other_workspace, member=create_user, role=20)
    other_project = Project.objects.create(
        name="Other Project", identifier="OTH", workspace=other_workspace, created_by=create_user
    )
    other_video_asset = FileAsset.objects.create(
        attributes={"name": "other.mp4", "type": "video/mp4", "size": 999},
        asset=f"{other_workspace.id}/other.mp4",
        size=999,
        workspace=other_workspace,
        project=other_project,
        created_by=create_user,
        entity_type=FileAsset.EntityTypeContext.ISSUE_DESCRIPTION,
        is_uploaded=True,
    )
    other_issue = Issue.objects.create(
        name="Other workspace task",
        project=other_project,
        workspace=other_workspace,
        created_by=create_user,
        description_html=(
            f'<p><a href="/api/assets/v2/workspaces/other-workspace/projects/{other_project.id}/'
            f'{other_video_asset.id}/">Video: other.mp4</a></p>'
        ),
    )

    call_command("migrate_eva_videos", workspace=fx["workspace"].slug)

    other_issue.refresh_from_db()
    assert "<video-component" not in other_issue.description_html
