/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { observer } from "mobx-react";
import useSWR from "swr";
import { useTranslation } from "@plane/i18n";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { cn } from "@plane/utils";
import useDebounce from "@/hooks/use-debounce";
import { useMember } from "@/hooks/store/use-member";
import { useProject } from "@/hooks/store/use-project";
import { useUser } from "@/hooks/store/user";
import { IssueService } from "@/services/issue";
import { timeCalendarService } from "@/services/time-calendar.service";
import type { TTimeCalendarLog } from "@/services/time-calendar.service";
import { UserService } from "@/services/user.service";
import { WorkspaceService } from "@/services/workspace.service";
import {
  addDays,
  browserTimeZone,
  capacitySeconds,
  formatDuration,
  formatWeekRange,
  isClockLog,
  toDateTimeLocalValue,
  localDateKey,
  loggedSeconds,
  startOfWeekMonday,
  timezoneLabel,
  wallTimeAsLocalDate,
} from "./time";
import { TimeWeekGrid } from "./week-grid";

type TRailIssue = {
  id: string;
  name: string;
  sequence_id: number;
  project_id: string;
  identifier?: string;
};

type TPendingCreate = {
  date: string;
  durationSeconds: number;
  startedAt: string;
};

type Props = {
  workspaceSlug: string;
  mode: "self" | "team";
};

const issueService = new IssueService();
const userService = new UserService();
const workspaceService = new WorkspaceService();

export const TimeCalendarRoot = observer(function TimeCalendarRoot(props: Props) {
  const { workspaceSlug, mode } = props;
  const { t, currentLocale } = useTranslation();
  const { data: currentUser } = useUser();
  const { getProjectById } = useProject();
  const { getUserDetails, workspace: workspaceMembers } = useMember();
  const currentUserId = currentUser?.id ?? "";
  const [timeZone, setTimeZone] = useState("UTC");
  const [zoneReady, setZoneReady] = useState(false);
  const [weekStart, setWeekStart] = useState<Date | null>(null);
  const [issueQuery, setIssueQuery] = useState("");
  const [selectedUserId, setSelectedUserId] = useState(currentUserId);
  const [chosenIssue, setChosenIssue] = useState<TRailIssue | null>(null);
  const [pending, setPending] = useState<TPendingCreate | null>(null);
  const [selectedLog, setSelectedLog] = useState<TTimeCalendarLog | null>(null);
  const [editStartedAt, setEditStartedAt] = useState("");
  const [editHours, setEditHours] = useState("0");
  const [editMinutes, setEditMinutes] = useState("0");
  const savingRef = useRef(false);
  const placementAttempt = useRef<Record<string, number>>({});
  const searchRef = useRef<HTMLInputElement>(null);
  const [placed, setPlaced] = useState<
    Record<string, Pick<TTimeCalendarLog, "date" | "started_at" | "stopped_at" | "duration_seconds">>
  >({});
  const [drafts, setDrafts] = useState<TTimeCalendarLog[]>([]);
  const [now, setNow] = useState(() => new Date());
  const debouncedQuery = useDebounce(issueQuery, 250);

  useEffect(() => {
    const zone = browserTimeZone();
    setTimeZone(zone);
    setNow(wallTimeAsLocalDate(new Date().toISOString(), zone));
    setZoneReady(true);
  }, []);

  useEffect(() => {
    if (currentUserId && !selectedUserId) setSelectedUserId(currentUserId);
  }, [currentUserId, selectedUserId]);

  useEffect(() => {
    if (!zoneReady || weekStart) return;
    setWeekStart(startOfWeekMonday(wallTimeAsLocalDate(new Date().toISOString(), timeZone)));
  }, [timeZone, weekStart, zoneReady]);

  useEffect(() => {
    if (pending) searchRef.current?.focus();
  }, [pending]);

  useEffect(() => {
    const interval = setInterval(() => {
      setNow(wallTimeAsLocalDate(new Date().toISOString(), timeZone));
    }, 60_000);
    return () => clearInterval(interval);
  }, [timeZone]);

  const viewedUserId = mode === "self" ? currentUserId : selectedUserId;
  const viewingOther = mode === "team" && !!viewedUserId && viewedUserId !== currentUserId;
  const weekEnd = weekStart ? addDays(weekStart, 6) : null;
  const startDate = weekStart ? localDateKey(weekStart) : "";
  const endDate = weekEnd ? localDateKey(weekEnd) : "";

  const { data, error, isLoading, mutate } = useSWR(
    viewedUserId && startDate ? ["time-calendar", workspaceSlug, viewedUserId, startDate, endDate] : null,
    () =>
      timeCalendarService.getTimeLogs(workspaceSlug, {
        start_date: startDate,
        end_date: endDate,
        user_id: viewedUserId,
      })
  );

  const { data: issueResponse } = useSWR(
    viewedUserId ? ["time-calendar-issues", workspaceSlug, viewedUserId] : null,
    () =>
      userService.getUserProfileIssues(workspaceSlug, viewedUserId, {
        assignees: viewedUserId,
        order_by: "-updated_at",
        per_page: 20,
      })
  );

  const { data: searchData } = useSWR(
    debouncedQuery.trim().length > 0 ? ["time-calendar-search", workspaceSlug, debouncedQuery.trim()] : null,
    () => workspaceService.searchWorkspace(workspaceSlug, { search: debouncedQuery.trim(), workspace_search: true })
  );

  const editableProjectIds = useMemo(() => new Set(data?.editable_project_ids ?? []), [data?.editable_project_ids]);
  const searchIssues = (searchData?.results?.issue ?? []).filter(
    (issue) => !viewingOther || editableProjectIds.has(issue.project_id)
  );
  const issues = useMemo(() => {
    const seen = new Set<string>();
    const fromLogs: TRailIssue[] = [];
    for (const log of data?.logs ?? []) {
      if (seen.has(log.issue_id)) continue;
      if (viewingOther && !editableProjectIds.has(log.project_id)) continue;
      seen.add(log.issue_id);
      fromLogs.push({
        id: log.issue_id,
        name: log.issue.name,
        sequence_id: log.issue.sequence_id,
        project_id: log.project_id,
        identifier: log.issue.project_identifier,
      });
    }
    const results = issueResponse?.results;
    const assigned = ((Array.isArray(results) ? results : []) as TRailIssue[]).filter((issue) => {
      if (seen.has(issue.id)) return false;
      if (viewingOther && !editableProjectIds.has(issue.project_id)) return false;
      seen.add(issue.id);
      return true;
    });
    return [...fromLogs, ...assigned].slice(0, 20);
  }, [data?.logs, editableProjectIds, issueResponse?.results, viewingOther]);

  const logs = useMemo(() => {
    const server = (data?.logs ?? []).map((log) => {
      const patch = placed[log.id];
      return patch ? Object.assign({}, log, patch) : log;
    });
    const visibleDrafts = drafts.filter(
      (draft) =>
        !server.some(
          (log) =>
            log.issue_id === draft.issue_id &&
            log.duration_seconds === draft.duration_seconds &&
            Math.abs(new Date(log.started_at).getTime() - new Date(draft.started_at).getTime()) < 2000
        )
    );
    return [...server, ...visibleDrafts];
  }, [data?.logs, drafts, placed]);
  const forbidden = (error as { code?: string } | undefined)?.code === "forbidden";
  const workingHoursEnabled = !!data?.working_hours?.enabled;
  const logged = weekStart && data ? loggedSeconds(logs, weekStart, timeZone, now) : 0;
  const capacity = data ? capacitySeconds(data.schedule, workingHoursEnabled) : 0;
  const memberIds = workspaceMembers.workspaceMemberIds ?? [];

  const refresh = async () => {
    await mutate();
  };

  const fail = (key: "time_calendar.save_error" | "time_calendar.delete_error") => {
    setToast({ type: TOAST_TYPE.ERROR, title: t(key) });
  };

  const createLog = async (issue: TRailIssue, draft: TPendingCreate) => {
    if (savingRef.current) return;
    savingRef.current = true;
    const tempId = `draft-${issue.id}-${draft.startedAt}`;
    const optimistic: TTimeCalendarLog = {
      id: tempId,
      project_id: issue.project_id,
      issue_id: issue.id,
      user_id: viewingOther ? viewedUserId : currentUserId || null,
      date: draft.date,
      started_at: draft.startedAt,
      stopped_at: new Date(new Date(draft.startedAt).getTime() + draft.durationSeconds * 1000).toISOString(),
      duration_seconds: draft.durationSeconds,
      stop_reason: "manual_entry",
      can_manage: false,
      issue: {
        name: issue.name,
        sequence_id: issue.sequence_id,
        project_identifier: issue.identifier ?? getProjectById(issue.project_id)?.identifier ?? "",
      },
    };
    setDrafts((current) => [...current.filter((item) => item.id !== tempId), optimistic]);
    setChosenIssue(null);
    setIssueQuery("");
    setPending(null);
    setSelectedLog(null);
    try {
      await issueService.createTimeLog(workspaceSlug, issue.project_id, issue.id, {
        date: draft.date,
        duration_seconds: draft.durationSeconds,
        started_at: draft.startedAt,
        ...(viewingOther ? { user_id: viewedUserId } : {}),
      });
      await refresh();
      setDrafts((current) => current.filter((item) => item.id !== tempId));
    } catch {
      setDrafts((current) => current.filter((item) => item.id !== tempId));
      setPending(draft);
      fail("time_calendar.save_error");
    } finally {
      savingRef.current = false;
    }
  };

  const onCreateRange = (date: string, durationSeconds: number, startedAt: string) => {
    const draft = { date, durationSeconds, startedAt };
    setSelectedLog(null);
    setPending(draft);
    if (chosenIssue) void createLog(chosenIssue, draft);
  };

  const pickIssue = (issue: TRailIssue) => {
    setChosenIssue(issue);
    if (pending) void createLog(issue, pending);
  };

  const rememberPlacement = (log: TTimeCalendarLog, date: string, durationSeconds: number, startedAt: string) => {
    const token = (placementAttempt.current[log.id] ?? 0) + 1;
    placementAttempt.current[log.id] = token;
    const stoppedAt = new Date(new Date(startedAt).getTime() + durationSeconds * 1000).toISOString();
    setPlaced((current) => ({
      ...current,
      [log.id]: { date, duration_seconds: durationSeconds, started_at: startedAt, stopped_at: stoppedAt },
    }));
    return token;
  };

  const forgetPlacement = (logId: string, token: number) => {
    if (placementAttempt.current[logId] !== token) return;
    setPlaced((current) => {
      if (!current[logId]) return current;
      const next = { ...current };
      delete next[logId];
      return next;
    });
  };

  const onMoveDuration = async (log: TTimeCalendarLog, date: string, startedAt: string) => {
    const token = rememberPlacement(log, date, log.duration_seconds, startedAt);
    try {
      await issueService.updateTimeLog(workspaceSlug, log.project_id, log.issue_id, log.id, {
        date,
        duration_seconds: log.duration_seconds,
        started_at: startedAt,
      });
    } catch {
      forgetPlacement(log.id, token);
      fail("time_calendar.save_error");
    }
  };

  const onResizeDuration = async (log: TTimeCalendarLog, date: string, durationSeconds: number, startedAt: string) => {
    const token = rememberPlacement(log, date, durationSeconds, startedAt);
    try {
      await issueService.updateTimeLog(workspaceSlug, log.project_id, log.issue_id, log.id, {
        date,
        duration_seconds: durationSeconds,
        started_at: startedAt,
      });
    } catch {
      forgetPlacement(log.id, token);
      fail("time_calendar.save_error");
    }
  };

  const openLog = (log: TTimeCalendarLog) => {
    setPending(null);
    setSelectedLog(log);
    setEditStartedAt(toDateTimeLocalValue(log.started_at, timeZone));
    setEditHours(String(Math.floor(log.duration_seconds / 3600)));
    setEditMinutes(String(Math.floor((log.duration_seconds % 3600) / 60)));
  };

  const liveSelected = selectedLog ? (logs.find((log) => log.id === selectedLog.id) ?? selectedLog) : null;

  useEffect(() => {
    if (!liveSelected || isClockLog(liveSelected)) return;
    setEditStartedAt(toDateTimeLocalValue(liveSelected.started_at, timeZone));
    setEditHours(String(Math.floor(liveSelected.duration_seconds / 3600)));
    setEditMinutes(String(Math.floor((liveSelected.duration_seconds % 3600) / 60)));
  }, [liveSelected, timeZone]);

  const saveLog = async () => {
    if (!selectedLog || isClockLog(selectedLog)) return;
    const durationSeconds = (Number(editHours) || 0) * 3600 + (Number(editMinutes) || 0) * 60;
    const started = new Date(editStartedAt);
    if (durationSeconds <= 0 || Number.isNaN(started.getTime())) return;
    const date = editStartedAt.slice(0, 10);
    const startedAt = started.toISOString();
    const token = rememberPlacement(selectedLog, date, durationSeconds, startedAt);
    try {
      await issueService.updateTimeLog(workspaceSlug, selectedLog.project_id, selectedLog.issue_id, selectedLog.id, {
        date,
        duration_seconds: durationSeconds,
        started_at: startedAt,
      });
      setSelectedLog(null);
      await refresh();
    } catch {
      forgetPlacement(selectedLog.id, token);
      fail("time_calendar.save_error");
    }
  };

  const deleteLog = async (log: TTimeCalendarLog) => {
    try {
      await issueService.deleteTimeLog(workspaceSlug, log.project_id, log.issue_id, log.id);
      setSelectedLog(null);
      await refresh();
    } catch {
      fail("time_calendar.delete_error");
    }
  };

  return (
    <div className="flex h-full min-h-0 w-full flex-col gap-3 px-page-x py-page-y">
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-1">
          <button
            type="button"
            className="rounded-md border border-subtle px-2 py-1 text-12 text-secondary hover:text-primary"
            onClick={() => weekStart && setWeekStart(addDays(weekStart, -7))}
          >
            {"<"}
          </button>
          <button
            type="button"
            className="rounded-md border border-subtle px-2 py-1 text-12 text-secondary hover:text-primary"
            onClick={() => weekStart && setWeekStart(addDays(weekStart, 7))}
          >
            {">"}
          </button>
          <button
            type="button"
            className="rounded-md border border-subtle px-2.5 py-1 text-12 font-medium text-secondary hover:text-primary"
            onClick={() => setWeekStart(startOfWeekMonday(wallTimeAsLocalDate(new Date().toISOString(), timeZone)))}
          >
            {t("time_calendar.today")}
          </button>
        </div>
        {weekStart && weekEnd && (
          <span className="text-13 font-medium text-primary">{formatWeekRange(weekStart, weekEnd, currentLocale)}</span>
        )}
        <span className="text-13 text-secondary">
          {capacity > 0
            ? t("time_calendar.week_total", { logged: formatDuration(logged), capacity: formatDuration(capacity) })
            : t("time_calendar.week_total_only", { logged: formatDuration(logged) })}
        </span>
        {zoneReady && (
          <span className="text-12 text-tertiary">
            {t("time_calendar.timezone_note", { timezone: timezoneLabel(timeZone, currentLocale) })}
          </span>
        )}
        {mode === "team" && (
          <label className="ml-auto flex items-center gap-2 text-12 text-tertiary">
            {t("time_calendar.member")}
            <select
              className="rounded-md border border-subtle bg-transparent px-2 py-1 text-12 text-primary"
              value={viewedUserId}
              onChange={(event) => {
                setSelectedUserId(event.target.value);
                setChosenIssue(null);
                setSelectedLog(null);
                setPending(null);
              }}
            >
              {memberIds.map((memberId) => (
                <option key={memberId} value={memberId}>
                  {getUserDetails(memberId)?.display_name ?? memberId}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>

      {forbidden ? (
        <div className="flex h-64 items-center justify-center text-13 text-tertiary">
          {t("time_calendar.forbidden")}
        </div>
      ) : error ? (
        <div className="flex h-64 items-center justify-center text-13 text-tertiary">
          {t("time_calendar.load_error")}
        </div>
      ) : (
        <div className="flex min-h-0 flex-1 gap-3">
          <div className="min-h-0 min-w-0 flex-1">
            {isLoading || !weekStart || !data ? (
              <div className="flex h-full items-center justify-center text-13 text-tertiary">{t("loading")}</div>
            ) : (
              <TimeWeekGrid
                logs={logs}
                weekStart={weekStart}
                timeZone={timeZone}
                now={now}
                schedule={data.schedule}
                workingHoursEnabled={workingHoursEnabled}
                locale={currentLocale}
                onCreateRange={onCreateRange}
                onMoveDuration={(log, date, startedAt) => void onMoveDuration(log, date, startedAt)}
                onResizeDuration={(log, date, durationSeconds, startedAt) =>
                  void onResizeDuration(log, date, durationSeconds, startedAt)
                }
                onSelectLog={openLog}
              />
            )}
          </div>
          <aside className="flex w-72 shrink-0 flex-col gap-3 overflow-y-auto rounded-md border border-subtle p-3">
            <p className="text-12 text-tertiary">{t("time_calendar.click_hint")}</p>
            <input
              ref={searchRef}
              value={issueQuery}
              onChange={(event) => setIssueQuery(event.target.value)}
              placeholder={t("time_calendar.search_issue")}
              className="rounded-md border border-subtle bg-transparent px-2 py-1.5 text-12 text-primary outline-none"
            />
            {issueQuery.trim().length > 0 &&
              issueQuery.trim() === debouncedQuery.trim() &&
              searchData &&
              searchIssues.length === 0 && <div className="text-12 text-tertiary">{t("time_calendar.no_matches")}</div>}
            {searchIssues.map((issue) => (
              <button
                key={`search-${issue.id}`}
                type="button"
                className="rounded-md px-2 py-1.5 text-left text-12 text-secondary hover:bg-layer-1-hover"
                onClick={() =>
                  pickIssue({
                    id: issue.id,
                    name: issue.name,
                    sequence_id: issue.sequence_id,
                    project_id: issue.project_id,
                    identifier: issue.project__identifier,
                  })
                }
              >
                {issue.project__identifier}-{issue.sequence_id} {issue.name}
              </button>
            ))}
            {pending && (
              <div className="rounded-md bg-layer-1 p-2 text-12 text-secondary">
                {t("time_calendar.logged", { duration: formatDuration(pending.durationSeconds) })}
                <div className="text-tertiary">{pending.date}</div>
                {!chosenIssue && <div className="mt-1">{t("time_calendar.select_issue")}</div>}
              </div>
            )}
            {selectedLog && (
              <div className="space-y-2 rounded-md bg-layer-1 p-2">
                <div className="text-13 font-medium text-primary">
                  {selectedLog.issue.project_identifier}-{selectedLog.issue.sequence_id}
                </div>
                <div className="text-12 text-secondary">{selectedLog.issue.name}</div>
                {isClockLog(selectedLog) ? (
                  <p className="text-12 text-tertiary">
                    {selectedLog.stopped_at ? t("time_calendar.clock_event") : t("time_calendar.running")}
                  </p>
                ) : (
                  <>
                    <label className="flex flex-col gap-1 text-12 text-tertiary">
                      {t("time_calendar.start")}
                      <input
                        type="datetime-local"
                        value={editStartedAt}
                        onChange={(event) => setEditStartedAt(event.target.value)}
                        className="rounded-md border border-subtle bg-transparent px-2 py-1 text-12 text-primary"
                      />
                    </label>
                    <div className="flex gap-2">
                      <label className="flex flex-1 flex-col gap-1 text-12 text-tertiary">
                        {t("time_calendar.hours")}
                        <input
                          type="number"
                          min={0}
                          value={editHours}
                          onChange={(event) => setEditHours(event.target.value)}
                          className="rounded-md border border-subtle bg-transparent px-2 py-1 text-12 text-primary"
                        />
                      </label>
                      <label className="flex flex-1 flex-col gap-1 text-12 text-tertiary">
                        {t("time_calendar.minutes")}
                        <input
                          type="number"
                          min={0}
                          max={59}
                          value={editMinutes}
                          onChange={(event) => setEditMinutes(event.target.value)}
                          className="rounded-md border border-subtle bg-transparent px-2 py-1 text-12 text-primary"
                        />
                      </label>
                    </div>
                    <button
                      type="button"
                      className="rounded-md bg-accent-primary px-2 py-1 text-12 font-medium text-on-color"
                      onClick={() => void saveLog()}
                    >
                      {t("save")}
                    </button>
                  </>
                )}
                {selectedLog.can_manage && (
                  <button
                    type="button"
                    className="rounded-md px-2 py-1 text-12 text-danger-primary"
                    onClick={() => void deleteLog(selectedLog)}
                  >
                    {t("delete")}
                  </button>
                )}
              </div>
            )}
            <div className="text-12 font-medium text-tertiary">{t("time_calendar.recent_issues")}</div>
            {issues.length === 0 ? (
              <div className="text-12 text-tertiary">{t("time_calendar.no_issues")}</div>
            ) : (
              issues.map((issue) => {
                const identifier = issue.identifier ?? getProjectById(issue.project_id)?.identifier;
                const label = `${identifier ? `${identifier}-` : ""}${issue.sequence_id} ${issue.name}`;
                return (
                  <button
                    key={`recent-${issue.id}`}
                    type="button"
                    className={cn(
                      "rounded-md px-2 py-1.5 text-left text-12 hover:bg-layer-1-hover",
                      chosenIssue?.id === issue.id ? "bg-layer-1-selected text-primary" : "text-secondary"
                    )}
                    onClick={() => pickIssue(issue)}
                  >
                    {label}
                  </button>
                );
              })
            )}
          </aside>
        </div>
      )}
    </div>
  );
});
