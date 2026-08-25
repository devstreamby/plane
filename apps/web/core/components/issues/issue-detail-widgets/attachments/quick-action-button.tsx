/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import React, { useCallback, useState } from "react";
import { observer } from "mobx-react";
import type { FileRejection } from "react-dropzone";
import { useDropzone } from "react-dropzone";
import { PlusIcon } from "@plane/propel/icons";
// plane imports
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { TIssueServiceType } from "@plane/types";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
// plane web hooks
import { useFileSize } from "@/hooks/use-file-size";
// local imports
import { useAttachmentOperations } from "./helper";

type Props = {
  workspaceSlug: string;
  projectId: string;
  issueId: string;
  customButton?: React.ReactNode;
  disabled?: boolean;
  issueServiceType: TIssueServiceType;
};

export const IssueAttachmentActionButton = observer(function IssueAttachmentActionButton(props: Props) {
  const { workspaceSlug, projectId, issueId, customButton, disabled = false, issueServiceType } = props;
  // state
  const [isLoading, setIsLoading] = useState(false);
  // store hooks
  const { setLastWidgetAction, fetchActivities } = useIssueDetail(issueServiceType);
  // file size
  const { maxFileSize } = useFileSize();
  // operations
  const { operations: attachmentOperations } = useAttachmentOperations(
    workspaceSlug,
    projectId,
    issueId,
    issueServiceType
  );
  // handlers
  const handleFetchPropertyActivities = useCallback(() => {
    fetchActivities(workspaceSlug, projectId, issueId);
  }, [fetchActivities, workspaceSlug, projectId, issueId]);

  const onDrop = useCallback(
    (acceptedFiles: File[], rejectedFiles: FileRejection[]) => {
      const totalAttachedFiles = acceptedFiles.length + rejectedFiles.length;

      if (rejectedFiles.length === 0) {
        const currentFile: File = acceptedFiles[0];
        if (!currentFile || !workspaceSlug) return;

        setIsLoading(true);
        attachmentOperations
          .create(currentFile)
          // Already surfaced via the promise-toast in useAttachmentOperations -- swallow
          // here only to avoid an unhandled rejection, don't show a second toast.
          .catch(() => {})
          .finally(() => {
            handleFetchPropertyActivities();
            setLastWidgetAction("attachments");
            setIsLoading(false);
          });
        return;
      }

      setToast({
        type: TOAST_TYPE.ERROR,
        title: "Error!",
        message:
          totalAttachedFiles > 1
            ? "Only one file can be uploaded at a time."
            : `File must be of ${maxFileSize / 1024 / 1024}MB or less in size.`,
      });
      return;
    },
    [attachmentOperations, maxFileSize, workspaceSlug, handleFetchPropertyActivities, setLastWidgetAction]
  );

  const { getRootProps, getInputProps } = useDropzone({
    onDrop,
    maxSize: maxFileSize,
    multiple: false,
    disabled: isLoading || disabled,
  });
  const rootProps = getRootProps();

  return (
    <>
      {/* react-dropzone opens this via a ref, not DOM nesting -- kept outside the button
          so a focusable input isn't nested inside another focusable control. */}
      <input {...getInputProps()} />
      <button
        {...rootProps}
        type="button"
        disabled={disabled}
        onClick={(e) => {
          // Stop the click from bubbling to the issue row (which opens the issue), then
          // run react-dropzone's own click handler to open the file picker.
          e.stopPropagation();
          rootProps.onClick?.(e);
        }}
      >
        {customButton ? customButton : <PlusIcon className="h-4 w-4" />}
      </button>
    </>
  );
});
