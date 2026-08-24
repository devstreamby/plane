/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Video } from "lucide-react";
import type { ChangeEvent } from "react";
import { useCallback, useEffect, useMemo, useRef } from "react";
// plane imports
import { cn } from "@plane/utils";
// constants
import { ACCEPTED_VIDEO_MIME_TYPES } from "@/constants/config";
// helpers
import type { EFileError } from "@/helpers/file";
// hooks
import { useUploader, useDropZone } from "@/hooks/use-file-upload";
// local imports
import { ECustomVideoStatus } from "../types";
import { getVideoComponentFileMap } from "../utils";
import { ImageUploadStatus } from "../../custom-image/components/upload-status";
import type { CustomVideoNodeViewProps } from "./node-view";

export function CustomVideoUploader(props: CustomVideoNodeViewProps) {
  const { editor, extension, getPos, node, selected, updateAttributes } = props;
  const fileInputRef = useRef<HTMLInputElement>(null);
  const hasTriedUploadingOnMountRef = useRef(false);
  const { id: videoEntityId } = node.attrs;
  const videoComponentFileMap = useMemo(() => getVideoComponentFileMap(editor), [editor]);
  const maxFileSize = editor.storage.videoComponent?.maxFileSize ?? 0;

  const onUpload = useCallback(
    (url: string) => {
      if (!url || !videoEntityId) return;
      updateAttributes({ src: url, status: ECustomVideoStatus.UPLOADED });
      videoComponentFileMap?.delete(videoEntityId);
    },
    [videoComponentFileMap, videoEntityId, updateAttributes]
  );

  const uploadVideoEditorCommand = useCallback(
    async (file: File) => {
      updateAttributes({ status: ECustomVideoStatus.UPLOADING });
      return await extension.options.uploadVideo?.(videoEntityId ?? "", file);
    },
    [extension.options, videoEntityId, updateAttributes]
  );

  const handleProgressStatus = useCallback(
    (isUploading: boolean) => {
      editor.storage.utility.uploadInProgress = isUploading;
    },
    [editor]
  );

  const handleInvalidFile = useCallback((_error: EFileError, _file: File, message: string) => {
    alert(message);
  }, []);

  const { isUploading, uploadFile } = useUploader({
    acceptedMimeTypes: ACCEPTED_VIDEO_MIME_TYPES,
    editorCommand: uploadVideoEditorCommand,
    handleProgressStatus,
    maxFileSize,
    onInvalidFile: handleInvalidFile,
    onUpload,
  });

  const { draggedInside, onDrop, onDragEnter, onDragLeave } = useDropZone({
    editor,
    getPos,
    type: "video",
    uploader: uploadFile,
  });

  // if the node was created via drag-and-drop, the file is already staged in
  // the extension's fileMap — pick it up and start uploading immediately.
  useEffect(() => {
    if (hasTriedUploadingOnMountRef.current) return;
    hasTriedUploadingOnMountRef.current = true;
    const meta = videoComponentFileMap?.get(videoEntityId ?? "");
    if (meta && meta.event === "drop" && "file" in meta) {
      uploadFile(meta.file);
    }
  }, [videoEntityId, uploadFile, videoComponentFileMap]);

  const onFileChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      e.target.value = "";
      if (file) uploadFile(file);
    },
    [uploadFile]
  );

  return (
    <div
      className={cn(
        "video-upload-component relative flex cursor-pointer items-center justify-start gap-2 rounded-lg border border-dashed bg-layer-3 px-2 py-3 text-tertiary transition-all duration-200 ease-in-out",
        {
          "border-subtle": !(selected && editor.isEditable),
          "hover:bg-layer-3-hover hover:text-secondary": editor.isEditable,
          "bg-layer-3-hover text-secondary": draggedInside && editor.isEditable,
          "bg-accent-primary/10 text-accent-secondary": selected && editor.isEditable,
        }
      )}
      onDrop={onDrop}
      onDragOver={onDragEnter}
      onDragLeave={onDragLeave}
      contentEditable={false}
      // eslint-disable-next-line jsx-a11y/prefer-tag-over-role -- a <button> can't accept the drag/drop handlers useDropZone types for HTMLDivElement
      role="button"
      tabIndex={editor.isEditable ? 0 : -1}
      onClick={() => editor.isEditable && !isUploading && fileInputRef.current?.click()}
      onKeyDown={(e) => {
        if ((e.key === "Enter" || e.key === " ") && editor.isEditable && !isUploading) {
          e.preventDefault();
          fileInputRef.current?.click();
        }
      }}
    >
      <Video className="size-4 flex-shrink-0" />
      <div className="flex-1 text-14 font-medium">
        {isUploading ? "Uploading…" : draggedInside && editor.isEditable ? "Drop video here" : "Click to add a video"}
      </div>
      {isUploading && videoEntityId && <ImageUploadStatus editor={editor} nodeId={videoEntityId} />}
      <input
        className="size-0 overflow-hidden"
        ref={fileInputRef}
        hidden
        type="file"
        accept={ACCEPTED_VIDEO_MIME_TYPES.join(",")}
        onChange={onFileChange}
      />
    </div>
  );
}
