/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { Editor } from "@tiptap/core";
import { Plugin, PluginKey } from "@tiptap/pm/state";
// plane imports
import { parseVideoUrl } from "@plane/utils";
// constants
import {
  ACCEPTED_ATTACHMENT_MIME_TYPES,
  ACCEPTED_IMAGE_MIME_TYPES,
  ACCEPTED_VIDEO_MIME_TYPES,
} from "@/constants/config";
// extensions
import type { ECustomVideoProvider } from "@/extensions/custom-video/types";
import { isValidProviderVideoId } from "@/extensions/custom-video/utils";
// types
import type { TEditorCommands, TExtensions } from "@/types";

type Props = {
  disabledExtensions?: TExtensions[];
  flaggedExtensions?: TExtensions[];
  editor: Editor;
};

export const DropHandlerPlugin = (props: Props): Plugin => {
  const { disabledExtensions, flaggedExtensions, editor } = props;

  return new Plugin({
    key: new PluginKey("drop-handler-plugin"),
    props: {
      handlePaste: (view, event) => {
        if (
          editor.isEditable &&
          event.clipboardData &&
          event.clipboardData.files &&
          event.clipboardData.files.length > 0
        ) {
          event.preventDefault();
          const files = Array.from(event.clipboardData.files);
          const acceptedFiles = files.filter(
            (f) => ACCEPTED_IMAGE_MIME_TYPES.includes(f.type) || ACCEPTED_ATTACHMENT_MIME_TYPES.includes(f.type)
          );

          if (acceptedFiles.length) {
            const pos = view.state.selection.from;
            insertFilesSafely({
              disabledExtensions,
              flaggedExtensions,
              editor,
              files: acceptedFiles,
              initialPos: pos,
              event: "drop",
            });
          }
          return true;
        }

        // A bare video-provider link, pasted on its own with nothing else
        // selected — auto-embed it instead of leaving it as plain link
        // text. Anywhere else in the document is where a user will
        // naturally try to paste a video link (not just inside the video
        // node's own "embed link" input), so this is the paste path that
        // actually needs to work.
        if (editor.isEditable && !disabledExtensions?.includes("video") && event.clipboardData) {
          const text = event.clipboardData.getData("text/plain")?.trim();
          if (text && !text.includes("\n") && !(event.clipboardData.files && event.clipboardData.files.length > 0)) {
            const parsed = parseVideoUrl(text);
            const provider = parsed?.provider as ECustomVideoProvider | undefined;
            if (parsed && provider && isValidProviderVideoId(provider, parsed.videoId)) {
              const pos = view.state.selection.from;
              const inserted = editor.commands.insertVideoEmbed({ provider, videoId: parsed.videoId, pos });
              if (inserted) {
                event.preventDefault();
                return true;
              }
            }
          }
        }

        return false;
      },
      handleDrop: (view, event, _slice, moved) => {
        if (
          editor.isEditable &&
          !moved &&
          event.dataTransfer &&
          event.dataTransfer.files &&
          event.dataTransfer.files.length > 0
        ) {
          event.preventDefault();
          const files = Array.from(event.dataTransfer.files);
          const acceptedFiles = files.filter(
            (f) => ACCEPTED_IMAGE_MIME_TYPES.includes(f.type) || ACCEPTED_ATTACHMENT_MIME_TYPES.includes(f.type)
          );

          if (acceptedFiles.length) {
            const coordinates = view.posAtCoords({
              left: event.clientX,
              top: event.clientY,
            });

            if (coordinates) {
              const pos = coordinates.pos;
              insertFilesSafely({
                disabledExtensions,
                editor,
                files: acceptedFiles,
                initialPos: pos,
                event: "drop",
              });
            }
            return true;
          }
        }
        return false;
      },
    },
  });
};

type InsertFilesSafelyArgs = {
  disabledExtensions?: TExtensions[];
  flaggedExtensions?: TExtensions[];
  editor: Editor;
  event: "insert" | "drop";
  files: File[];
  initialPos: number;
  type?: Extract<TEditorCommands, "attachment" | "image" | "video">;
};

export const insertFilesSafely = async (args: InsertFilesSafelyArgs) => {
  const { disabledExtensions, editor, event, files, initialPos, type } = args;
  let pos = initialPos;

  for (const file of files) {
    // safe insertion
    const docSize = editor.state.doc.content.size;
    pos = Math.min(pos, docSize);

    let fileType: "image" | "video" | "attachment" | null = null;

    try {
      if (type) {
        if (["image", "video", "attachment"].includes(type)) fileType = type;
        else throw new Error("Wrong file type passed");
      } else {
        if (ACCEPTED_IMAGE_MIME_TYPES.includes(file.type)) fileType = "image";
        else if (ACCEPTED_VIDEO_MIME_TYPES.includes(file.type)) fileType = "video";
        else if (ACCEPTED_ATTACHMENT_MIME_TYPES.includes(file.type)) fileType = "attachment";
      }
      // insert file depending on the type at the current position
      if (fileType === "image" && !disabledExtensions?.includes("image")) {
        editor.commands.insertImageComponent({
          file,
          pos,
          event,
        });
      } else if (fileType === "video" && !disabledExtensions?.includes("video")) {
        editor.commands.insertVideoComponent({
          file,
          pos,
          event,
        });
      } else if (fileType === "attachment") {
      }
    } catch (error) {
      console.error(`Error while ${event}ing file:`, error);
    }

    // Move to the next position
    pos += 1;
  }
};
