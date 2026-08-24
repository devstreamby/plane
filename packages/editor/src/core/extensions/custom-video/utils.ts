/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { Editor, NodeViewProps } from "@tiptap/core";
// constants
import { CORE_EXTENSIONS } from "@/constants/extension";
// local imports
import { ECustomVideoAttributeNames, ECustomVideoProvider } from "./types";
import type { TCustomVideoAttributes } from "./types";

export const DEFAULT_CUSTOM_VIDEO_ATTRIBUTES: TCustomVideoAttributes = {
  [ECustomVideoAttributeNames.ID]: null,
  [ECustomVideoAttributeNames.SOURCE]: null,
  [ECustomVideoAttributeNames.SRC]: null,
  [ECustomVideoAttributeNames.PROVIDER]: null,
  [ECustomVideoAttributeNames.VIDEO_ID]: null,
  [ECustomVideoAttributeNames.STATUS]: null,
};

export const getVideoComponentFileMap = (editor: Editor) => editor.storage.videoComponent?.fileMap;

export const getVideoBlockId = (id: string) => `editor-video-block-${id}`;

// Video ids we accept from third-party providers are only ever plugged into a
// hardcoded embed URL template (never interpolated into raw HTML/JS), but we
// still validate their shape defensively before building that URL, in case a
// node ever reaches the client with a malformed/tampered attribute.
const PROVIDER_VIDEO_ID_PATTERN: Record<ECustomVideoProvider, RegExp> = {
  [ECustomVideoProvider.YOUTUBE]: /^[A-Za-z0-9_-]{1,32}$/,
  [ECustomVideoProvider.VIMEO]: /^[A-Za-z0-9_-]{1,32}$/,
  [ECustomVideoProvider.RUTUBE]: /^[A-Za-z0-9_-]{1,64}$/,
  [ECustomVideoProvider.VK]: /^-?\d{1,20}_\d{1,20}$/,
  [ECustomVideoProvider.DIRECT]: /^https:\/\/[^\s"'<>]{1,2048}$/,
};

export const isValidProviderVideoId = (provider: ECustomVideoProvider | null, videoId: string | null): boolean => {
  if (!provider || !videoId) return false;
  const pattern = PROVIDER_VIDEO_ID_PATTERN[provider];
  return pattern ? pattern.test(videoId) : false;
};

// After the video block finishes resolving (upload done, or embed link
// submitted), move the cursor to the paragraph after it — creating one if
// none exists yet — so the user isn't left with nowhere to type. Mirrors
// the equivalent logic in custom-image's uploader.
export const moveCursorAfterVideoNode = (editor: Editor, getPos: NodeViewProps["getPos"]) => {
  const pos = getPos();
  if (pos === undefined) return;
  const nextNode = editor.state.doc.nodeAt(pos + 1);
  if (nextNode && nextNode.type.name === CORE_EXTENSIONS.PARAGRAPH) {
    editor.commands.setTextSelection(pos + 1);
  } else {
    editor.commands.createParagraphNear();
  }
};

// Builds the embed src for iframe-based providers. Returns undefined for
// providers that aren't rendered via an iframe (e.g. "direct").
export const getVideoEmbedSrc = (provider: ECustomVideoProvider, videoId: string): string | undefined => {
  switch (provider) {
    case ECustomVideoProvider.YOUTUBE:
      return `https://www.youtube-nocookie.com/embed/${videoId}`;
    case ECustomVideoProvider.VIMEO:
      return `https://player.vimeo.com/video/${videoId}`;
    case ECustomVideoProvider.RUTUBE:
      return `https://rutube.ru/play/embed/${videoId}`;
    case ECustomVideoProvider.VK: {
      const [oid, id] = videoId.split("_");
      return `https://vk.com/video_ext.php?oid=${oid}&id=${id}&hd=2`;
    }
    default:
      return undefined;
  }
};
