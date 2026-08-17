/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import useSWR from "swr";
import { PlusIcon } from "lucide-react";
// plane imports
import { PROJECT_ISSUE_TYPES } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { EmptyStateCompact } from "@plane/propel/empty-state";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { TIssueType } from "@plane/types";
import { AlertModalCore, Loader } from "@plane/ui";
// hooks
import { useIssueType } from "@/hooks/store/use-issue-type";
import { useProject } from "@/hooks/store/use-project";
// local imports
import { CreateUpdateWorkItemTypeModal } from "./create-update-modal";
import { WorkItemTypeListItem } from "./type-list-item";

type Props = {
  workspaceSlug: string;
  projectId: string;
  isEditable: boolean;
};

export const WorkItemTypesRoot = observer(function WorkItemTypesRoot(props: Props) {
  const { workspaceSlug, projectId, isEditable } = props;
  const { t } = useTranslation();
  const { currentProjectDetails, updateProject } = useProject();
  const { fetchProjectIssueTypes, getProjectIssueTypes, deleteIssueType, fetchedMap } = useIssueType();

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [typeToEdit, setTypeToEdit] = useState<TIssueType | undefined>(undefined);
  const [typeToDelete, setTypeToDelete] = useState<TIssueType | undefined>(undefined);
  const [isEnabling, setIsEnabling] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const isEnabled = !!currentProjectDetails?.is_issue_type_enabled;

  useSWR(
    isEnabled ? PROJECT_ISSUE_TYPES(projectId, undefined) : null,
    isEnabled ? () => fetchProjectIssueTypes(workspaceSlug, projectId) : null,
    { revalidateIfStale: false, revalidateOnFocus: false }
  );

  const issueTypes = getProjectIssueTypes(projectId);

  const handleEnable = async () => {
    setIsEnabling(true);
    try {
      await updateProject(workspaceSlug, projectId, { is_issue_type_enabled: true });
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: t("common.error.label"), message: t("common.error.message") });
    } finally {
      setIsEnabling(false);
    }
  };

  const handleDelete = async () => {
    if (!typeToDelete) return;
    setIsDeleting(true);
    try {
      await deleteIssueType(workspaceSlug, projectId, typeToDelete.id);
      setTypeToDelete(undefined);
    } catch (error: any) {
      setToast({ type: TOAST_TYPE.ERROR, title: t("common.error.label"), message: error?.error });
    } finally {
      setIsDeleting(false);
    }
  };

  if (!isEnabled) {
    return (
      <EmptyStateCompact
        assetKey="work-item"
        assetClassName="size-20"
        title={t("settings_empty_state.work_item_types.title")}
        description={t("settings_empty_state.work_item_types.description")}
        actions={
          isEditable
            ? [
                {
                  label: t("settings_empty_state.work_item_types.cta_primary"),
                  onClick: handleEnable,
                  disabled: isEnabling,
                },
              ]
            : []
        }
        align="start"
        rootClassName="py-16"
      />
    );
  }

  if (isEnabled && !fetchedMap[projectId]) {
    return (
      <Loader className="space-y-3">
        <Loader.Item height="52px" />
        <Loader.Item height="52px" />
        <Loader.Item height="52px" />
      </Loader>
    );
  }

  return (
    <div className="space-y-3">
      {issueTypes.map((issueType) => (
        <WorkItemTypeListItem
          key={issueType.id}
          workspaceSlug={workspaceSlug}
          projectId={projectId}
          issueType={issueType}
          isEditable={isEditable}
          onEdit={(type) => {
            setTypeToEdit(type);
            setIsModalOpen(true);
          }}
          onDeleteAttempt={setTypeToDelete}
        />
      ))}

      {isEditable && (
        <Button
          variant="secondary"
          size="sm"
          prependIcon={<PlusIcon className="size-3.5" />}
          onClick={() => {
            setTypeToEdit(undefined);
            setIsModalOpen(true);
          }}
        >
          {t("add")}
        </Button>
      )}

      <CreateUpdateWorkItemTypeModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        workspaceSlug={workspaceSlug}
        projectId={projectId}
        issueTypeToUpdate={typeToEdit}
      />

      <AlertModalCore
        isOpen={!!typeToDelete}
        handleClose={() => setTypeToDelete(undefined)}
        handleSubmit={handleDelete}
        isSubmitting={isDeleting}
        title={t("delete")}
        content={
          <>
            {t("delete")} <span className="font-medium text-primary">{typeToDelete?.name}</span>?
          </>
        }
      />
    </div>
  );
});
