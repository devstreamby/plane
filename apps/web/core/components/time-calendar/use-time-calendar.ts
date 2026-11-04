/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useMemo, useRef, useState, useSyncExternalStore } from "react";
import type { Dispatch, SetStateAction } from "react";
import useSWR from "swr";
import { useTranslation } from "@plane/i18n";
import type { IWorkspaceIssueSearchResult } from "@plane/types";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
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
  capacitySeconds,
  isClockLog,
  localDateKey,
  loggedSeconds,
  startOfWeekMonday,
  wallTimeAsLocalDate,
  zonedDateTimeToIso,
} from "./time";

export type TRailIssue = {
  id: string;
  name: string;
  sequence_id: number;
  project_id: string;
  identifier?: string;
};

export type TPendingCreate = {
  date: string;
  durationSeconds: number;
  startedAt: string;
};

type Placement = Pick<TTimeCalendarLog, "date" | "started_at" | "stopped_at" | "duration_seconds">;
type SetPlaced = Dispatch<SetStateAction<Record<string, Placement>>>;
type SetDrafts = Dispatch<SetStateAction<TTimeCalendarLog[]>>;

type CalendarMode = "self" | "team";

const issueService = new IssueService();
const userService = new UserService();
const workspaceService = new WorkspaceService();

const SERVER_NOW = new Date(0);
let nowSnapshot = SERVER_NOW;
let nowKey = "";

function subscribeNow(onStoreChange: () => void) {
  const interval = setInterval(onStoreChange, 60_000);
  return () => clearInterval(interval);
}

function getServerNow() {
  return SERVER_NOW;
}

function readZonedNow(timeZone: string) {
  const key = `${timeZone}:${Math.floor(Date.now() / 60_000)}`;
  if (key === nowKey) return nowSnapshot;
  nowKey = key;
  nowSnapshot = wallTimeAsLocalDate(new Date().toISOString(), timeZone);
  return nowSnapshot;
}

function useCalendarClock(timeZone: string) {
  const now = useSyncExternalStore(subscribeNow, () => readZonedNow(timeZone || "UTC"), getServerNow);
  const [chosenWeek, setChosenWeek] = useState<Date | null>(null);
  const defaultWeekStart = useMemo(() => {
    if (!timeZone) return null;
    return startOfWeekMonday(wallTimeAsLocalDate(new Date().toISOString(), timeZone));
  }, [timeZone]);

  return {
    timeZone,
    zoneReady: Boolean(timeZone),
    now,
    weekStart: chosenWeek ?? defaultWeekStart,
    setWeekStart: setChosenWeek,
  };
}

function resolveViewedUser(mode: CalendarMode, currentUserId: string, selectedUserId: string) {
  const viewedUserId = mode === "self" ? currentUserId : selectedUserId || currentUserId;
  return {
    viewedUserId,
    viewingOther: mode === "team" && viewedUserId !== "" && viewedUserId !== currentUserId,
  };
}

function weekRange(weekStart: Date | null) {
  if (!weekStart) return { weekEnd: null as Date | null, startDate: "", endDate: "" };
  const weekEnd = addDays(weekStart, 6);
  return { weekEnd, startDate: localDateKey(weekStart), endDate: localDateKey(weekEnd) };
}

function isForbiddenError(error: unknown) {
  if (typeof error !== "object" || error === null || !("code" in error)) return false;
  return error.code === "forbidden";
}

function asRailIssues(results: unknown): TRailIssue[] {
  if (!Array.isArray(results)) return [];
  return results as TRailIssue[];
}

function withIdentifier(issue: TRailIssue, identifierFor: (projectId: string) => string | undefined): TRailIssue {
  if (issue.identifier) return issue;
  return Object.assign({}, issue, { identifier: identifierFor(issue.project_id) });
}

function buildRailIssues(
  logs: TTimeCalendarLog[],
  assigned: TRailIssue[],
  viewingOther: boolean,
  editable: Set<string>,
  identifierFor: (projectId: string) => string | undefined
) {
  const seen = new Set<string>();
  const fromLogs: TRailIssue[] = [];
  for (const log of logs) {
    if (seen.has(log.issue_id) || (viewingOther && !editable.has(log.project_id))) continue;
    seen.add(log.issue_id);
    fromLogs.push({
      id: log.issue_id,
      name: log.issue.name,
      sequence_id: log.issue.sequence_id,
      project_id: log.project_id,
      identifier: log.issue.project_identifier,
    });
  }
  const extras: TRailIssue[] = [];
  for (const issue of assigned) {
    if (seen.has(issue.id) || (viewingOther && !editable.has(issue.project_id))) continue;
    seen.add(issue.id);
    extras.push(issue);
  }
  return [...fromLogs, ...extras].slice(0, 20).map((issue) => withIdentifier(issue, identifierFor));
}

function filterSearchIssues(issues: IWorkspaceIssueSearchResult[], viewingOther: boolean, editable: Set<string>) {
  const visible = viewingOther ? issues.filter((issue) => editable.has(issue.project_id)) : issues;
  return visible.map((issue) => ({
    id: issue.id,
    name: issue.name,
    sequence_id: issue.sequence_id,
    project_id: issue.project_id,
    identifier: issue.project__identifier,
  }));
}

function sameDraft(log: TTimeCalendarLog, draft: TTimeCalendarLog) {
  return (
    log.issue_id === draft.issue_id &&
    log.duration_seconds === draft.duration_seconds &&
    Math.abs(new Date(log.started_at).getTime() - new Date(draft.started_at).getTime()) < 2000
  );
}

function mergeCalendarLogs(
  serverLogs: TTimeCalendarLog[] | undefined,
  placed: Record<string, Placement>,
  drafts: TTimeCalendarLog[]
) {
  const server = (serverLogs ?? []).map((log) => {
    const patch = placed[log.id];
    return patch ? Object.assign({}, log, patch) : log;
  });
  const visibleDrafts = drafts.filter((draft) => !server.some((log) => sameDraft(log, draft)));
  return [...server, ...visibleDrafts];
}

function findSelected(logs: TTimeCalendarLog[], selected: TTimeCalendarLog | null) {
  if (!selected) return null;
  return logs.find((log) => log.id === selected.id) ?? selected;
}

function memberOptions(
  mode: CalendarMode,
  memberIds: string[] | null | undefined,
  labelFor: (memberId: string) => string
) {
  if (mode !== "team") return null;
  return (memberIds ?? []).map((id) => ({ id, label: labelFor(id) }));
}

function showNoMatches(query: string, debounced: string, hasResults: boolean, count: number) {
  const trimmed = query.trim();
  return trimmed.length > 0 && trimmed === debounced.trim() && hasResults && count === 0;
}

function fieldsToUpdate(startedAtLocal: string, hours: string, minutes: string, timeZone: string) {
  const durationSeconds = (Number(hours) || 0) * 3600 + (Number(minutes) || 0) * 60;
  const startedAt = zonedDateTimeToIso(startedAtLocal, timeZone);
  if (durationSeconds <= 0 || !startedAt) return null;
  return { date: startedAtLocal.slice(0, 10), durationSeconds, startedAt };
}

function draftLog(
  issue: TRailIssue,
  draft: TPendingCreate,
  userId: string | null,
  projectIdentifier: string
): TTimeCalendarLog {
  return {
    id: `draft-${issue.id}-${draft.startedAt}`,
    project_id: issue.project_id,
    issue_id: issue.id,
    user_id: userId,
    date: draft.date,
    started_at: draft.startedAt,
    stopped_at: new Date(new Date(draft.startedAt).getTime() + draft.durationSeconds * 1000).toISOString(),
    duration_seconds: draft.durationSeconds,
    stop_reason: "manual_entry",
    can_manage: false,
    issue: {
      name: issue.name,
      sequence_id: issue.sequence_id,
      project_identifier: projectIdentifier,
    },
  };
}

function takePlacement(
  attempts: { current: Record<string, number> },
  setPlaced: SetPlaced,
  log: TTimeCalendarLog,
  date: string,
  durationSeconds: number,
  startedAt: string
) {
  const token = (attempts.current[log.id] ?? 0) + 1;
  attempts.current[log.id] = token;
  const stoppedAt = new Date(new Date(startedAt).getTime() + durationSeconds * 1000).toISOString();
  setPlaced((current) => ({
    ...current,
    [log.id]: { date, duration_seconds: durationSeconds, started_at: startedAt, stopped_at: stoppedAt },
  }));
  return token;
}

function dropPlacement(
  attempts: { current: Record<string, number> },
  setPlaced: SetPlaced,
  logId: string,
  token: number
) {
  if (attempts.current[logId] !== token) return;
  setPlaced((current) => {
    if (!current[logId]) return current;
    const next = { ...current };
    delete next[logId];
    return next;
  });
}

async function submitCreate(input: {
  workspaceSlug: string;
  issue: TRailIssue;
  draft: TPendingCreate;
  userId: string | null;
  assignUserId?: string;
  projectIdentifier: string;
  saving: { current: boolean };
  setDrafts: SetDrafts;
  clearSelection: () => void;
  restorePending: (draft: TPendingCreate) => void;
  refresh: () => Promise<unknown>;
  onError: () => void;
}) {
  if (input.saving.current) return;
  input.saving.current = true;
  const optimistic = draftLog(input.issue, input.draft, input.userId, input.projectIdentifier);
  input.setDrafts((current) => [...current.filter((item) => item.id !== optimistic.id), optimistic]);
  input.clearSelection();
  try {
    await issueService.createTimeLog(input.workspaceSlug, input.issue.project_id, input.issue.id, {
      date: input.draft.date,
      duration_seconds: input.draft.durationSeconds,
      started_at: input.draft.startedAt,
      ...(input.assignUserId ? { user_id: input.assignUserId } : {}),
    });
    await input.refresh();
    input.setDrafts((current) => current.filter((item) => item.id !== optimistic.id));
  } catch {
    input.setDrafts((current) => current.filter((item) => item.id !== optimistic.id));
    input.restorePending(input.draft);
    input.onError();
  } finally {
    input.saving.current = false;
  }
}

async function removeLog(input: {
  workspaceSlug: string;
  log: TTimeCalendarLog;
  refresh: () => Promise<unknown>;
  clearSelected: () => void;
  onError: () => void;
}) {
  try {
    await issueService.deleteTimeLog(input.workspaceSlug, input.log.project_id, input.log.issue_id, input.log.id);
    input.clearSelected();
    await input.refresh();
  } catch {
    input.onError();
  }
}

async function persistLogUpdate(input: {
  workspaceSlug: string;
  log: TTimeCalendarLog;
  date: string;
  durationSeconds: number;
  startedAt: string;
  attempts: { current: Record<string, number> };
  setPlaced: SetPlaced;
  refresh?: () => Promise<unknown>;
  onSuccess?: () => void;
  onError: () => void;
}) {
  const token = takePlacement(
    input.attempts,
    input.setPlaced,
    input.log,
    input.date,
    input.durationSeconds,
    input.startedAt
  );
  try {
    await issueService.updateTimeLog(input.workspaceSlug, input.log.project_id, input.log.issue_id, input.log.id, {
      date: input.date,
      duration_seconds: input.durationSeconds,
      started_at: input.startedAt,
    });
  } catch {
    dropPlacement(input.attempts, input.setPlaced, input.log.id, token);
    input.onError();
    return;
  }
  try {
    await input.refresh?.();
  } finally {
    dropPlacement(input.attempts, input.setPlaced, input.log.id, token);
  }
  input.onSuccess?.();
}

function useCalendarData(
  workspaceSlug: string,
  viewedUserId: string,
  startDate: string,
  endDate: string,
  query: string
) {
  const logsKey = viewedUserId && startDate ? ["time-calendar", workspaceSlug, viewedUserId, startDate, endDate] : null;
  const logsQuery = useSWR(logsKey, () =>
    timeCalendarService.getTimeLogs(workspaceSlug, {
      start_date: startDate,
      end_date: endDate,
      user_id: viewedUserId,
    })
  );
  const issuesKey = viewedUserId ? ["time-calendar-issues", workspaceSlug, viewedUserId] : null;
  const issuesQuery = useSWR(issuesKey, () =>
    userService.getUserProfileIssues(workspaceSlug, viewedUserId, {
      assignees: viewedUserId,
      order_by: "-updated_at",
      per_page: 20,
    })
  );
  const trimmed = query.trim();
  const searchKey = trimmed.length > 0 ? ["time-calendar-search", workspaceSlug, trimmed] : null;
  const searchQuery = useSWR(searchKey, () =>
    workspaceService.searchWorkspace(workspaceSlug, { search: trimmed, workspace_search: true })
  );
  return {
    data: logsQuery.data,
    error: logsQuery.error as unknown,
    isLoading: logsQuery.isLoading,
    mutate: logsQuery.mutate,
    issueResponse: issuesQuery.data,
    searchData: searchQuery.data,
  };
}

export function useTimeCalendar(props: { workspaceSlug: string; mode: CalendarMode; timeZone: string }) {
  const { workspaceSlug, mode, timeZone } = props;
  const { t } = useTranslation();
  const { data: currentUser } = useUser();
  const { getProjectById } = useProject();
  const { getUserDetails, workspace: workspaceMembers } = useMember();
  const currentUserId = currentUser?.id ?? "";
  const clock = useCalendarClock(timeZone);
  const [issueQuery, setIssueQuery] = useState("");
  const [selectedUserId, setSelectedUserId] = useState("");
  const [chosenIssue, setChosenIssue] = useState<TRailIssue | null>(null);
  const [pending, setPending] = useState<TPendingCreate | null>(null);
  const [selectedLog, setSelectedLog] = useState<TTimeCalendarLog | null>(null);
  const savingRef = useRef(false);
  const placementAttempt = useRef<Record<string, number>>({});
  const [placed, setPlaced] = useState<Record<string, Placement>>({});
  const [drafts, setDrafts] = useState<TTimeCalendarLog[]>([]);
  const debouncedQuery = useDebounce(issueQuery, 250);
  const viewed = resolveViewedUser(mode, currentUserId, selectedUserId);
  const range = weekRange(clock.weekStart);
  const loaded = useCalendarData(workspaceSlug, viewed.viewedUserId, range.startDate, range.endDate, debouncedQuery);
  const logs = useMemo(() => mergeCalendarLogs(loaded.data?.logs, placed, drafts), [drafts, loaded.data?.logs, placed]);
  const editableProjectIds = new Set(loaded.data?.editable_project_ids ?? []);
  const identifierFor = (projectId: string) => getProjectById(projectId)?.identifier || undefined;
  const issues = buildRailIssues(
    loaded.data?.logs ?? [],
    asRailIssues(loaded.issueResponse?.results),
    viewed.viewingOther,
    editableProjectIds,
    identifierFor
  );
  const searchIssues = filterSearchIssues(
    loaded.searchData?.results?.issue ?? [],
    viewed.viewingOther,
    editableProjectIds
  );
  const workingHoursEnabled = !!loaded.data?.working_hours?.enabled;
  const logged = clock.weekStart && loaded.data ? loggedSeconds(logs, clock.weekStart, clock.timeZone, clock.now) : 0;
  const capacity = loaded.data ? capacitySeconds(loaded.data.schedule, workingHoursEnabled) : 0;
  const forbidden = isForbiddenError(loaded.error);
  const fail = (key: "time_calendar.save_error" | "time_calendar.delete_error") => {
    setToast({ type: TOAST_TYPE.ERROR, title: t(key) });
  };

  const refresh = () => loaded.mutate();
  const clearSelection = () => {
    setChosenIssue(null);
    setIssueQuery("");
    setPending(null);
    setSelectedLog(null);
  };
  const onError = () => fail("time_calendar.save_error");

  const createLog = (issue: TRailIssue, draft: TPendingCreate) => {
    void submitCreate({
      workspaceSlug,
      issue,
      draft,
      userId: viewed.viewingOther ? viewed.viewedUserId : currentUserId || null,
      assignUserId: viewed.viewingOther ? viewed.viewedUserId : undefined,
      projectIdentifier: issue.identifier ?? identifierFor(issue.project_id) ?? "",
      saving: savingRef,
      setDrafts,
      clearSelection,
      restorePending: setPending,
      refresh,
      onError,
    });
  };

  const onCreateRange = (date: string, durationSeconds: number, startedAt: string) => {
    const draft = { date, durationSeconds, startedAt };
    setSelectedLog(null);
    setPending(draft);
    if (chosenIssue) createLog(chosenIssue, draft);
  };

  const onPickIssue = (issue: TRailIssue) => {
    setChosenIssue(issue);
    if (pending) createLog(issue, pending);
  };

  const updateLog = (
    log: TTimeCalendarLog,
    date: string,
    durationSeconds: number,
    startedAt: string,
    refreshAfter: boolean
  ) => {
    void persistLogUpdate({
      workspaceSlug,
      log,
      date,
      durationSeconds,
      startedAt,
      attempts: placementAttempt,
      setPlaced,
      refresh,
      onSuccess: refreshAfter ? () => setSelectedLog(null) : undefined,
      onError,
    });
  };

  const saveLog = (startedAtLocal: string, hours: string, minutes: string) => {
    if (!selectedLog || isClockLog(selectedLog)) return;
    const update = fieldsToUpdate(startedAtLocal, hours, minutes, clock.timeZone);
    if (!update) return;
    updateLog(selectedLog, update.date, update.durationSeconds, update.startedAt, true);
  };

  const deleteLog = (log: TTimeCalendarLog) => {
    void removeLog({
      workspaceSlug,
      log,
      refresh,
      clearSelected: () => setSelectedLog(null),
      onError: () => fail("time_calendar.delete_error"),
    });
  };

  const shiftWeek = (days: number) => {
    if (!clock.weekStart) return;
    clock.setWeekStart(addDays(clock.weekStart, days));
  };

  return {
    timeZone: clock.timeZone,
    zoneReady: clock.zoneReady,
    now: clock.now,
    weekStart: clock.weekStart,
    weekEnd: range.weekEnd,
    logged,
    capacity,
    forbidden,
    hasError: Boolean(loaded.error) && !forbidden,
    members: memberOptions(
      mode,
      workspaceMembers.workspaceMemberIds,
      (memberId) => getUserDetails(memberId)?.display_name ?? memberId
    ),
    viewedUserId: viewed.viewedUserId,
    onSelectUser: (userId: string) => {
      setSelectedUserId(userId);
      setChosenIssue(null);
      setSelectedLog(null);
      setPending(null);
    },
    onPrevious: () => shiftWeek(-7),
    onNext: () => shiftWeek(7),
    onToday: () => clock.setWeekStart(startOfWeekMonday(wallTimeAsLocalDate(new Date().toISOString(), clock.timeZone))),
    grid:
      clock.weekStart && loaded.data && !loaded.isLoading
        ? {
            logs,
            weekStart: clock.weekStart,
            timeZone: clock.timeZone,
            now: clock.now,
            schedule: loaded.data.schedule,
            workingHoursEnabled,
            onCreateRange,
            onMoveDuration: (log: TTimeCalendarLog, date: string, startedAt: string) =>
              updateLog(log, date, log.duration_seconds, startedAt, false),
            onResizeDuration: (log: TTimeCalendarLog, date: string, durationSeconds: number, startedAt: string) =>
              updateLog(log, date, durationSeconds, startedAt, false),
            onSelectLog: (log: TTimeCalendarLog) => {
              setPending(null);
              setSelectedLog(log);
            },
          }
        : null,
    sidebar: {
      issueQuery,
      onIssueQuery: setIssueQuery,
      showNoMatches: showNoMatches(issueQuery, debouncedQuery, Boolean(loaded.searchData), searchIssues.length),
      searchIssues,
      pending,
      chosenIssueId: chosenIssue?.id ?? null,
      onPickIssue,
      selectedLog: findSelected(logs, selectedLog),
      timeZone: clock.timeZone,
      onSave: saveLog,
      onDelete: deleteLog,
      issues,
    },
  };
}
