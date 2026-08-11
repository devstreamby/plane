# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.http import HttpResponseRedirect
from django.views import View

from plane.authentication.adapter.error import AUTHENTICATION_ERROR_CODES, AuthenticationException
from plane.authentication.provider.credentials.ldap import LdapProvider
from plane.authentication.rate_limit import authentication_throttle_allows
from plane.authentication.utils.host import base_host
from plane.authentication.utils.login import user_login
from plane.authentication.utils.redirection_path import get_redirection_path
from plane.authentication.utils.user_auth_workflow import post_user_auth_workflow
from plane.license.models import Instance
from plane.utils.path_validator import get_safe_redirect_url


class LdapSignInEndpoint(View):
    def _redirect(self, request, next_path, params):
        return HttpResponseRedirect(
            get_safe_redirect_url(
                base_url=base_host(request=request, is_app=True),
                next_path=next_path,
                params=params,
            )
        )

    def post(self, request):
        next_path = request.POST.get("next_path")
        instance = Instance.objects.first()
        if instance is None or not instance.is_setup_done:
            exc = AuthenticationException(
                error_code=AUTHENTICATION_ERROR_CODES["INSTANCE_NOT_CONFIGURED"],
                error_message="INSTANCE_NOT_CONFIGURED",
            )
            return self._redirect(request, next_path, {**exc.get_error_dict(), "auth_method": "ldap"})

        if not authentication_throttle_allows(request):
            exc = AuthenticationException(
                error_code=AUTHENTICATION_ERROR_CODES["RATE_LIMIT_EXCEEDED"],
                error_message="RATE_LIMIT_EXCEEDED",
            )
            return self._redirect(request, next_path, {**exc.get_error_dict(), "auth_method": "ldap"})

        username = str(request.POST.get("username", "")).strip()
        password = str(request.POST.get("password", ""))
        if not username or not password:
            exc = AuthenticationException(
                error_code=AUTHENTICATION_ERROR_CODES["LDAP_INVALID_CREDENTIALS"],
                error_message="LDAP_INVALID_CREDENTIALS",
            )
            return self._redirect(request, next_path, {**exc.get_error_dict(), "auth_method": "ldap"})

        try:
            provider = LdapProvider(
                request=request,
                username=username,
                password=password,
                callback=post_user_auth_workflow,
            )
            user = provider.authenticate()
            user_login(request=request, user=user, is_app=True)
            path = next_path or get_redirection_path(user=user)
            return self._redirect(request, path, {})
        except AuthenticationException as exc:
            return self._redirect(request, next_path, {**exc.get_error_dict(), "auth_method": "ldap"})
