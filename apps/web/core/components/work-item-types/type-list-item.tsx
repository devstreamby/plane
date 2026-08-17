/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { PencilIcon, Trash2Icon } from "lucide-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Logo } from "@plane/propel/emoji-icon-picker";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { TIssueType } from "@plane/types";
import { ToggleSwitch, Tooltip } from "@plane/ui";
// hooks
import { useIssueType } from "@/hooks/store/use-issue-type";

type Props = {
  workspaceSlug: string;
  projectId: string;
  issueType: TIssueType;
  isEditable: boolean;
  onEdit: (issueType: TIssueType) => void;
  onDeleteAttempt: (issueType: TIssueType) => void;
};

export const WorkItemTypeListItem = observer(function WorkItemTypeListItem(props: Props) {
  const { workspaceSlug, projectId, issueType, isEditable, onEdit, onDeleteAttempt } = props;
  const { t } = useTranslation();
  const { updateIssueType, markAsDefault } = useIssueType();

  const handleToggleActive = async (value: boolean) => {
    try {
      await updateIssueType(workspaceSlug, projectId, issueType.id, { is_active: value });
    } catch (error: any) {
      setToast({ type: TOAST_TYPE.ERROR, title: t("common.error.label"), message: error?.error });
    }
  };

  const handleSetDefault = async () => {
    if (!issueType.is_active) return;
    try {
      await markAsDefault(workspaceSlug, projectId, issueType.id);
    } catch (error: any) {
      setToast({ type: TOAST_TYPE.ERROR, title: t("common.error.label"), message: error?.error });
    }
  };

  return (
    <div className="flex items-center gap-3 rounded-sm border border-subtle px-3 py-2.5">
      <Logo logo={issueType.logo_props} size={18} />
      <div className="min-w-0 flex-grow">
        <div className="flex items-center gap-2">
          <span className="truncate text-body-sm-medium text-primary">{issueType.name}</span>
          {issueType.is_default && (
            <span className="rounded-sm bg-layer-2 px-1.5 py-0.5 text-caption-sm-medium text-tertiary">
              {t("common.default")}
            </span>
          )}
        </div>
        {issueType.description && <p className="text-body-xs truncate text-tertiary">{issueType.description}</p>}
      </div>

      {isEditable && !issueType.is_default && (
        <Tooltip
          tooltipContent={
            issueType.is_active
              ? t("work_item_types.settings.set_as_default")
              : t("work_item_types.settings.cant_set_default_inactive_message")
          }
        >
          <button
            type="button"
            onClick={handleSetDefault}
            disabled={!issueType.is_active}
            className="rounded-sm px-2 py-1 text-body-xs-medium text-tertiary hover:bg-layer-transparent-hover hover:text-secondary disabled:cursor-not-allowed disabled:opacity-50"
          >
            {t("work_item_types.settings.set_as_default")}
          </button>
        </Tooltip>
      )}

      {isEditable && <ToggleSwitch value={issueType.is_active} onChange={handleToggleActive} size="sm" />}

      {isEditable && (
        <div className="flex items-center gap-1">
          <button
            type="button"
            aria-label={t("edit")}
            onClick={() => onEdit(issueType)}
            className="rounded-sm p-1.5 text-tertiary hover:bg-layer-transparent-hover hover:text-secondary"
          >
            <PencilIcon className="size-3.5" />
          </button>
          <Tooltip
            tooltipContent={issueType.is_default ? t("work_item_types.settings.cant_delete_default_message") : ""}
            disabled={!issueType.is_default}
          >
            <button
              type="button"
              aria-label={t("delete")}
              onClick={() => onDeleteAttempt(issueType)}
              disabled={issueType.is_default}
              className="rounded-sm p-1.5 text-tertiary hover:bg-layer-transparent-hover hover:text-danger-primary disabled:cursor-not-allowed disabled:opacity-40"
            >
              <Trash2Icon className="size-3.5" />
            </button>
          </Tooltip>
        </div>
      )}
    </div>
  );
});
