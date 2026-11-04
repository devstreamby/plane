/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { PROFILE_ADMINS_TAB, PROFILE_TIME_TAB, PROFILE_VIEWER_TAB } from "@plane/constants";

/** Time is only on your own profile, and only for workspace members. */
export function getProfileTabs(isAuthorized: boolean, isOwnProfile: boolean) {
  return [
    ...PROFILE_VIEWER_TAB,
    ...(isAuthorized && isOwnProfile ? [PROFILE_TIME_TAB] : []),
    ...(isAuthorized ? PROFILE_ADMINS_TAB : []),
  ];
}
