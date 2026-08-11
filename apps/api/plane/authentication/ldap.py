# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import os
import ssl
import uuid
from dataclasses import dataclass

from ldap3 import Connection, NONE, Server, Tls
from ldap3.core.exceptions import LDAPBindError, LDAPException, LDAPSocketOpenError
from ldap3.utils.conv import escape_filter_chars

from plane.license.utils.instance_value import get_configuration_value


class LdapConfigurationError(Exception):
    pass


class LdapConnectionError(Exception):
    pass


class LdapInvalidCredentials(Exception):
    pass


class LdapUserNotFound(Exception):
    pass


class LdapUserDataError(Exception):
    pass


@dataclass(frozen=True)
class LdapConfiguration:
    server: str
    port: int
    bind_dn: str
    bind_password: str
    user_search_base: str
    user_search_filter: str
    email_attribute: str
    first_name_attribute: str
    last_name_attribute: str
    ca_certificate: str


@dataclass(frozen=True)
class LdapUser:
    provider_id: str
    dn: str
    email: str
    first_name: str
    last_name: str


LDAP_CONFIGURATION_DEFAULTS = {
    "LDAP_SERVER": "",
    "LDAP_PORT": "636",
    "LDAP_BIND_DN": "",
    "LDAP_BIND_PASSWORD": "",
    "LDAP_USER_SEARCH_BASE": "",
    "LDAP_USER_SEARCH_FILTER": "(&(objectClass=user)(|(sAMAccountName={username})(userPrincipalName={username})))",
    "LDAP_EMAIL_ATTRIBUTE": "mail",
    "LDAP_FIRST_NAME_ATTRIBUTE": "givenName",
    "LDAP_LAST_NAME_ATTRIBUTE": "sn",
    "LDAP_CA_CERTIFICATE": "",
}


def get_ldap_configuration(overrides=None):
    overrides = overrides or {}
    keys = [
        {
            "key": key,
            "default": overrides.get(key, os.environ.get(key, default)),
        }
        for key, default in LDAP_CONFIGURATION_DEFAULTS.items()
    ]
    values = get_configuration_value(keys)
    data = dict(zip(LDAP_CONFIGURATION_DEFAULTS.keys(), values))
    data.update({key: value for key, value in overrides.items() if key in LDAP_CONFIGURATION_DEFAULTS})

    required_keys = (
        "LDAP_SERVER",
        "LDAP_BIND_DN",
        "LDAP_BIND_PASSWORD",
        "LDAP_USER_SEARCH_BASE",
        "LDAP_USER_SEARCH_FILTER",
        "LDAP_EMAIL_ATTRIBUTE",
    )
    if any(not str(data.get(key, "")).strip() for key in required_keys):
        raise LdapConfigurationError("Active Directory configuration is incomplete")

    server = str(data["LDAP_SERVER"]).strip()
    if "://" in server or "/" in server:
        raise LdapConfigurationError("LDAP server must be a hostname or IP address")

    try:
        port = int(data["LDAP_PORT"])
    except (TypeError, ValueError) as exc:
        raise LdapConfigurationError("LDAP port must be a number") from exc
    if not 1 <= port <= 65535:
        raise LdapConfigurationError("LDAP port is outside the valid range")

    search_filter = str(data["LDAP_USER_SEARCH_FILTER"]).strip()
    if "{username}" not in search_filter:
        raise LdapConfigurationError("LDAP search filter must contain {username}")

    return LdapConfiguration(
        server=server,
        port=port,
        bind_dn=str(data["LDAP_BIND_DN"]).strip(),
        bind_password=str(data["LDAP_BIND_PASSWORD"]),
        user_search_base=str(data["LDAP_USER_SEARCH_BASE"]).strip(),
        user_search_filter=search_filter,
        email_attribute=str(data["LDAP_EMAIL_ATTRIBUTE"]).strip(),
        first_name_attribute=str(data["LDAP_FIRST_NAME_ATTRIBUTE"] or "givenName").strip(),
        last_name_attribute=str(data["LDAP_LAST_NAME_ATTRIBUTE"] or "sn").strip(),
        ca_certificate=str(data["LDAP_CA_CERTIFICATE"] or "").strip(),
    )


class ActiveDirectoryClient:
    def __init__(self, configuration):
        self.configuration = configuration
        tls_options = {
            "validate": ssl.CERT_REQUIRED,
            "version": ssl.PROTOCOL_TLS_CLIENT,
        }
        if configuration.ca_certificate:
            tls_options["ca_certs_data"] = configuration.ca_certificate
        self.server = Server(
            configuration.server,
            port=configuration.port,
            use_ssl=True,
            tls=Tls(**tls_options),
            connect_timeout=5,
            get_info=NONE,
        )

    def _connection(self, user, password):
        try:
            connection = Connection(
                self.server,
                user=user,
                password=password,
                raise_exceptions=True,
                receive_timeout=5,
            )
            if not connection.bind():
                raise LdapInvalidCredentials
            return connection
        except LDAPBindError as exc:
            raise LdapInvalidCredentials from exc
        except (LDAPSocketOpenError, LDAPException, OSError, ssl.SSLError) as exc:
            raise LdapConnectionError from exc

    def test_connection(self):
        connection = self._connection(self.configuration.bind_dn, self.configuration.bind_password)
        try:
            connection.search(
                search_base=self.configuration.user_search_base,
                search_filter="(objectClass=*)",
                attributes=["distinguishedName"],
                size_limit=1,
            )
        except LDAPException as exc:
            raise LdapConnectionError from exc
        finally:
            connection.unbind()

    def authenticate(self, username, password):
        if not username or not password:
            raise LdapInvalidCredentials

        service_connection = self._connection(self.configuration.bind_dn, self.configuration.bind_password)
        try:
            search_filter = self.configuration.user_search_filter.replace(
                "{username}", escape_filter_chars(username.strip())
            )
            attributes = list(
                dict.fromkeys(
                    [
                        "objectGUID",
                        self.configuration.email_attribute,
                        self.configuration.first_name_attribute,
                        self.configuration.last_name_attribute,
                    ]
                )
            )
            service_connection.search(
                search_base=self.configuration.user_search_base,
                search_filter=search_filter,
                attributes=attributes,
                size_limit=2,
            )
            if len(service_connection.entries) != 1:
                raise LdapUserNotFound
            entry = service_connection.entries[0]
            user = self._entry_to_user(entry)
        except LdapUserNotFound:
            raise
        except LDAPException as exc:
            raise LdapConnectionError from exc
        finally:
            service_connection.unbind()

        user_connection = self._connection(user.dn, password)
        user_connection.unbind()
        return user

    def _entry_to_user(self, entry):
        def attribute_value(name):
            if not name or name not in entry.entry_attributes:
                return ""
            return entry[name].value or ""

        guid_value = attribute_value("objectGUID")
        if isinstance(guid_value, (bytes, bytearray)):
            provider_id = str(uuid.UUID(bytes_le=bytes(guid_value)))
        else:
            provider_id = str(guid_value).strip()

        email = str(attribute_value(self.configuration.email_attribute)).strip().lower()
        if not provider_id or not email:
            raise LdapUserDataError

        return LdapUser(
            provider_id=provider_id,
            dn=entry.entry_dn,
            email=email,
            first_name=str(attribute_value(self.configuration.first_name_attribute)).strip(),
            last_name=str(attribute_value(self.configuration.last_name_attribute)).strip(),
        )
