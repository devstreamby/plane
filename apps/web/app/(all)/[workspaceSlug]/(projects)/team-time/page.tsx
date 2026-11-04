/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { PageHead } from "@/components/core/page-title";
import { TimeCalendarRoot } from "@/components/time-calendar";
import { useWorkspace } from "@/hooks/store/use-workspace";
import { useUserPermissions } from "@/hooks/store/user";
import type { Route } from "./+types/page";

function TeamTimePage({ params }: Route.ComponentProps) {
  const { workspaceSlug } = params;
  const { t } = useTranslation();
  const { currentWorkspace } = useWorkspace();
  const { allowPermissions } = useUserPermissions();

  const pageTitle = currentWorkspace?.name
    ? t("time_calendar.page_label", { workspace: currentWorkspace.name })
    : undefined;

  const canView = allowPermissions([EUserPermissions.ADMIN, EUserPermissions.MEMBER], EUserPermissionsLevel.WORKSPACE);

  if (!canView) {
    return (
      <div className="flex h-full w-full items-center justify-center text-13 text-tertiary">
        {t("time_calendar.forbidden")}
      </div>
    );
  }

  return (
    <>
      <PageHead title={pageTitle} />
      <TimeCalendarRoot workspaceSlug={workspaceSlug} mode="team" />
    </>
  );
}

export default observer(TeamTimePage);
