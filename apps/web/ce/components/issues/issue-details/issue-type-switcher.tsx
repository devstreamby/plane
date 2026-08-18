/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useTranslation } from "@plane/i18n";
import { Logo } from "@plane/propel/emoji-icon-picker";
import { setToast, TOAST_TYPE } from "@plane/propel/toast";
import { Tooltip } from "@plane/propel/tooltip";
import { CustomSearchSelect } from "@plane/ui";
import { cn } from "@plane/utils";
import { observer } from "mobx-react";
// store hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useIssueType } from "@/hooks/store/use-issue-type";
import { useProject } from "@/hooks/store/use-project";
import { useRouterParams } from "@/hooks/store/use-router-params";
// components
import { IdentifierText } from "@/components/issues/issue-detail/identifier-text";
// plane web components
import { IssueIdentifier } from "@/plane-web/components/issues/issue-details/issue-identifier";

export type TIssueTypeSwitcherProps = {
  issueId: string;
  disabled: boolean;
};

export const IssueTypeSwitcher = observer(function IssueTypeSwitcher(props: TIssueTypeSwitcherProps) {
  const { issueId, disabled } = props;
  const { t } = useTranslation();
  // store hooks
  const {
    issue: { getIssueById },
    updateIssue,
  } = useIssueDetail();
  const { getProjectIssueTypes, getIssueTypeById } = useIssueType();
  const { getProjectIdentifierById } = useProject();
  const { workspaceSlug } = useRouterParams();
  // derived values
  const issue = getIssueById(issueId);
  const projectId = issue?.project_id;
  const issueTypes = getProjectIssueTypes(projectId).filter((type) => type.is_active);

  if (!issue || !projectId) return <></>;

  if (disabled || issueTypes.length === 0) {
    return <IssueIdentifier issueId={issueId} projectId={projectId} size="md" enableClickToCopyIdentifier />;
  }

  const selectedType = getIssueTypeById(projectId, issue.type_id);
  const options = issueTypes.map((type) => ({
    value: type.id,
    query: type.name,
    content: (
      <div className="flex items-center gap-2">
        <Logo logo={type.logo_props} size={14} />
        <span className="truncate">{type.name}</span>
      </div>
    ),
  }));

  const handleTypeChange = async (typeId: string) => {
    if (!workspaceSlug || typeId === issue.type_id) return;
    try {
      await updateIssue(workspaceSlug, projectId, issueId, { type_id: typeId });
    } catch {
      setToast({
        title: t("common.error.label"),
        type: TOAST_TYPE.ERROR,
        message: t("entity.update.failed", { entity: t("issue.label") }),
      });
    }
  };

  return (
    <div className="flex shrink-0 items-center gap-2">
      <CustomSearchSelect
        value={issue.type_id}
        onChange={handleTypeChange}
        options={options}
        customButton={
          <Tooltip tooltipContent={t("work_item_types.switcher.tooltip")} position="top">
            <button
              type="button"
              className={cn("flex items-center justify-center rounded-sm p-0.5 hover:bg-layer-2 focus:outline-none")}
            >
              {selectedType ? <Logo logo={selectedType.logo_props} size={14} /> : <span className="h-3.5 w-3.5" />}
            </button>
          </Tooltip>
        }
      />
      <IdentifierText
        identifier={`${getProjectIdentifierById(projectId)}-${issue.sequence_id}`}
        enableClickToCopyIdentifier
        size="md"
      />
    </div>
  );
});
