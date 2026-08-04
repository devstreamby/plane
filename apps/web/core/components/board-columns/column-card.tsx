/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useRef, useState } from "react";
import { combine } from "@atlaskit/pragmatic-drag-and-drop/combine";
import { draggable, dropTargetForElements } from "@atlaskit/pragmatic-drag-and-drop/element/adapter";
import { attachClosestEdge, extractClosestEdge } from "@atlaskit/pragmatic-drag-and-drop-hitbox/closest-edge";
import { observer } from "mobx-react";
import { GripVertical, Trash2 } from "lucide-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import type { IState, TBoardColumn } from "@plane/types";
import { Input, Tooltip } from "@plane/ui";
import { cn } from "@plane/utils";
// local imports
import { BoardColumnStateChip } from "./state-chip";
import type { TColumnDragData, TStateDragData } from "./types";
import { isColumnDragData, isStateDragData } from "./types";

type TBoardColumnCardProps = {
  column: TBoardColumn;
  states: IState[];
  isEditable: boolean;
  onRename: (columnId: string, name: string) => Promise<void>;
  onDelete: (column: TBoardColumn) => void;
  onStateDropped: (data: TStateDragData, targetColumnId: string) => Promise<void>;
  onColumnDropped: (columnId: string, targetColumnId: string, edge: "left" | "right") => Promise<void>;
};

export const BoardColumnCard = observer(function BoardColumnCard(props: TBoardColumnCardProps) {
  const { column, states, isEditable, onRename, onDelete, onStateDropped, onColumnDropped } = props;
  // refs
  const cardRef = useRef<HTMLDivElement | null>(null);
  const handleRef = useRef<HTMLDivElement | null>(null);
  // states
  const [name, setName] = useState(column.name);
  const [isDragging, setIsDragging] = useState(false);
  const [isStateDraggedOver, setIsStateDraggedOver] = useState(false);
  const [closestEdge, setClosestEdge] = useState<string | null>(null);
  // hooks
  const { t } = useTranslation();
  // derived values
  const entryState = states[0];

  useEffect(() => setName(column.name), [column.name]);

  useEffect(() => {
    const element = cardRef.current;
    const handle = handleRef.current;
    if (!element) return;

    return combine(
      ...(handle && isEditable
        ? [
            draggable({
              element,
              dragHandle: handle,
              getInitialData: (): TColumnDragData => ({ dragType: "BOARD_COLUMN", columnId: column.id }),
              onDragStart: () => setIsDragging(true),
              onDrop: () => setIsDragging(false),
            }),
          ]
        : []),
      dropTargetForElements({
        element,
        canDrop: ({ source }) =>
          isStateDragData(source.data) || (isColumnDragData(source.data) && source.data.columnId !== column.id),
        getData: ({ input }) =>
          attachClosestEdge({ columnId: column.id }, { element, input, allowedEdges: ["left", "right"] }),
        onDragEnter: ({ source, self }) => {
          if (isStateDragData(source.data)) setIsStateDraggedOver(true);
          else setClosestEdge(extractClosestEdge(self.data));
        },
        onDrag: ({ source, self }) => {
          if (!isStateDragData(source.data)) setClosestEdge(extractClosestEdge(self.data));
        },
        onDragLeave: () => {
          setIsStateDraggedOver(false);
          setClosestEdge(null);
        },
        onDrop: ({ source, self }) => {
          const edge = extractClosestEdge(self.data);
          setIsStateDraggedOver(false);
          setClosestEdge(null);
          if (isStateDragData(source.data)) {
            if (source.data.sourceColumnId === column.id) return;
            void onStateDropped(source.data, column.id);
          } else if (isColumnDragData(source.data) && (edge === "left" || edge === "right")) {
            void onColumnDropped(source.data.columnId, column.id, edge);
          }
        },
      })
    );
  }, [column.id, isEditable, onColumnDropped, onStateDropped]);

  const handleRenameSubmit = async () => {
    const trimmed = name.trim();
    if (!trimmed || trimmed === column.name) {
      setName(column.name);
      return;
    }
    await onRename(column.id, trimmed);
  };

  return (
    <div className="relative flex-shrink-0">
      {closestEdge === "left" && (
        <div className="absolute top-0 -left-1.5 z-1 h-full w-0.5 rounded-sm bg-accent-primary" />
      )}
      <div
        ref={cardRef}
        className={cn(
          "flex h-full w-64 flex-col gap-2 rounded-sm border border-subtle bg-surface-2 p-3 transition-all",
          isStateDraggedOver && "border-accent-strong bg-layer-2",
          isDragging && "opacity-50"
        )}
      >
        <div className="flex items-center gap-1.5">
          {isEditable && (
            <div ref={handleRef} className="flex-shrink-0 cursor-grab">
              <GripVertical className="size-4 text-tertiary" />
            </div>
          )}
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            onBlur={handleRenameSubmit}
            onKeyDown={(e) => {
              if (e.key === "Enter") e.currentTarget.blur();
              if (e.key === "Escape") setName(column.name);
            }}
            disabled={!isEditable}
            className="h-7 w-full border-none bg-transparent px-1 font-medium focus:bg-layer-1"
          />
          {isEditable && (
            <Tooltip tooltipContent={t("project_settings.board_columns.delete_column")}>
              <button
                type="button"
                onClick={() => onDelete(column)}
                className="flex-shrink-0 rounded-sm p-1 text-tertiary hover:bg-layer-2 hover:text-danger-secondary"
              >
                <Trash2 className="size-3.5" />
              </button>
            </Tooltip>
          )}
        </div>

        <div className="flex min-h-24 flex-col gap-1.5">
          {states.map((state) => (
            <BoardColumnStateChip key={state.id} state={state} sourceColumnId={column.id} isDraggable={isEditable} />
          ))}
          {states.length === 0 && (
            <p className="rounded-sm border border-dashed border-subtle p-3 text-center text-13 text-tertiary">
              {t("project_settings.board_columns.empty_column")}
            </p>
          )}
        </div>

        {entryState && (
          <p className="text-11 text-tertiary">
            {t("project_settings.board_columns.entry_state", { state: entryState.name })}
          </p>
        )}
      </div>
      {closestEdge === "right" && (
        <div className="absolute top-0 -right-1.5 z-1 h-full w-0.5 rounded-sm bg-accent-primary" />
      )}
    </div>
  );
});
