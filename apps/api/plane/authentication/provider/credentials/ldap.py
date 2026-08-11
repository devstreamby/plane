# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import os

from django.db import IntegrityError
from django.utils import timezone

from plane.authentication.adapter.credential import CredentialAdapter
from plane.authentication.adapter.error import AUTHENTICATION_ERROR_CODES, AuthenticationException
from plane.authentication.ldap import (
    ActiveDirectoryClient,
    LdapConfigurationError,
    LdapConnectionError,
    LdapInvalidCredentials,
    LdapUserDataError,
    LdapUserNotFound,
    get_ldap_configuration,
)
from plane.db.models import Account, User
from plane.license.utils.instance_value import get_configuration_value


class LdapProvider(CredentialAdapter):
    provider = "ldap"

    def __init__(self, request, username, password, callback=None):
        super().__init__(request=request, provider=self.provider, callback=callback)
        self.username = username
        self.code = password
        self.directory_user = None

        (IS_LDAP_ENABLED,) = get_configuration_value(
            [{"key": "IS_LDAP_ENABLED", "default": os.environ.get("IS_LDAP_ENABLED", "0")}]
        )
        if IS_LDAP_ENABLED != "1":
            raise AuthenticationException(
                error_code=AUTHENTICATION_ERROR_CODES["LDAP_NOT_CONFIGURED"],
                error_message="LDAP_NOT_CONFIGURED",
            )

    def authenticate(self):
        try:
            client = ActiveDirectoryClient(get_ldap_configuration())
            self.directory_user = client.authenticate(self.username, self.code)
        except LdapConfigurationError as exc:
            self.logger.warning("Active Directory authentication is not configured")
            raise AuthenticationException(
                error_code=AUTHENTICATION_ERROR_CODES["LDAP_NOT_CONFIGURED"],
                error_message="LDAP_NOT_CONFIGURED",
            ) from exc
        except (LdapInvalidCredentials, LdapUserNotFound) as exc:
            self.logger.warning("Active Directory authentication failed")
            raise AuthenticationException(
                error_code=AUTHENTICATION_ERROR_CODES["LDAP_INVALID_CREDENTIALS"],
                error_message="LDAP_INVALID_CREDENTIALS",
            ) from exc
        except LdapConnectionError as exc:
            self.logger.exception("Could not connect to Active Directory")
            raise AuthenticationException(
                error_code=AUTHENTICATION_ERROR_CODES["LDAP_CONNECTION_ERROR"],
                error_message="LDAP_CONNECTION_ERROR",
            ) from exc
        except LdapUserDataError as exc:
            self.logger.warning("Active Directory user has no stable ID or email")
            raise AuthenticationException(
                error_code=AUTHENTICATION_ERROR_CODES["LDAP_USER_DATA_INVALID"],
                error_message="LDAP_USER_DATA_INVALID",
            ) from exc

        self._link_existing_account()
        self.set_user_data()
        self.set_token_data({"provider_account_id": self.directory_user.provider_id})
        return self.complete_login_or_signup()

    def _link_existing_account(self):
        account = (
            Account.objects.filter(
                provider=self.provider,
                provider_account_id=self.directory_user.provider_id,
            )
            .select_related("user")
            .first()
        )
        if not account:
            return

        user = account.user
        directory_email = self.directory_user.email
        if user.email != directory_email:
            if User.objects.filter(email=directory_email).exclude(pk=user.pk).exists():
                raise AuthenticationException(
                    error_code=AUTHENTICATION_ERROR_CODES["LDAP_USER_DATA_INVALID"],
                    error_message="LDAP_USER_DATA_INVALID",
                )
            user.email = directory_email
            user.save(update_fields=["email", "updated_at"])

    def set_user_data(self):
        super().set_user_data(
            {
                "email": self.directory_user.email,
                "user": {
                    "avatar": "",
                    "first_name": self.directory_user.first_name,
                    "last_name": self.directory_user.last_name,
                    "provider_id": self.directory_user.provider_id,
                    "is_password_autoset": True,
                },
            }
        )

    def create_update_account(self, user):
        try:
            Account.objects.update_or_create(
                provider=self.provider,
                provider_account_id=self.directory_user.provider_id,
                defaults={
                    "user": user,
                    "access_token": "",
                    "last_connected_at": timezone.now(),
                    "metadata": {"dn": self.directory_user.dn},
                },
            )
        except IntegrityError as exc:
            self.logger.exception("Could not link Active Directory account")
            raise AuthenticationException(
                error_code=AUTHENTICATION_ERROR_CODES["LDAP_USER_DATA_INVALID"],
                error_message="LDAP_USER_DATA_INVALID",
            ) from exc
