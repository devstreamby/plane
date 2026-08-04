/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useState } from "react";
import { useParams } from "next/navigation";
import type { TIssueGroupByOptions } from "@plane/types";
import { useProjectState } from "@/hooks/store/use-project-state";

/**
 * Workflow enforcement for board/list drag-and-drop. Only active when work items
 * are grouped (or sub-grouped) by state or by board column; a no-op for every
 * other grouping axis.
 */
export const useWorkFlowFDragNDrop = (groupBy: TIssueGroupByOptions | undefined, subGroupBy?: TIssueGroupByOptions) => {
  const { projectId } = useParams();
  const { getIsTransitionAllowed, getProjectBoardColumns, getTargetStateIdForColumn } = useProjectState();

  const [dragSourceGroupId, setDragSourceGroupId] = useState<string | undefined>(undefined);
  const [dragDestinationGroupId, setDragDestinationGroupId] = useState<string | undefined>(undefined);

  const workflowAxis = groupBy === "state" || groupBy === "board_column" ? groupBy : undefined;
  const workflowSubGroupAxis = subGroupBy === "state" || subGroupBy === "board_column" ? subGroupBy : undefined;
  // Whichever axis carries states decides which group ids to look at.
  const activeAxis = workflowAxis ?? workflowSubGroupAxis;

  const handleWorkFlowState = useCallback(
    (sourceGroupId: string, destinationGroupId: string, sourceSubGroupId?: string, destinationSubGroupId?: string) => {
      if (!activeAxis) return;
      setDragSourceGroupId(workflowAxis ? sourceGroupId : sourceSubGroupId);
      setDragDestinationGroupId(workflowAxis ? destinationGroupId : destinationSubGroupId);
    },
    [activeAxis, workflowAxis]
  );

  const getIsDropDisabled = () => {
    if (!activeAxis || !dragSourceGroupId || !dragDestinationGroupId) return false;
    const currentProjectId = projectId?.toString();

    if (activeAxis === "state") {
      return !getIsTransitionAllowed(currentProjectId, dragSourceGroupId, dragDestinationGroupId);
    }

    // Board columns hold one or more states and the dragged item's own state is not known here,
    // so the drop stays open while any state of the source column can reach the target state.
    // The API rejects the move if the item's actual state cannot.
    const targetStateId = getTargetStateIdForColumn(currentProjectId, dragDestinationGroupId);
    if (!targetStateId) return false;
    const sourceStateIds =
      getProjectBoardColumns(currentProjectId).find((column) => column.id === dragSourceGroupId)?.state_ids ?? [];
    if (sourceStateIds.length === 0) return false;
    return !sourceStateIds.some((stateId) => getIsTransitionAllowed(currentProjectId, stateId, targetStateId));
  };

  const isWorkflowDropDisabled = getIsDropDisabled();

  return {
    workflowDisabledSource: isWorkflowDropDisabled ? dragSourceGroupId : undefined,
    isWorkflowDropDisabled,
    // Work item creation may target any state in phase 1.
    getIsWorkflowWorkItemCreationDisabled: (_groupId: string, _subGroupId?: string) => false,
    handleWorkFlowState,
  };
};
