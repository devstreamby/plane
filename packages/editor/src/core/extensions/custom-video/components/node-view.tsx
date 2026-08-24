/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { NodeViewWrapper } from "@tiptap/react";
import type { NodeViewProps } from "@tiptap/react";
// local imports
import type { CustomVideoExtensionType, TCustomVideoAttributes } from "../types";
import { ECustomVideoAttributeNames, ECustomVideoSource, ECustomVideoStatus } from "../types";
import { CustomVideoPlayer } from "./player";
import { CustomVideoUploader } from "./uploader";

export type CustomVideoNodeViewProps = Omit<NodeViewProps, "extension" | "updateAttributes"> & {
  extension: CustomVideoExtensionType;
  node: NodeViewProps["node"] & {
    attrs: TCustomVideoAttributes;
  };
  updateAttributes: (attrs: Partial<TCustomVideoAttributes>) => void;
};

export function CustomVideoNodeView(props: CustomVideoNodeViewProps) {
  const { node } = props;
  const { source, status } = node.attrs;

  // "external" nodes only ever get created fully-resolved (provider +
  // videoId set together, see insertVideoEmbed) — there's no in-between
  // state to render here.
  const content =
    source === ECustomVideoSource.EXTERNAL || status === ECustomVideoStatus.UPLOADED ? (
      <CustomVideoPlayer {...props} />
    ) : (
      <CustomVideoUploader {...props} />
    );

  return (
    <NodeViewWrapper key={node.attrs[ECustomVideoAttributeNames.ID]}>
      <div className="video-component mx-0 my-2 p-0" data-drag-handle>
        {content}
      </div>
    </NodeViewWrapper>
  );
}
