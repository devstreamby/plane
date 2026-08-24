/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Link2, Upload, Video } from "lucide-react";
// plane imports
import { cn } from "@plane/utils";
// local imports
import { ECustomVideoAttributeNames, ECustomVideoSource, ECustomVideoStatus } from "../types";
import type { CustomVideoNodeViewProps } from "./node-view";

export function CustomVideoChooser(props: CustomVideoNodeViewProps) {
  const { editor, updateAttributes } = props;
  const isEditable = editor.isEditable;

  return (
    <div
      className="video-upload-component flex cursor-default items-center justify-start gap-2 rounded-lg border border-dashed border-subtle bg-layer-3 px-2 py-3 text-tertiary"
      contentEditable={false}
    >
      <Video className="size-4 flex-shrink-0" />
      <div className="flex-1 text-14 font-medium">Add a video</div>
      {isEditable && (
        <div className="flex flex-shrink-0 items-center gap-1.5">
          <button
            type="button"
            className={cn(
              "flex items-center gap-1 rounded-md border border-subtle px-2 py-1 text-12 font-medium transition-colors",
              "hover:bg-layer-3-hover hover:text-secondary"
            )}
            onClick={() =>
              updateAttributes({
                [ECustomVideoAttributeNames.SOURCE]: ECustomVideoSource.UPLOAD,
                [ECustomVideoAttributeNames.STATUS]: ECustomVideoStatus.PENDING,
              })
            }
          >
            <Upload className="size-3" />
            Upload
          </button>
          <button
            type="button"
            className={cn(
              "flex items-center gap-1 rounded-md border border-subtle px-2 py-1 text-12 font-medium transition-colors",
              "hover:bg-layer-3-hover hover:text-secondary"
            )}
            onClick={() =>
              updateAttributes({
                [ECustomVideoAttributeNames.SOURCE]: ECustomVideoSource.EXTERNAL,
              })
            }
          >
            <Link2 className="size-3" />
            Embed link
          </button>
        </div>
      )}
    </div>
  );
}
