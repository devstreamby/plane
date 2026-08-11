/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useRef, useState } from "react";
import { draggable } from "@atlaskit/pragmatic-drag-and-drop/element/adapter";
import { observer } from "mobx-react";
import { GripVertical } from "lucide-react";
// plane imports
import { EIconSize } from "@plane/constants";
import { StateGroupIcon } from "@plane/propel/icons";
import type { IState } from "@plane/types";
import { cn } from "@plane/utils";
// local imports
import type { TStateDragData } from "./types";

type TBoardColumnStateChipProps = {
  state: IState;
  sourceColumnId: string | undefined;
  isDraggable: boolean;
};

export const BoardColumnStateChip = observer(function BoardColumnStateChip(props: TBoardColumnStateChipProps) {
  const { state, sourceColumnId, isDraggable } = props;
  // refs
  const chipRef = useRef<HTMLDivElement | null>(null);
  // states
  const [isDragging, setIsDragging] = useState(false);

  useEffect(() => {
    const element = chipRef.current;
    if (!element || !isDraggable) return;
    return draggable({
      element,
      getInitialData: (): TStateDragData => ({
        dragType: "BOARD_COLUMN_STATE",
        stateId: state.id,
        sourceColumnId,
      }),
      onDragStart: () => setIsDragging(true),
      onDrop: () => setIsDragging(false),
    });
  }, [isDraggable, sourceColumnId, state.id]);

  return (
    <div
      ref={chipRef}
      className={cn(
        "flex items-center gap-1.5 rounded-sm border border-subtle bg-layer-1 px-2 py-1.5 text-13",
        isDraggable && "cursor-grab",
        isDragging && "opacity-50"
      )}
    >
      {isDraggable && <GripVertical className="size-3.5 flex-shrink-0 text-tertiary" />}
      <StateGroupIcon stateGroup={state.group} color={state.color} size={EIconSize.SM} />
      <span className="truncate">{state.name}</span>
    </div>
  );
});
