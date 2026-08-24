/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { ReactNodeViewRenderer } from "@tiptap/react";
import { v4 as uuidv4 } from "uuid";
// constants
import { ACCEPTED_VIDEO_MIME_TYPES } from "@/constants/config";
// helpers
import { isFileValid } from "@/helpers/file";
import { insertEmptyParagraphAtNodeBoundaries } from "@/helpers/insert-empty-paragraph-at-node-boundary";
// types
import type { TFileHandler } from "@/types";
// local imports
import type { CustomVideoNodeViewProps } from "./components/node-view";
import { CustomVideoNodeView } from "./components/node-view";
import { CustomVideoExtensionConfig } from "./extension-config";
import type { CustomVideoExtensionOptions, CustomVideoExtensionStorage } from "./types";
import { ECustomVideoAttributeNames, ECustomVideoSource, ECustomVideoStatus } from "./types";
import { getVideoComponentFileMap } from "./utils";

type Props = {
  fileHandler: TFileHandler;
  isEditable: boolean;
};

export function CustomVideoExtension(extensionProps: Props) {
  const { fileHandler, isEditable } = extensionProps;
  const { getAssetSrc, getAssetDownloadSrc, restore: restoreVideoFn } = fileHandler;

  return CustomVideoExtensionConfig.extend<CustomVideoExtensionOptions, CustomVideoExtensionStorage>({
    selectable: isEditable,
    draggable: isEditable,

    addOptions() {
      const upload = "upload" in fileHandler ? fileHandler.upload : undefined;
      return {
        ...this.parent?.(),
        getVideoSource: getAssetSrc,
        getVideoDownloadSource: getAssetDownloadSrc,
        restoreVideo: restoreVideoFn,
        uploadVideo: upload,
      };
    },

    addStorage() {
      const maxFileSize = "validation" in fileHandler ? fileHandler.validation?.maxFileSize : 0;

      return {
        fileMap: new Map(),
        deletedVideoSet: new Map<string, boolean>(),
        maxFileSize,
        // video markdown conversion happens through the custom-components HTML
        // handler, not tiptap-markdown's JSON serializer.
        markdown: {
          serialize() {},
        },
      };
    },

    addCommands() {
      return {
        insertVideoComponent:
          (props) =>
          ({ commands }) => {
            const videoId = uuidv4();
            const attributes: Partial<Record<ECustomVideoAttributeNames, unknown>> = {
              [ECustomVideoAttributeNames.ID]: videoId,
            };

            // A file is only present for drag-and-drop / paste — in that case
            // we know upfront this is an upload, and start it immediately.
            if (props?.file) {
              if (
                !isFileValid({
                  acceptedMimeTypes: ACCEPTED_VIDEO_MIME_TYPES,
                  file: props.file,
                  maxFileSize: this.storage.maxFileSize,
                  onError: (_error, message) => alert(message),
                })
              ) {
                return false;
              }

              const videoComponentFileMap = getVideoComponentFileMap(this.editor);
              if (videoComponentFileMap && props.event === "drop") {
                videoComponentFileMap.set(videoId, { file: props.file, event: "drop" });
              }

              attributes[ECustomVideoAttributeNames.SOURCE] = ECustomVideoSource.UPLOAD;
              attributes[ECustomVideoAttributeNames.STATUS] = ECustomVideoStatus.PENDING;
            }
            // Otherwise (toolbar/slash-command insert) the node starts in a
            // "choose upload or embed" state — the NodeView renders a chooser.

            if (props.pos !== undefined) {
              return commands.insertContentAt(props.pos, {
                type: this.name,
                attrs: attributes,
              });
            }
            return commands.insertContent({
              type: this.name,
              attrs: attributes,
            });
          },
      };
    },

    addKeyboardShortcuts() {
      return {
        ArrowDown: insertEmptyParagraphAtNodeBoundaries("down", this.name),
        ArrowUp: insertEmptyParagraphAtNodeBoundaries("up", this.name),
      };
    },

    addNodeView() {
      return ReactNodeViewRenderer((props) => (
        <CustomVideoNodeView {...props} node={props.node as CustomVideoNodeViewProps["node"]} />
      ));
    },
  });
}
