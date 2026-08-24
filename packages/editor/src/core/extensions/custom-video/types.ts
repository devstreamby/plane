/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { Node } from "@tiptap/core";
// types
import type { TFileHandler } from "@/types";

export enum ECustomVideoAttributeNames {
  ID = "id",
  SOURCE = "source",
  SRC = "src",
  PROVIDER = "provider",
  VIDEO_ID = "videoid",
  STATUS = "status",
}

// "upload" -> a video file stored in Plane's own asset storage.
// "external" -> a link to a video hosted elsewhere, rendered via an embed.
export enum ECustomVideoSource {
  UPLOAD = "upload",
  EXTERNAL = "external",
}

export enum ECustomVideoStatus {
  PENDING = "pending",
  UPLOADING = "uploading",
  UPLOADED = "uploaded",
}

export enum ECustomVideoProvider {
  YOUTUBE = "youtube",
  VIMEO = "vimeo",
  RUTUBE = "rutube",
  VK = "vk",
  DIRECT = "direct",
}

export type TCustomVideoAttributes = {
  [ECustomVideoAttributeNames.ID]: string | null;
  [ECustomVideoAttributeNames.SOURCE]: ECustomVideoSource | null;
  [ECustomVideoAttributeNames.SRC]: string | null;
  [ECustomVideoAttributeNames.PROVIDER]: ECustomVideoProvider | null;
  [ECustomVideoAttributeNames.VIDEO_ID]: string | null;
  [ECustomVideoAttributeNames.STATUS]: ECustomVideoStatus | null;
};

export type UploadEntity = ({ event: "insert" } | { event: "drop"; file: File }) & { hasOpenedFileInputOnce?: boolean };

export type InsertVideoComponentProps = {
  file?: File;
  pos?: number;
  event: "insert" | "drop";
};

export type InsertVideoEmbedProps = {
  provider: ECustomVideoProvider;
  videoId: string;
  pos?: number;
};

export type CustomVideoExtensionOptions = {
  getVideoSource: TFileHandler["getAssetSrc"];
  getVideoDownloadSource: TFileHandler["getAssetDownloadSrc"];
  restoreVideo: TFileHandler["restore"];
  uploadVideo?: TFileHandler["upload"];
};

export type CustomVideoExtensionStorage = {
  fileMap: Map<string, UploadEntity>;
  deletedVideoSet: Map<string, boolean>;
  maxFileSize: number;
};

export type CustomVideoExtensionType = Node<CustomVideoExtensionOptions, CustomVideoExtensionStorage>;
