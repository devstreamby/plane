/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/** Payload attached to a dragged state chip. */
export type TStateDragData = {
  dragType: "BOARD_COLUMN_STATE";
  stateId: string;
  sourceColumnId: string | undefined;
};

/** Payload attached to a dragged column. */
export type TColumnDragData = {
  dragType: "BOARD_COLUMN";
  columnId: string;
};

export const isStateDragData = (data: Record<string, unknown>): data is TStateDragData =>
  data.dragType === "BOARD_COLUMN_STATE";

export const isColumnDragData = (data: Record<string, unknown>): data is TColumnDragData =>
  data.dragType === "BOARD_COLUMN";
