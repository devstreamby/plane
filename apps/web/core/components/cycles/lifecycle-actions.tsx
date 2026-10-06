import { useState } from "react";
import { observer } from "mobx-react";
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { setToast, TOAST_TYPE } from "@plane/propel/toast";
import { ModalCore, EModalPosition, EModalWidth } from "@plane/ui";
import { useCycle } from "@/hooks/store/use-cycle";
import { useUserPermissions } from "@/hooks/store/user";

type Props = { workspaceSlug: string; projectId: string; cycleId: string };

export const CycleLifecycleActions = observer(function CycleLifecycleActions({
  workspaceSlug,
  projectId,
  cycleId,
}: Props) {
  const { getCycleById, transitionCycle } = useCycle();
  const { allowPermissions } = useUserPermissions();
  const { t } = useTranslation();
  const [busy, setBusy] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const cycle = getCycleById(cycleId);
  const status = cycle?.status?.toLowerCase();
  const allowed = allowPermissions(
    [EUserPermissions.ADMIN, EUserPermissions.MEMBER],
    EUserPermissionsLevel.PROJECT,
    workspaceSlug,
    projectId
  );

  const transition = async (action: "start" | "complete") => {
    setBusy(true);
    try {
      await transitionCycle(workspaceSlug, projectId, cycleId, action);
      setConfirm(false);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("project_cycles.action.update.success.title"),
        message: t("project_cycles.action.update.success.description"),
      });
    } catch {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("project_cycles.action.update.failed.title"),
        message: t("project_cycles.action.update.failed.description"),
      });
    } finally {
      setBusy(false);
    }
  };

  if (
    !allowed ||
    !cycle ||
    cycle.start_date ||
    cycle.end_date ||
    cycle.archived_at ||
    !["draft", "current"].includes(status ?? "")
  )
    return null;

  return (
    <>
      <Button
        variant="secondary"
        size="sm"
        loading={busy}
        onClick={(event) => {
          event.preventDefault();
          event.stopPropagation();
          if (status === "draft") void transition("start");
          else setConfirm(true);
        }}
      >
        {t(status === "draft" ? "cycle.manual.start" : "cycle.manual.complete")}
      </Button>
      <ModalCore
        isOpen={confirm}
        handleClose={() => {
          if (!busy) setConfirm(false);
        }}
        position={EModalPosition.CENTER}
        width={EModalWidth.LG}
      >
        <div className="space-y-4 p-5">
          <h3 className="text-18 font-medium">
            {t("cycle.manual.complete")}: {cycle.name}
          </h3>
          <p className="text-13 text-secondary">{t("cycle.manual.confirm")}</p>
          <div className="flex justify-end gap-2">
            <Button
              variant="secondary"
              size="lg"
              disabled={busy}
              onClick={(event) => {
                event.preventDefault();
                event.stopPropagation();
                setConfirm(false);
              }}
            >
              {t("common.cancel")}
            </Button>
            <Button
              variant="primary"
              size="lg"
              loading={busy}
              onClick={(event) => {
                event.preventDefault();
                event.stopPropagation();
                void transition("complete");
              }}
            >
              {t("cycle.manual.complete")}
            </Button>
          </div>
        </div>
      </ModalCore>
    </>
  );
});
