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

// Reconstructs the canonical, human-visitable page URL for a provider video
// — used both as the oEmbed request target and as the "watch on X" link in
// the preview card. For "direct" links, videoId already *is* the URL.
export const buildProviderVideoUrl = (provider: ECustomVideoProvider, videoId: string): string => {
  switch (provider) {
    case ECustomVideoProvider.YOUTUBE:
      return `https://www.youtube.com/watch?v=${videoId}`;
    case ECustomVideoProvider.VIMEO:
      return `https://vimeo.com/${videoId}`;
    case ECustomVideoProvider.RUTUBE:
      return `https://rutube.ru/video/${videoId}/`;
    case ECustomVideoProvider.VK: {
      const [oid, id] = videoId.split("_");
      return `https://vk.com/video${oid}_${id}`;
    }
    case ECustomVideoProvider.DIRECT:
    default:
      return videoId;
  }
};

// Builds the embed src for iframe-based providers, used to play a video
// inline in place once the user clicks play on its preview card. Returns
// undefined for providers that aren't rendered via an iframe (e.g. "direct").
export const buildProviderEmbedSrc = (provider: ECustomVideoProvider, videoId: string): string | undefined => {
  switch (provider) {
    case ECustomVideoProvider.YOUTUBE:
      return `https://www.youtube-nocookie.com/embed/${videoId}?autoplay=1`;
    case ECustomVideoProvider.VIMEO:
      return `https://player.vimeo.com/video/${videoId}?autoplay=1`;
    case ECustomVideoProvider.RUTUBE:
      return `https://rutube.ru/play/embed/${videoId}?autoStart=true`;
    case ECustomVideoProvider.VK: {
      const [oid, id] = videoId.split("_");
      return `https://vk.com/video_ext.php?oid=${oid}&id=${id}&hd=2&autoplay=1`;
    }
    default:
      return undefined;
  }
};

export type TVideoOEmbedResult = {
  title: string;
  authorName?: string;
  thumbnailUrl?: string;
};

// Public, CORS-enabled oEmbed endpoints — no API key needed, fetchable
// straight from the browser. VK has no equivalent without an authenticated
// API call, so it's intentionally absent here; the card falls back to a
// plain link for it.
const OEMBED_ENDPOINT_BUILDERS: Partial<Record<ECustomVideoProvider, (pageUrl: string) => string>> = {
  [ECustomVideoProvider.YOUTUBE]: (pageUrl) =>
    `https://www.youtube.com/oembed?url=${encodeURIComponent(pageUrl)}&format=json`,
  [ECustomVideoProvider.VIMEO]: (pageUrl) => `https://vimeo.com/api/oembed.json?url=${encodeURIComponent(pageUrl)}`,
  [ECustomVideoProvider.RUTUBE]: (pageUrl) =>
    `https://rutube.ru/api/oembed/?url=${encodeURIComponent(pageUrl)}&format=json`,
};

// Renders the video as a static link-preview card (title/thumbnail/author,
// fetched once via the provider's public oEmbed endpoint) instead of a live
// iframe player — avoids sandbox/CSP embed-player failures entirely and
// matches the "smart link" pattern from tools like Jira/Confluence.
export const fetchVideoOEmbed = async (
  provider: ECustomVideoProvider,
  videoId: string
): Promise<TVideoOEmbedResult | undefined> => {
  const buildEndpoint = OEMBED_ENDPOINT_BUILDERS[provider];
  if (!buildEndpoint) return undefined;

  const pageUrl = buildProviderVideoUrl(provider, videoId);
  const response = await fetch(buildEndpoint(pageUrl));
  if (!response.ok) throw new Error(`oEmbed request failed with status ${response.status}`);

  const data: unknown = await response.json();
  const title = (data as { title?: unknown } | null)?.title;
  if (typeof title !== "string") throw new Error("oEmbed response missing a title");

  const authorName = (data as { author_name?: unknown }).author_name;
  const thumbnailUrl = (data as { thumbnail_url?: unknown }).thumbnail_url;

  return {
    title,
    authorName: typeof authorName === "string" ? authorName : undefined,
    thumbnailUrl: typeof thumbnailUrl === "string" ? thumbnailUrl : undefined,
  };
};
