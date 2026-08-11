/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useRef, useState } from "react";
import { dropTargetForElements } from "@atlaskit/pragmatic-drag-and-drop/element/adapter";
import { observer } from "mobx-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import type { IState } from "@plane/types";
import { cn } from "@plane/utils";
// local imports
import { BoardColumnStateChip } from "./state-chip";
import type { TStateDragData } from "./types";
import { isStateDragData } from "./types";

type TUnmappedStatesProps = {
  states: IState[];
  isEditable: boolean;
  onStateDropped: (data: TStateDragData) => Promise<void>;
};

export const BoardColumnsUnmappedStates = observer(function BoardColumnsUnmappedStates(props: TUnmappedStatesProps) {
  const { states, isEditable, onStateDropped } = props;
  // refs
  const trayRef = useRef<HTMLDivElement | null>(null);
  // states
  const [isDraggedOver, setIsDraggedOver] = useState(false);
  // hooks
  const { t } = useTranslation();

  useEffect(() => {
    const element = trayRef.current;
    if (!element) return;
    return dropTargetForElements({
      element,
      canDrop: ({ source }) => isStateDragData(source.data) && !!source.data.sourceColumnId,
      onDragEnter: () => setIsDraggedOver(true),
      onDragLeave: () => setIsDraggedOver(false),
      onDrop: ({ source }) => {
        setIsDraggedOver(false);
        if (isStateDragData(source.data)) void onStateDropped(source.data);
      },
    });
  }, [onStateDropped]);

  return (
    <div
      ref={trayRef}
      className={cn(
        "flex flex-col gap-2 rounded-sm border border-dashed border-subtle p-3 transition-all",
        isDraggedOver && "border-accent-strong bg-layer-2"
      )}
    >
      <div>
        <h4 className="text-13 font-medium">{t("project_settings.board_columns.unmapped.title")}</h4>
        <p className="text-11 text-tertiary">{t("project_settings.board_columns.unmapped.description")}</p>
      </div>
      {states.length > 0 ? (
        <div className="flex flex-wrap gap-1.5">
          {states.map((state) => (
            <BoardColumnStateChip key={state.id} state={state} sourceColumnId={undefined} isDraggable={isEditable} />
          ))}
        </div>
      ) : (
        <p className="text-13 text-tertiary">{t("project_settings.board_columns.unmapped.empty")}</p>
      )}
    </div>
  );
});
