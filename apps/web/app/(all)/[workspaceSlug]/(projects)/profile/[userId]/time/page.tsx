/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { PageHead } from "@/components/core/page-title";
import { TimeCalendarRoot } from "@/components/time-calendar";
import { useWorkspace } from "@/hooks/store/use-workspace";
import { useUser, useUserPermissions } from "@/hooks/store/user";
import type { Route } from "./+types/page";

function ProfileTimePage({ params }: Route.ComponentProps) {
  const { workspaceSlug, userId } = params;
  const { t } = useTranslation();
  const { currentWorkspace } = useWorkspace();
  const { data: currentUser } = useUser();
  const { allowPermissions } = useUserPermissions();
  const canView = allowPermissions([EUserPermissions.ADMIN, EUserPermissions.MEMBER], EUserPermissionsLevel.WORKSPACE);
  const isOwnProfile = currentUser?.id === userId;

  const pageTitle = currentWorkspace?.name ? `${currentWorkspace.name} - ${t("profile.tabs.time")}` : undefined;

  if (!canView || !isOwnProfile) {
    return (
      <div className="grid h-full w-full place-items-center text-13 text-tertiary">
        {t("you_do_not_have_the_permission_to_access_this_page")}
      </div>
    );
  }

  return (
    <>
      <PageHead title={pageTitle} />
      <TimeCalendarRoot workspaceSlug={workspaceSlug} mode="self" />
    </>
  );
}

export default ProfileTimePage;
