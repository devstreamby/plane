/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useParams } from "next/navigation";
import { observer } from "mobx-react";
// plane imports
import { Logo } from "@plane/propel/emoji-icon-picker";
import type { TIssueIdentifierProps, TIssueTypeIdentifier } from "@plane/types";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useIssueType } from "@/hooks/store/use-issue-type";
import { useProject } from "@/hooks/store/use-project";
import { IdentifierText } from "@/components/issues/issue-detail/identifier-text";

export const IssueIdentifier = observer(function IssueIdentifier(props: TIssueIdentifierProps) {
  const { projectId, variant, size, displayProperties, enableClickToCopyIdentifier = false } = props;
  // store hooks
  const { getProjectIdentifierById } = useProject();
  const {
    issue: { getIssueById },
  } = useIssueDetail();
  const { getIssueTypeById } = useIssueType();
  // Determine if the component is using store data or not
  const isUsingStoreData = "issueId" in props;
  // derived values
  const issue = isUsingStoreData ? getIssueById(props.issueId) : null;
  const projectIdentifier = isUsingStoreData ? getProjectIdentifierById(projectId) : props.projectIdentifier;
  const issueSequenceId = isUsingStoreData ? issue?.sequence_id : props.issueSequenceId;
  const issueTypeId = isUsingStoreData ? issue?.type_id : props.issueTypeId;
  const issueType = getIssueTypeById(projectId, issueTypeId);
  const shouldRenderIssueID = displayProperties ? displayProperties.key : true;
  const shouldRenderIssueType = (displayProperties ? displayProperties.issue_type : true) && !!issueType;

  if (!shouldRenderIssueID && !shouldRenderIssueType) return null;

  return (
    <div className="flex shrink-0 items-center space-x-2">
      {shouldRenderIssueType && issueType && <Logo logo={issueType.logo_props} size={14} />}
      {shouldRenderIssueID && (
        <IdentifierText
          identifier={`${projectIdentifier}-${issueSequenceId}`}
          enableClickToCopyIdentifier={enableClickToCopyIdentifier}
          variant={variant}
          size={size}
        />
      )}
    </div>
  );
});

export const IssueTypeIdentifier = observer(function IssueTypeIdentifier(props: TIssueTypeIdentifier) {
  const { issueTypeId, size } = props;
  const { projectId } = useParams<{ projectId: string }>();
  const { getIssueTypeById } = useIssueType();
  const issueType = getIssueTypeById(projectId, issueTypeId);

  if (!issueType) return null;

  return <Logo logo={issueType.logo_props} size={size === "lg" ? 16 : 14} />;
});
