/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { Checkbox, CustomSelect, EModalPosition, EModalWidth, ModalCore } from "@plane/ui";
import { downloadBlob } from "@plane/utils";
// hooks
import useLocalStorage from "@/hooks/use-local-storage";
// services
import { CycleService } from "@/services/cycle.service";

type TExportFormat = "csv" | "markdown";

const EXPORT_FORMATS: { key: TExportFormat; label: string }[] = [
  { key: "csv", label: "CSV" },
  { key: "markdown", label: "Markdown" },
];

// key: the API field name. i18n: label shown in the modal. Order here is the export column order.
const MANDATORY_FIELDS = [
  { key: "identifier", i18n: "project_cycles.export_modal.fields.identifier" },
  { key: "name", i18n: "project_cycles.export_modal.fields.name" },
  { key: "description", i18n: "project_cycles.export_modal.fields.description" },
] as const;

const OPTIONAL_FIELDS = [
  { key: "state_name", i18n: "project_cycles.export_modal.fields.state_name" },
  { key: "priority", i18n: "project_cycles.export_modal.fields.priority" },
  { key: "assignees", i18n: "project_cycles.export_modal.fields.assignees" },
  { key: "subscribers", i18n: "project_cycles.export_modal.fields.subscribers" },
  { key: "labels", i18n: "project_cycles.export_modal.fields.labels" },
  { key: "cycles", i18n: "project_cycles.export_modal.fields.cycles" },
  { key: "modules", i18n: "project_cycles.export_modal.fields.modules" },
  { key: "estimate", i18n: "project_cycles.export_modal.fields.estimate" },
  { key: "start_date", i18n: "project_cycles.export_modal.fields.start_date" },
  { key: "target_date", i18n: "project_cycles.export_modal.fields.target_date" },
  { key: "completed_at", i18n: "project_cycles.export_modal.fields.completed_at" },
  { key: "created_at", i18n: "project_cycles.export_modal.fields.created_at" },
  { key: "updated_at", i18n: "project_cycles.export_modal.fields.updated_at" },
  { key: "created_by_name", i18n: "project_cycles.export_modal.fields.created_by_name" },
  { key: "parent", i18n: "project_cycles.export_modal.fields.parent" },
  { key: "links", i18n: "project_cycles.export_modal.fields.links" },
  { key: "relations", i18n: "project_cycles.export_modal.fields.relations" },
  { key: "comments", i18n: "project_cycles.export_modal.fields.comments" },
  { key: "sub_issues_count", i18n: "project_cycles.export_modal.fields.sub_issues_count" },
  { key: "link_count", i18n: "project_cycles.export_modal.fields.link_count" },
  { key: "attachment_count", i18n: "project_cycles.export_modal.fields.attachment_count" },
] as const;

const cycleExportService = new CycleService();

type Props = {
  isOpen: boolean;
  handleClose: () => void;
  workspaceSlug: string;
  projectId: string;
  cycleId: string;
  cycleName: string;
};

export const CycleExportModal = observer(function CycleExportModal(props: Props) {
  const { isOpen, handleClose, workspaceSlug, projectId, cycleId, cycleName } = props;
  // i18n
  const { t } = useTranslation();
  // states
  const [format, setFormat] = useState<TExportFormat>("csv");
  const [isExporting, setIsExporting] = useState(false);
  // persisted column selection, shared across cycles
  const { storedValue: selectedOptionalFields, setValue: setSelectedOptionalFields } = useLocalStorage<string[]>(
    "cycle_export_columns",
    []
  );
  const optionalFields = selectedOptionalFields ?? [];

  const toggleField = (key: string) => {
    setSelectedOptionalFields(
      optionalFields.includes(key) ? optionalFields.filter((f) => f !== key) : [...optionalFields, key]
    );
  };

  const handleExport = async () => {
    setIsExporting(true);
    try {
      const fields = [...MANDATORY_FIELDS.map((f) => f.key), ...optionalFields];
      const { blob, filename } = await cycleExportService.exportIssues(workspaceSlug, projectId, cycleId, {
        export_format: format,
        fields,
      });
      downloadBlob(blob, filename);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("project_cycles.export_modal.toasts.success.title"),
        message: t("project_cycles.export_modal.toasts.success.message"),
      });
      handleClose();
    } catch {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("error"),
        message: t("project_cycles.export_modal.toasts.error.message"),
      });
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <ModalCore isOpen={isOpen} handleClose={handleClose} position={EModalPosition.CENTER} width={EModalWidth.XL}>
      <div className="flex flex-col gap-4 p-6">
        <div>
          <h3 className="text-18 font-medium">{t("project_cycles.export_modal.title")}</h3>
          <p className="text-13 text-secondary">{cycleName}</p>
        </div>

        <div className="flex items-center justify-between gap-2">
          <span className="text-13 text-secondary">{t("project_cycles.export_modal.format")}</span>
          <CustomSelect
            value={format}
            onChange={(val: TExportFormat) => setFormat(val)}
            label={EXPORT_FORMATS.find((f) => f.key === format)?.label}
            buttonClassName="border-none"
            placement="bottom-end"
          >
            {EXPORT_FORMATS.map((f) => (
              <CustomSelect.Option key={f.key} value={f.key}>
                {f.label}
              </CustomSelect.Option>
            ))}
          </CustomSelect>
        </div>

        <div>
          <div className="mb-2 text-13 text-secondary">{t("project_cycles.export_modal.columns")}</div>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {MANDATORY_FIELDS.map((field) => (
              <label key={field.key} className="flex cursor-not-allowed items-center gap-2 text-13">
                <Checkbox checked disabled />
                {t(field.i18n)}
              </label>
            ))}
            {OPTIONAL_FIELDS.map((field) => (
              <label key={field.key} className="flex cursor-pointer items-center gap-2 text-13">
                <Checkbox checked={optionalFields.includes(field.key)} onChange={() => toggleField(field.key)} />
                {t(field.i18n)}
              </label>
            ))}
          </div>
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={handleClose}>
            {t("cancel")}
          </Button>
          <Button variant="primary" onClick={handleExport} disabled={isExporting} loading={isExporting}>
            {isExporting ? `${t("project_cycles.export_modal.exporting")}...` : t("project_cycles.export_modal.export")}
          </Button>
        </div>
      </div>
    </ModalCore>
  );
});
