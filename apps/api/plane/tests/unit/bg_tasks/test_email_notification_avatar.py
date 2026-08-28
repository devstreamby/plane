# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Regression tests for the actor avatar in issue-update notification emails.

send_email_notification() used to build the avatar URL as
``f"{base_api}{actor.avatar_url}"``. User.avatar_url is None when the user has no
avatar, so that produced the string "<base_api>None" -- which is truthy, so the
template's ``{% if actor_detail.avatar_url %}`` guard always took the <img>
branch and its initial-circle fallback never fired. Every notification email
about a user without an avatar rendered a broken image.

These tests drive the real task against the real template, mocking only redis,
the SMTP configuration and the outgoing message, so a regression shows up as the
rendered HTML changing rather than as an assertion about an internal variable.
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from plane.bgtasks.email_notification_task import send_email_notification
from plane.db.models import FileAsset, Issue
from plane.tests.factories import ProjectFactory, UserFactory, WorkspaceFactory

pytestmark = pytest.mark.unit

BASE_API = "https://plane.example.com"


@pytest.fixture
def issue_and_actors(db):
    """An issue plus the actor who changed it and the receiver being notified."""
    workspace = WorkspaceFactory()
    project = ProjectFactory(workspace=workspace)
    # UserFactory leaves username unset, and username is unique -- two users from
    # the same factory would both get "" and collide. Set it explicitly.
    actor_id, receiver_id = uuid4().hex[:8], uuid4().hex[:8]
    actor = UserFactory(email=f"actor-{actor_id}@plane.so", username=f"actor_{actor_id}")
    receiver = UserFactory(email=f"receiver-{receiver_id}@plane.so", username=f"receiver_{receiver_id}")
    issue = Issue.objects.create(
        name="Something changed",
        project=project,
        workspace=workspace,
        created_by=actor,
    )
    return issue, actor, receiver


def render_notification(issue, actor, receiver):
    """Run the task and return the HTML body it would have sent."""
    notification_data = {
        str(actor.id): [
            {
                "issue_activity": {
                    "field": "state",
                    "old_value": "Todo",
                    "new_value": "In Progress",
                    "activity_time": "2026-08-28T10:51:00Z",
                }
            }
        ]
    }

    redis = MagicMock()
    redis.get.return_value = BASE_API.encode()

    captured = {}

    class RecordingMessage:
        def __init__(self, *args, **kwargs):
            pass

        def attach_alternative(self, content, mimetype):
            captured["html"] = content

        def send(self):
            return 1

    with (
        patch("plane.bgtasks.email_notification_task.redis_instance", return_value=redis),
        patch("plane.bgtasks.email_notification_task.acquire_lock", return_value=True),
        patch("plane.bgtasks.email_notification_task.release_lock"),
        patch(
            "plane.bgtasks.email_notification_task.get_email_configuration",
            return_value=("smtp.example.com", "user", "pass", "587", "1", "0", "noreply@example.com"),
        ),
        patch("plane.bgtasks.email_notification_task.get_connection"),
        patch("plane.bgtasks.email_notification_task.EmailMultiAlternatives", RecordingMessage),
    ):
        send_email_notification(
            issue_id=str(issue.id),
            notification_data=notification_data,
            receiver_id=str(receiver.id),
            email_notification_ids=[],
        )

    assert "html" in captured, "the task did not render/send an email"
    return captured["html"]


def test_actor_without_avatar_emits_no_broken_image(issue_and_actors):
    """The regression: the old code rendered src="<base_api>None"."""
    issue, actor, receiver = issue_and_actors

    html = render_notification(issue, actor, receiver)

    assert f"{BASE_API}None" not in html, "the broken avatar URL is back"
    # No avatar image pointing at our host at all. The template's other <img>
    # tags are logos and state icons on unrelated CDNs, so this stays specific
    # to the avatar without depending on their markup.
    assert f'<img src="{BASE_API}' not in html


def test_actor_without_avatar_renders_the_initial_fallback(issue_and_actors):
    """And the template's initial-circle fallback actually fires instead."""
    issue, actor, receiver = issue_and_actors
    actor.first_name = "Uladzislau"
    actor.save()

    html = render_notification(issue, actor, receiver)

    # The fallback is a 25px circle carrying the actor's first initial.
    assert "border-radius: 50%" in html
    circle = html.split("border-radius: 50%")[1][:400]
    assert ">\n" in circle or ">" in circle
    assert "U" in circle, "the actor's initial is missing from the fallback circle"


def test_actor_with_avatar_still_renders_the_image(issue_and_actors):
    """Behaviour preserved: a real avatar is still emitted as an absolute URL."""
    issue, actor, receiver = issue_and_actors
    asset = FileAsset.objects.create(
        attributes={"name": "me.png", "type": "image/png", "size": 1024},
        asset="deadbeef-me.png",
        size=1024,
        user=actor,
        created_by=actor,
        entity_type=FileAsset.EntityTypeContext.USER_AVATAR,
        is_uploaded=True,
    )
    actor.avatar_asset = asset
    actor.save()

    html = render_notification(issue, actor, receiver)

    expected = f"{BASE_API}/api/assets/v2/static/{asset.id}/"
    assert expected in html
    assert f'<img src="{expected}"' in html
