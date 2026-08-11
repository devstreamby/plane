# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import uuid
from unittest.mock import Mock, patch

import pytest
from django.test import RequestFactory

from plane.authentication.adapter.error import AuthenticationException
from plane.authentication.ldap import (
    ActiveDirectoryClient,
    LdapConfiguration,
    LdapConfigurationError,
    LdapInvalidCredentials,
    LdapUser,
    get_ldap_configuration,
)
from plane.authentication.provider.credentials.ldap import LdapProvider
from plane.db.models import Account, User


LDAP_VALUES = (
    "dc01.example.local",
    "636",
    "plane-bind@example.local",
    "bind-secret",
    "OU=Users,DC=example,DC=local",
    "(&(objectClass=user)(sAMAccountName={username}))",
    "mail",
    "givenName",
    "sn",
    "",
)


def test_ldap_configuration_requires_username_placeholder():
    values = list(LDAP_VALUES)
    values[5] = "(sAMAccountName=static-user)"

    with patch("plane.authentication.ldap.get_configuration_value", return_value=tuple(values)):
        with pytest.raises(LdapConfigurationError, match="must contain"):
            get_ldap_configuration()


def test_ldap_configuration_rejects_url_in_server_field():
    values = list(LDAP_VALUES)
    values[0] = "ldaps://dc01.example.local"

    with patch("plane.authentication.ldap.get_configuration_value", return_value=tuple(values)):
        with pytest.raises(LdapConfigurationError, match="hostname or IP"):
            get_ldap_configuration()


def test_active_directory_client_escapes_username_in_search_filter():
    provider_id = "d915e2c5-f5e6-42f2-b128-a67b50cb7412"

    class Attribute:
        def __init__(self, value):
            self.value = value

    class Entry:
        entry_dn = "CN=Ada Lovelace,OU=Users,DC=example,DC=local"
        entry_attributes = ["objectGUID", "mail", "givenName", "sn"]
        values = {
            "objectGUID": Attribute(uuid.UUID(provider_id).bytes_le),
            "mail": Attribute("ada@example.com"),
            "givenName": Attribute("Ada"),
            "sn": Attribute("Lovelace"),
        }

        def __getitem__(self, name):
            return self.values[name]

    service_connection = Mock(entries=[Entry()])
    user_connection = Mock()
    client = ActiveDirectoryClient(
        LdapConfiguration(
            server="dc01.example.local",
            port=636,
            bind_dn="plane-bind@example.local",
            bind_password="bind-secret",
            user_search_base="OU=Users,DC=example,DC=local",
            user_search_filter="(sAMAccountName={username})",
            email_attribute="mail",
            first_name_attribute="givenName",
            last_name_attribute="sn",
            ca_certificate="",
        )
    )

    with patch.object(client, "_connection", side_effect=[service_connection, user_connection]):
        user = client.authenticate("ada*)(objectClass=*)", "domain-secret")

    search_filter = service_connection.search.call_args.kwargs["search_filter"]
    assert search_filter == r"(sAMAccountName=ada\2a\29\28objectClass=\2a\29)"
    assert user.provider_id == provider_id
    user_connection.unbind.assert_called_once()


@pytest.mark.django_db
def test_ldap_provider_provisions_and_links_directory_user():
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
        patch("plane.authentication.adapter.base.get_configuration_value", return_value=("1",)),
    ):
        client_class.return_value.authenticate.return_value = directory_user
        user = LdapProvider(request=request, username="ada", password="domain-secret").authenticate()

    assert user.email == "ada@example.com"
    assert user.first_name == "Ada"
    assert user.last_name == "Lovelace"
    assert user.is_password_autoset is True
    assert user.last_login_medium == "ldap"
    assert Account.objects.filter(
        user=user,
        provider="ldap",
        provider_account_id=directory_user.provider_id,
    ).exists()


@pytest.mark.django_db
def test_ldap_provider_maps_invalid_credentials_to_authentication_error():
    request = RequestFactory().post("/auth/ldap/")

    with (
        patch("plane.authentication.provider.credentials.ldap.get_configuration_value", return_value=("1",)),
        patch("plane.authentication.provider.credentials.ldap.get_ldap_configuration", return_value=Mock()),
        patch("plane.authentication.provider.credentials.ldap.ActiveDirectoryClient") as client_class,
    ):
        client_class.return_value.authenticate.side_effect = LdapInvalidCredentials
        with pytest.raises(AuthenticationException) as exc_info:
            LdapProvider(request=request, username="ada", password="wrong").authenticate()

    assert exc_info.value.error_message == "LDAP_INVALID_CREDENTIALS"
    assert not User.objects.exists()
