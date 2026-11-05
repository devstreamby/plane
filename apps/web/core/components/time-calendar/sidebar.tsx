/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useRef, useState } from "react";
import { useTranslation } from "@plane/i18n";
import { cn, generateWorkItemLink } from "@plane/utils";
import type { TTimeCalendarLog } from "@/services/time-calendar.service";
import { formatDuration, toDateTimeLocalValue } from "./time";
import type { TPendingCreate, TRailIssue } from "./use-time-calendar";

type Props = {
  issueQuery: string;
  onIssueQuery: (value: string) => void;
  showNoMatches: boolean;
  searchIssues: TRailIssue[];
  pending: TPendingCreate | null;
  chosenIssueId: string | null;
  onPickIssue: (issue: TRailIssue) => void;
  selectedLog: TTimeCalendarLog | null;
  workspaceSlug: string;
  timeZone: string;
  onSave: (startedAt: string, hours: string, minutes: string) => void;
  onDelete: (log: TTimeCalendarLog) => void;
  issues: TRailIssue[];
};

function IssueChoice(props: { issue: TRailIssue; selected: boolean; onPick: (issue: TRailIssue) => void }) {
  const prefix = props.issue.identifier ? `${props.issue.identifier}-` : "";
  return (
    <button
      type="button"
      className={cn(
        "rounded-md px-2 py-1.5 text-left text-12 hover:bg-layer-1-hover",
        props.selected ? "bg-layer-1-selected text-primary" : "text-secondary"
      )}
      onClick={() => props.onPick(props.issue)}
    >
      {prefix}
      {props.issue.sequence_id} {props.issue.name}
    </button>
  );
}

function LogEditor(props: { log: TTimeCalendarLog; timeZone: string; onSave: Props["onSave"] }) {
  const { t } = useTranslation();
  const [startedAt, setStartedAt] = useState(() => toDateTimeLocalValue(props.log.started_at, props.timeZone));
  const [hours, setHours] = useState(() => String(Math.floor(props.log.duration_seconds / 3600)));
  const [minutes, setMinutes] = useState(() => String(Math.floor((props.log.duration_seconds % 3600) / 60)));

  return (
    <>
      <label className="flex flex-col gap-1 text-12 text-tertiary">
        {t("time_calendar.start")}
        <input
          type="datetime-local"
          value={startedAt}
          onChange={(event) => setStartedAt(event.target.value)}
          className="rounded-md border border-subtle bg-transparent px-2 py-1 text-12 text-primary"
        />
      </label>
      <div className="flex gap-2">
        <label className="flex flex-1 flex-col gap-1 text-12 text-tertiary">
          {t("time_calendar.hours")}
          <input
            type="number"
            min={0}
            value={hours}
            onChange={(event) => setHours(event.target.value)}
            className="rounded-md border border-subtle bg-transparent px-2 py-1 text-12 text-primary"
          />
        </label>
        <label className="flex flex-1 flex-col gap-1 text-12 text-tertiary">
          {t("time_calendar.minutes")}
          <input
            type="number"
            min={0}
            max={59}
            value={minutes}
            onChange={(event) => setMinutes(event.target.value)}
            className="rounded-md border border-subtle bg-transparent px-2 py-1 text-12 text-primary"
          />
        </label>
      </div>
      <button
        type="button"
        className="rounded-md bg-accent-primary px-2 py-1 text-12 font-medium text-on-color"
        onClick={() => props.onSave(startedAt, hours, minutes)}
      >
        {t("save")}
      </button>
    </>
  );
}

function SelectedLog(props: {
  log: TTimeCalendarLog;
  workspaceSlug: string;
  timeZone: string;
  onSave: Props["onSave"];
  onDelete: Props["onDelete"];
}) {
  const { t } = useTranslation();
  const running = !props.log.stopped_at;
  const workItemHref = generateWorkItemLink({
    workspaceSlug: props.workspaceSlug,
    projectId: props.log.project_id,
    issueId: props.log.issue_id,
    projectIdentifier: props.log.issue.project_identifier,
    sequenceId: props.log.issue.sequence_id,
  });
  return (
    <div className="space-y-2 rounded-md bg-layer-1 p-2">
      <a
        href={workItemHref}
        target="_blank"
        rel="noopener noreferrer"
        className="text-13 font-medium text-accent-primary hover:underline"
      >
        {props.log.issue.project_identifier}-{props.log.issue.sequence_id}
      </a>
      <div className="text-12 text-secondary">{props.log.issue.name}</div>
      {running ? (
        <p className="text-12 text-tertiary">{t("time_calendar.running")}</p>
      ) : (
        <LogEditor
          key={`${props.log.id}:${props.log.started_at}:${props.log.duration_seconds}:${props.timeZone}`}
          log={props.log}
          timeZone={props.timeZone}
          onSave={props.onSave}
        />
      )}
      {props.log.can_manage && (
        <button
          type="button"
          className="rounded-md px-2 py-1 text-12 text-danger-primary"
          onClick={() => props.onDelete(props.log)}
        >
          {t("delete")}
        </button>
      )}
    </div>
  );
}

export function TimeCalendarSidebar(props: Props) {
  const { t } = useTranslation();
  const searchRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (props.pending) searchRef.current?.focus();
  }, [props.pending]);

  return (
    <aside className="flex w-72 shrink-0 flex-col gap-3 overflow-y-auto rounded-md border border-subtle p-3">
      <p className="text-12 text-tertiary">{t("time_calendar.click_hint")}</p>
      <input
        ref={searchRef}
        value={props.issueQuery}
        onChange={(event) => props.onIssueQuery(event.target.value)}
        placeholder={t("time_calendar.search_issue")}
        aria-label={t("time_calendar.search_issue")}
        className="rounded-md border border-subtle bg-transparent px-2 py-1.5 text-12 text-primary outline-none"
      />
      {props.showNoMatches && <div className="text-12 text-tertiary">{t("time_calendar.no_matches")}</div>}
      {props.searchIssues.map((issue) => (
        <IssueChoice key={`search-${issue.id}`} issue={issue} selected={false} onPick={props.onPickIssue} />
      ))}
      {props.pending && (
        <div className="rounded-md bg-layer-1 p-2 text-12 text-secondary">
          {t("time_calendar.logged", { duration: formatDuration(props.pending.durationSeconds) })}
          <div className="text-tertiary">{props.pending.date}</div>
          {!props.chosenIssueId && <div className="mt-1">{t("time_calendar.select_issue")}</div>}
        </div>
      )}
      {props.selectedLog && (
        <SelectedLog
          log={props.selectedLog}
          workspaceSlug={props.workspaceSlug}
          timeZone={props.timeZone}
          onSave={props.onSave}
          onDelete={props.onDelete}
        />
      )}
      <div className="text-12 font-medium text-tertiary">{t("time_calendar.recent_issues")}</div>
      {props.issues.length === 0 ? (
        <div className="text-12 text-tertiary">{t("time_calendar.no_issues")}</div>
      ) : (
        props.issues.map((issue) => (
          <IssueChoice
            key={`recent-${issue.id}`}
            issue={issue}
            selected={props.chosenIssueId === issue.id}
            onPick={props.onPickIssue}
          />
        ))
      )}
    </aside>
  );
}
