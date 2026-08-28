# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Regression tests for avatar handling in Adapter.sync_user_data().

sync_user_data() runs on every sign-in once IDP sync is enabled. It used to call
delete_old_avatar() unconditionally, before knowing whether the provider had
supplied a replacement. delete_old_avatar() removes the object from storage as
well as the FileAsset row, so for any provider that does not send an avatar the
user's own uploaded avatar was destroyed -- irrecoverably -- on their next login.

The LDAP provider hardcodes "avatar": "" and ENABLE_LDAP_SYNC defaults to on, so
this was every LDAP login, not an edge case.
"""

from unittest.mock import Mock, patch

import pytest
from django.test import RequestFactory

from plane.authentication.adapter.base import Adapter
from plane.authentication.ldap import LdapUser
from plane.authentication.provider.credentials.ldap import LdapProvider
from plane.db.models import FileAsset, User

pytestmark = pytest.mark.unit


def make_adapter(avatar):
    """An Adapter primed with the user payload a provider would produce."""
    adapter = Adapter(request=RequestFactory().post("/auth/ldap/"), provider="ldap")
    adapter.user_data = {
        "email": "ada@example.com",
        "user": {
            "avatar": avatar,
            "first_name": "Ada",
            "last_name": "Lovelace",
            "display_name": "ada",
        },
    }
    return adapter


@pytest.fixture
def user_with_avatar(db):
    """A user whose avatar was uploaded through the UI, not by a provider."""
    user = User.objects.create(email="ada@example.com", username="ada")
    asset = FileAsset.objects.create(
        attributes={"name": "me.png", "type": "image/png", "size": 1024},
        asset="deadbeef-me.png",
        size=1024,
        user=user,
        created_by=user,
        entity_type=FileAsset.EntityTypeContext.USER_AVATAR,
        is_uploaded=True,
    )
    user.avatar_asset = asset
    user.save()
    return user, asset


@pytest.mark.django_db
def test_sync_keeps_avatar_when_provider_sends_none(user_with_avatar):
    """The regression: no avatar from the provider must mean "leave it alone"."""
    user, asset = user_with_avatar
    adapter = make_adapter(avatar="")

    with patch.object(Adapter, "delete_old_avatar") as delete_old_avatar:
        adapter.sync_user_data(user=user)

    delete_old_avatar.assert_not_called()

    user.refresh_from_db()
    assert user.avatar_asset_id == asset.id
    assert FileAsset.objects.filter(pk=asset.id).exists()


@pytest.mark.django_db
def test_sync_keeps_avatar_when_provider_omits_the_key(user_with_avatar):
    """Same when the payload has no "avatar" key at all, not just an empty one."""
    user, asset = user_with_avatar
    adapter = make_adapter(avatar="")
    del adapter.user_data["user"]["avatar"]

    with patch.object(Adapter, "delete_old_avatar") as delete_old_avatar:
        adapter.sync_user_data(user=user)

    delete_old_avatar.assert_not_called()

    user.refresh_from_db()
    assert user.avatar_asset_id == asset.id


@pytest.mark.django_db
def test_sync_still_syncs_other_fields_when_avatar_is_absent(user_with_avatar):
    """Skipping the avatar must not skip the rest of the sync."""
    user, _ = user_with_avatar
    adapter = make_adapter(avatar="")

    with patch.object(Adapter, "delete_old_avatar"):
        adapter.sync_user_data(user=user)

    user.refresh_from_db()
    assert user.first_name == "Ada"
    assert user.last_name == "Lovelace"
    assert user.display_name == "ada"


@pytest.mark.django_db
def test_sync_replaces_avatar_when_provider_sends_one(user_with_avatar):
    """Behaviour preserved: a provider that does send an avatar still wins."""
    user, old_asset = user_with_avatar
    adapter = make_adapter(avatar="https://idp.example.com/avatar.png")

    new_asset = FileAsset.objects.create(
        attributes={"name": "idp.png", "type": "image/png", "size": 2048},
        asset="cafebabe-idp.png",
        size=2048,
        user=user,
        created_by=user,
        entity_type=FileAsset.EntityTypeContext.USER_AVATAR,
        is_uploaded=True,
    )

    with (
        patch.object(Adapter, "delete_old_avatar") as delete_old_avatar,
        patch.object(Adapter, "download_and_upload_avatar", return_value=new_asset),
    ):
        adapter.sync_user_data(user=user)

    delete_old_avatar.assert_called_once()

    user.refresh_from_db()
    assert user.avatar_asset_id == new_asset.id
    assert user.avatar_asset_id != old_asset.id


@pytest.mark.django_db
def test_sync_falls_back_to_remote_url_when_upload_fails(user_with_avatar):
    """Behaviour preserved: a failed download still records the provider's URL."""
    user, _ = user_with_avatar
    remote = "https://idp.example.com/avatar.png"
    adapter = make_adapter(avatar=remote)

    with (
        patch.object(Adapter, "delete_old_avatar") as delete_old_avatar,
        patch.object(Adapter, "download_and_upload_avatar", return_value=None),
    ):
        adapter.sync_user_data(user=user)

    delete_old_avatar.assert_called_once()

    user.refresh_from_db()
    assert user.avatar == remote


@pytest.mark.django_db
def test_ldap_login_does_not_wipe_an_existing_avatar(user_with_avatar):
    """End-to-end over the path that actually broke in production.

    A returning LDAP user signs in with sync enabled. The LDAP provider never
    supplies an avatar, so the one the user uploaded must survive the login.
    """
    user, asset = user_with_avatar

    directory_user = LdapUser(
        provider_id="d915e2c5-f5e6-42f2-b128-a67b50cb7412",
        dn="CN=Ada Lovelace,OU=Users,DC=example,DC=local",
        email="ada@example.com",
        first_name="Ada",
        last_name="Lovelace",
    )
    request = RequestFactory().post("/auth/ldap/")

    with (
        patch("plane.authentication.provider.credentials.ldap.get_configuration_value", return_value=("1",)),
        patch("plane.authentication.provider.credentials.ldap.get_ldap_configuration", return_value=Mock()),
        patch("plane.authentication.provider.credentials.ldap.ActiveDirectoryClient") as client_class,
        # ENABLE_LDAP_SYNC on -- the configuration this deployment actually runs.
        patch("plane.authentication.adapter.base.get_configuration_value", return_value=("1",)),
    ):
        client_class.return_value.authenticate.return_value = directory_user
        signed_in = LdapProvider(request=request, username="ada", password="domain-secret").authenticate()

    assert signed_in.id == user.id

    user.refresh_from_db()
    assert user.avatar_asset_id == asset.id, "LDAP sign-in wiped the user's avatar"
    assert FileAsset.objects.filter(pk=asset.id).exists(), "LDAP sign-in deleted the avatar asset"
