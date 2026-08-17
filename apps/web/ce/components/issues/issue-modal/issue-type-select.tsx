/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Controller } from "react-hook-form";
import type { Control } from "react-hook-form";
import { ChevronDownIcon } from "lucide-react";
// plane imports
import { Logo } from "@plane/propel/emoji-icon-picker";
import type { EditorRefApi } from "@plane/editor";
// types
import type { TBulkIssueProperties, TIssue } from "@plane/types";
// ui
import { CustomSearchSelect } from "@plane/ui";
import { cn } from "@plane/utils";
// hooks
import { useIssueType } from "@/hooks/store/use-issue-type";

export type TIssueFields = TIssue & TBulkIssueProperties;

export type TIssueTypeDropdownVariant = "xs" | "sm";

export type TIssueTypeSelectProps<T extends Partial<TIssueFields>> = {
  control: Control<T>;
  projectId: string | null;
  editorRef?: React.MutableRefObject<EditorRefApi | null>;
  disabled?: boolean;
  variant?: TIssueTypeDropdownVariant;
  placeholder?: string;
  isRequired?: boolean;
  renderChevron?: boolean;
  dropDownContainerClassName?: string;
  showMandatoryFieldInfo?: boolean; // Show info about mandatory fields
  handleFormChange?: () => void;
};

export function IssueTypeSelect<T extends Partial<TIssueFields>>(props: TIssueTypeSelectProps<T>) {
  const {
    control,
    projectId,
    disabled = false,
    placeholder = "Type",
    renderChevron = false,
    dropDownContainerClassName,
    handleFormChange,
  } = props;
  const { getProjectIssueTypes, getIssueTypeById } = useIssueType();

  const issueTypes = getProjectIssueTypes(projectId).filter((type) => type.is_active);
  if (issueTypes.length === 0) return null;

  return (
    <Controller
      control={control}
      name={"type_id" as never}
      render={({ field: { value, onChange } }) => {
        const selectedType = getIssueTypeById(projectId, value as string | null | undefined);
        const options = issueTypes.map((type) => ({
          value: type.id,
          query: type.name,
          content: (
            <div className="flex items-center gap-2">
              <Logo logo={type.logo_props} size={14} />
              <span className="truncate">{type.name}</span>
            </div>
          ),
        }));

        return (
          <div className={cn("h-7", dropDownContainerClassName)}>
            <CustomSearchSelect
              value={value as string | null | undefined}
              onChange={(val: string) => {
                onChange(val);
                handleFormChange?.();
              }}
              options={options}
              disabled={disabled}
              customButton={
                <button
                  type="button"
                  disabled={disabled}
                  className={cn(
                    "flex h-7 items-center gap-1.5 rounded-sm border-[0.5px] border-subtle bg-layer-2 px-2 py-0.5 text-body-xs-medium",
                    { "cursor-not-allowed opacity-60": disabled }
                  )}
                >
                  {selectedType ? (
                    <>
                      <Logo logo={selectedType.logo_props} size={14} />
                      <span className="truncate">{selectedType.name}</span>
                    </>
                  ) : (
                    <span className="text-placeholder">{placeholder}</span>
                  )}
                  {renderChevron && <ChevronDownIcon className="h-3 w-3 flex-shrink-0 text-tertiary" />}
                </button>
              }
            />
          </div>
        );
      }}
    />
  );
}
