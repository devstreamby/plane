/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// local imports
import { getFileURL } from "../file";

type TEditorSrcArgs = {
  assetId: string;
  projectId?: string;
  workspaceSlug: string;
};

/**
 * @description generate the file source using assetId
 * @param {TEditorSrcArgs} args
 */
export const getEditorAssetSrc = (args: TEditorSrcArgs): string | undefined => {
  const { assetId, projectId, workspaceSlug } = args;
  let url: string | undefined = "";
  if (projectId) {
    url = getFileURL(`/api/assets/v2/workspaces/${workspaceSlug}/projects/${projectId}/${assetId}/`);
  } else {
    url = getFileURL(`/api/assets/v2/workspaces/${workspaceSlug}/${assetId}/`);
  }
  return url;
};

/**
 * @description generate the file source using assetId
 * @param {TEditorSrcArgs} args
 */
export const getEditorAssetDownloadSrc = (args: TEditorSrcArgs): string | undefined => {
  const { assetId, projectId, workspaceSlug } = args;
  let url: string | undefined = "";
  if (projectId) {
    url = getFileURL(`/api/assets/v2/workspaces/${workspaceSlug}/projects/${projectId}/download/${assetId}/`);
  } else {
    url = getFileURL(`/api/assets/v2/workspaces/${workspaceSlug}/download/${assetId}/`);
  }
  return url;
};

export const getTextContent = (jsx: React.ReactNode | null | undefined): string => {
  if (!jsx) return "";

  const div = document.createElement("div");
  div.innerHTML = jsx.toString();
  return div.textContent?.trim() ?? "";
};

export const isEditorEmpty = (description: string | undefined): boolean =>
  !description ||
  description === "<p></p>" ||
  description === `<p class="editor-paragraph-block"></p>` ||
  description.trim() === "";

export type TVideoEmbedProvider = "youtube" | "vimeo" | "rutube" | "vk" | "direct";

export type TParsedVideoEmbed = {
  provider: TVideoEmbedProvider;
  videoId: string;
};

/**
 * @description parse a pasted URL into a {provider, videoId} pair the video
 * node can embed. Returns undefined for URLs that don't match a known
 * provider or a direct video file link — those are left as plain text/links.
 * @param {string} rawUrl
 */
export const parseVideoUrl = (rawUrl: string): TParsedVideoEmbed | undefined => {
  let url: URL;
  try {
    url = new URL(rawUrl.trim());
  } catch {
    return undefined;
  }
  if (url.protocol !== "https:" && url.protocol !== "http:") return undefined;
  const host = url.hostname.replace(/^www\./, "").toLowerCase();

  if (host === "youtu.be") {
    const videoId = url.pathname.slice(1).split("/")[0];
    if (videoId) return { provider: "youtube", videoId };
  }
  if (host === "youtube.com" || host === "m.youtube.com") {
    if (url.pathname === "/watch") {
      const videoId = url.searchParams.get("v");
      if (videoId) return { provider: "youtube", videoId };
    }
    const embedMatch = url.pathname.match(/^\/(embed|shorts|live)\/([^/]+)/);
    if (embedMatch) return { provider: "youtube", videoId: embedMatch[2] };
  }

  if (host === "vimeo.com") {
    const match = url.pathname.match(/^\/(\d+)/);
    if (match) return { provider: "vimeo", videoId: match[1] };
  }
  if (host === "player.vimeo.com") {
    const match = url.pathname.match(/^\/video\/(\d+)/);
    if (match) return { provider: "vimeo", videoId: match[1] };
  }

  if (host === "rutube.ru") {
    const match = url.pathname.match(/^\/video\/([a-z0-9]+)/i);
    if (match) return { provider: "rutube", videoId: match[1] };
  }

  if (host === "vk.com" || host === "vkvideo.ru") {
    const match = url.pathname.match(/\/video(-?\d+_\d+)/);
    if (match) return { provider: "vk", videoId: match[1] };
  }

  if (/\.(mp4|webm|ogg)$/i.test(url.pathname)) {
    return { provider: "direct", videoId: url.toString() };
  }

  return undefined;
};

export enum CORE_EXTENSIONS {
  BLOCKQUOTE = "blockquote",
  BOLD = "bold",
  BULLET_LIST = "bulletList",
  CALLOUT = "calloutComponent",
  CHARACTER_COUNT = "characterCount",
  CODE_BLOCK = "codeBlock",
  CODE_INLINE = "code",
  CUSTOM_COLOR = "customColor",
  CUSTOM_IMAGE = "imageComponent",
  CUSTOM_LINK = "link",
  CUSTOM_VIDEO = "videoComponent",
  DOCUMENT = "doc",
  DROP_CURSOR = "dropCursor",
  ENTER_KEY = "enterKey",
  GAP_CURSOR = "gapCursor",
  HARD_BREAK = "hardBreak",
  HEADING = "heading",
  HEADINGS_LIST = "headingsList",
  HISTORY = "history",
  HORIZONTAL_RULE = "horizontalRule",
  IMAGE = "image",
  ITALIC = "italic",
  LIST_ITEM = "listItem",
  MARKDOWN_CLIPBOARD = "markdownClipboard",
  MENTION = "mention",
  ORDERED_LIST = "orderedList",
  PARAGRAPH = "paragraph",
  PLACEHOLDER = "placeholder",
  SIDE_MENU = "editorSideMenu",
  SLASH_COMMANDS = "slash-command",
  STRIKETHROUGH = "strike",
  TABLE = "table",
  TABLE_CELL = "tableCell",
  TABLE_HEADER = "tableHeader",
  TABLE_ROW = "tableRow",
  TASK_ITEM = "taskItem",
  TASK_LIST = "taskList",
  TEXT_ALIGN = "textAlign",
  TEXT_STYLE = "textStyle",
  TYPOGRAPHY = "typography",
  UNDERLINE = "underline",
  UTILITY = "utility",
  WORK_ITEM_EMBED = "issue-embed-component",
  EMOJI = "emoji",
}

export enum ADDITIONAL_EXTENSIONS {}
