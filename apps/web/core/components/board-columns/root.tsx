/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useState } from "react";
import { observer } from "mobx-react";
import useSWR from "swr";
import { PlusIcon } from "lucide-react";
// plane imports
import { STATE_GROUPS } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { IState, TBoardColumn } from "@plane/types";
import { AlertModalCore, Loader } from "@plane/ui";
// hooks
import { useProjectState } from "@/hooks/store/use-project-state";
// local imports
import { BoardColumnCard } from "./column-card";
import type { TStateDragData } from "./types";
import { BoardColumnsUnmappedStates } from "./unmapped-states";

type TBoardColumnsRootProps = {
  workspaceSlug: string;
  projectId: string;
  isEditable: boolean;
};

/** Sequence for a column dropped between two neighbours. */
const getSequenceBetween = (previous: number | undefined, next: number | undefined) => {
  if (previous === undefined && next === undefined) return 65535;
  if (previous === undefined) return (next as number) - 15000;
  if (next === undefined) return previous + 15000;
  return (previous + next) / 2;
};

export const BoardColumnsRoot = observer(function BoardColumnsRoot(props: TBoardColumnsRootProps) {
  const { workspaceSlug, projectId, isEditable } = props;
  // hooks
  const { t } = useTranslation();
  const {
    fetchProjectStates,
    fetchBoardColumns,
    getProjectStates,
    getProjectBoardColumns,
    boardColumnsFetchedMap,
    createBoardColumn,
    updateBoardColumn,
    deleteBoardColumn,
  } = useProjectState();
  // states
  const [columnToDelete, setColumnToDelete] = useState<TBoardColumn | undefined>(undefined);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useSWR(
    workspaceSlug && projectId ? `PROJECT_BOARD_COLUMN_STATES_${workspaceSlug}_${projectId}` : null,
    workspaceSlug && projectId ? () => fetchProjectStates(workspaceSlug, projectId) : null,
    { revalidateIfStale: false, revalidateOnFocus: false }
  );
  useSWR(
    workspaceSlug && projectId ? `PROJECT_BOARD_COLUMNS_SETTINGS_${workspaceSlug}_${projectId}` : null,
    workspaceSlug && projectId ? () => fetchBoardColumns(workspaceSlug, projectId) : null,
    { revalidateIfStale: false, revalidateOnFocus: false }
  );

  // derived values
  const projectStates = getProjectStates(projectId);
  const columns = getProjectBoardColumns(projectId);
  const isLoading = !projectStates || !boardColumnsFetchedMap[projectId];
  const mappedStateIds = new Set(columns.flatMap((column) => column.state_ids));
  const unmappedStates = (projectStates ?? []).filter((state) => !mappedStateIds.has(state.id));

  const getColumnStates = (column: TBoardColumn): IState[] =>
    column.state_ids
      .map((stateId) => projectStates?.find((state) => state.id === stateId))
      .filter((state): state is IState => !!state);

  const showError = useCallback(
    (message: string) => setToast({ type: TOAST_TYPE.ERROR, title: t("common.error.label"), message }),
    [t]
  );

  const handleStateDroppedOnColumn = useCallback(
    async (data: TStateDragData, targetColumnId: string) => {
      const targetColumn = getProjectBoardColumns(projectId).find((column) => column.id === targetColumnId);
      if (!targetColumn) return;
      try {
        // A state belongs to a single column, so adding it here also takes it out of its old one.
        await updateBoardColumn(workspaceSlug, projectId, targetColumnId, {
          state_ids: [...targetColumn.state_ids, data.stateId],
        });
      } catch {
        showError(t("project_settings.board_columns.toasts.move_state_error"));
      }
    },
    [getProjectBoardColumns, projectId, showError, t, updateBoardColumn, workspaceSlug]
  );

  const handleStateDroppedOnTray = useCallback(
    async (data: TStateDragData) => {
      const sourceColumn = getProjectBoardColumns(projectId).find((column) => column.id === data.sourceColumnId);
      if (!sourceColumn) return;
      try {
        await updateBoardColumn(workspaceSlug, projectId, sourceColumn.id, {
          state_ids: sourceColumn.state_ids.filter((stateId) => stateId !== data.stateId),
        });
      } catch {
        showError(t("project_settings.board_columns.toasts.move_state_error"));
      }
    },
    [getProjectBoardColumns, projectId, showError, t, updateBoardColumn, workspaceSlug]
  );

  const handleColumnDropped = useCallback(
    async (columnId: string, targetColumnId: string, edge: "left" | "right") => {
      const ordered = getProjectBoardColumns(projectId);
      const targetIndex = ordered.findIndex((column) => column.id === targetColumnId);
      if (targetIndex === -1) return;
      // Insert before or after the column that was dropped on, ignoring the dragged column itself.
      const withoutDragged = ordered.filter((column) => column.id !== columnId);
      const insertAt = withoutDragged.findIndex((column) => column.id === targetColumnId) + (edge === "left" ? 0 : 1);
      const sequence = getSequenceBetween(withoutDragged[insertAt - 1]?.sequence, withoutDragged[insertAt]?.sequence);
      try {
        await updateBoardColumn(workspaceSlug, projectId, columnId, { sequence });
      } catch {
        showError(t("project_settings.board_columns.toasts.reorder_error"));
      }
    },
    [getProjectBoardColumns, projectId, showError, t, updateBoardColumn, workspaceSlug]
  );

  const handleRename = useCallback(
    async (columnId: string, name: string) => {
      try {
        await updateBoardColumn(workspaceSlug, projectId, columnId, { name });
      } catch {
        showError(t("project_settings.board_columns.toasts.rename_error"));
      }
    },
    [projectId, showError, t, updateBoardColumn, workspaceSlug]
  );

  const handleCreate = async () => {
    setIsSubmitting(true);
    try {
      await createBoardColumn(workspaceSlug, projectId, {
        name: t("project_settings.board_columns.new_column_name", { count: columns.length + 1 }),
      });
    } catch {
      showError(t("project_settings.board_columns.toasts.create_error"));
    } finally {
      setIsSubmitting(false);
    }
  };

  /** One column per state group that actually has states, in the groups' own order. */
  const handleCreateDefaults = async () => {
    if (!projectStates) return;
    setIsSubmitting(true);
    try {
      for (const group of Object.values(STATE_GROUPS)) {
        const groupStates = projectStates.filter((state) => state.group === group.key);
        if (groupStates.length === 0) continue;
        // Sequential on purpose: each new column takes its sequence from the last one,
        // so creating them in parallel would leave the order up to chance.
        // eslint-disable-next-line no-await-in-loop
        await createBoardColumn(workspaceSlug, projectId, {
          name: group.label,
          state_ids: groupStates.map((state) => state.id),
        });
      }
      await fetchBoardColumns(workspaceSlug, projectId);
    } catch {
      showError(t("project_settings.board_columns.toasts.create_error"));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!columnToDelete) return;
    setIsSubmitting(true);
    try {
      await deleteBoardColumn(workspaceSlug, projectId, columnToDelete.id);
      setColumnToDelete(undefined);
    } catch {
      showError(t("project_settings.board_columns.toasts.delete_error"));
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <Loader className="space-y-4">
        <Loader.Item height="180px" />
        <Loader.Item height="80px" />
      </Loader>
    );
  }

  return (
    <div className="space-y-4">
      {columns.length === 0 ? (
        <div className="flex flex-col items-center gap-3 rounded-sm border border-dashed border-subtle p-8 text-center">
          <p className="text-13 text-secondary">{t("project_settings.board_columns.empty.description")}</p>
          {isEditable && (
            <div className="flex items-center gap-2">
              <Button variant="primary" size="sm" onClick={handleCreateDefaults} loading={isSubmitting}>
                {t("project_settings.board_columns.empty.create_defaults")}
              </Button>
              <Button variant="secondary" size="sm" onClick={handleCreate} loading={isSubmitting}>
                {t("project_settings.board_columns.add_column")}
              </Button>
            </div>
          )}
        </div>
      ) : (
        <div className="horizontal-scrollbar flex scrollbar-sm items-stretch gap-3 overflow-x-auto pb-2">
          {columns.map((column) => (
            <BoardColumnCard
              key={column.id}
              column={column}
              states={getColumnStates(column)}
              isEditable={isEditable}
              onRename={handleRename}
              onDelete={setColumnToDelete}
              onStateDropped={handleStateDroppedOnColumn}
              onColumnDropped={handleColumnDropped}
            />
          ))}
          {isEditable && (
            <button
              type="button"
              onClick={handleCreate}
              disabled={isSubmitting}
              className="flex w-40 flex-shrink-0 items-center justify-center gap-1.5 rounded-sm border border-dashed border-subtle text-13 text-tertiary hover:border-strong hover:text-secondary"
            >
              <PlusIcon className="size-4" />
              {t("project_settings.board_columns.add_column")}
            </button>
          )}
        </div>
      )}

      <BoardColumnsUnmappedStates
        states={unmappedStates}
        isEditable={isEditable}
        onStateDropped={handleStateDroppedOnTray}
      />

      <AlertModalCore
        isOpen={!!columnToDelete}
        handleClose={() => setColumnToDelete(undefined)}
        handleSubmit={handleDelete}
        isSubmitting={isSubmitting}
        title={t("project_settings.board_columns.delete_modal.title")}
        content={t("project_settings.board_columns.delete_modal.description", { name: columnToDelete?.name ?? "" })}
      />
    </div>
  );
});
