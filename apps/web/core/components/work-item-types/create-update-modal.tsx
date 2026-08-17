/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useState } from "react";
import { observer } from "mobx-react";
import { Controller, useForm } from "react-hook-form";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { EmojiIconPickerTypes, EmojiPicker, Logo } from "@plane/propel/emoji-icon-picker";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { TIssueType, TIssueTypePayload, TLogoProps } from "@plane/types";
import { EModalPosition, EModalWidth, ModalCore, Input, TextArea } from "@plane/ui";
// hooks
import { useIssueType } from "@/hooks/store/use-issue-type";

type TWorkItemTypeFormValues = {
  name: string;
  description: string;
  logo_props: TLogoProps;
};

const DEFAULT_LOGO: TLogoProps = {
  in_use: "icon",
  icon: { name: "Task", color: "#2563EB", package: "work-item-type" },
};

type Props = {
  isOpen: boolean;
  onClose: () => void;
  workspaceSlug: string;
  projectId: string;
  issueTypeToUpdate?: TIssueType;
};

export const CreateUpdateWorkItemTypeModal = observer(function CreateUpdateWorkItemTypeModal(props: Props) {
  const { isOpen, onClose, workspaceSlug, projectId, issueTypeToUpdate } = props;
  const { t } = useTranslation();
  const { createIssueType, updateIssueType } = useIssueType();
  const [isEmojiPickerOpen, setIsEmojiPickerOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const {
    control,
    handleSubmit,
    register,
    reset,
    formState: { errors },
  } = useForm<TWorkItemTypeFormValues>({
    defaultValues: { name: "", description: "", logo_props: DEFAULT_LOGO },
  });

  useEffect(() => {
    if (!isOpen) return;
    reset({
      name: issueTypeToUpdate?.name ?? "",
      description: issueTypeToUpdate?.description ?? "",
      logo_props: issueTypeToUpdate?.logo_props ?? DEFAULT_LOGO,
    });
  }, [isOpen, issueTypeToUpdate, reset]);

  const handleClose = () => {
    onClose();
    setIsEmojiPickerOpen(false);
  };

  const onSubmit = async (data: TWorkItemTypeFormValues) => {
    setIsSubmitting(true);
    const payload: TIssueTypePayload = {
      name: data.name.trim(),
      description: data.description,
      logo_props: data.logo_props,
    };
    try {
      if (issueTypeToUpdate) {
        await updateIssueType(workspaceSlug, projectId, issueTypeToUpdate.id, payload);
      } else {
        await createIssueType(workspaceSlug, projectId, payload);
      }
      handleClose();
    } catch (error: any) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("common.error.label"),
        message: error?.name?.[0] ?? error?.error ?? t("common.error.message"),
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <ModalCore isOpen={isOpen} handleClose={handleClose} position={EModalPosition.CENTER} width={EModalWidth.LG}>
      <form onSubmit={handleSubmit(onSubmit)}>
        <div className="space-y-4 p-5">
          <h3 className="text-h6-medium">
            {issueTypeToUpdate ? t("save") : t("add")} — {t("work_item_types.label")}
          </h3>
          <div className="flex items-start gap-3">
            <Controller
              control={control}
              name="logo_props"
              render={({ field: { value, onChange } }) => (
                <EmojiPicker
                  iconType="work-item-type"
                  closeOnSelect={false}
                  isOpen={isEmojiPickerOpen}
                  handleToggle={setIsEmojiPickerOpen}
                  className="flex items-center justify-center"
                  buttonClassName="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-sm border border-subtle bg-layer-2"
                  label={<Logo logo={value} size={20} />}
                  onChange={(val) => {
                    let logoValue = {};
                    if (val?.type === "emoji") logoValue = { value: val.value };
                    else if (val?.type === "icon") logoValue = val.value;
                    onChange({ in_use: val?.type, [val?.type]: logoValue });
                    setIsEmojiPickerOpen(false);
                  }}
                  defaultIconColor={value?.in_use === "icon" ? value?.icon?.color : undefined}
                  defaultOpen={value?.in_use === "icon" ? EmojiIconPickerTypes.ICON : EmojiIconPickerTypes.EMOJI}
                />
              )}
            />
            <div className="flex-grow">
              <Input
                id="name"
                type="text"
                placeholder={t("name")}
                className="w-full"
                hasError={!!errors.name}
                {...register("name", { required: true, maxLength: 255 })}
              />
            </div>
          </div>
          <TextArea
            id="description"
            placeholder={t("description")}
            className="w-full text-13"
            rows={3}
            {...register("description")}
          />
        </div>
        <div className="flex items-center justify-end gap-2 border-t border-subtle px-5 py-3">
          <Button variant="secondary" size="sm" onClick={handleClose} type="button">
            {t("cancel")}
          </Button>
          <Button variant="primary" size="sm" type="submit" loading={isSubmitting}>
            {t("save")}
          </Button>
        </div>
      </form>
    </ModalCore>
  );
});
