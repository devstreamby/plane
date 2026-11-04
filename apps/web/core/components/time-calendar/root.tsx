/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { formatDuration, formatWeekRange, timezoneLabel } from "./time";
import { TimeCalendarSidebar } from "./sidebar";
import { useTimeCalendar } from "./use-time-calendar";
import { TimeWeekGrid } from "./week-grid";

type Props = {
  workspaceSlug: string;
  mode: "self" | "team";
  timeZone: string;
};

function TimeCalendarToolbar(props: { calendar: ReturnType<typeof useTimeCalendar>; locale: string }) {
  const { t } = useTranslation();
  const { calendar } = props;
  const total =
    calendar.capacity > 0
      ? t("time_calendar.week_total", {
          logged: formatDuration(calendar.logged),
          capacity: formatDuration(calendar.capacity),
        })
      : t("time_calendar.week_total_only", { logged: formatDuration(calendar.logged) });

  return (
    <div className="flex flex-wrap items-center gap-2">
      <div className="flex items-center gap-1">
        <button
          type="button"
          className="rounded-md border border-subtle px-2 py-1 text-12 text-secondary hover:text-primary"
          aria-label={t("time_calendar.previous_week")}
          onClick={calendar.onPrevious}
        >
          {"<"}
        </button>
        <button
          type="button"
          className="rounded-md border border-subtle px-2 py-1 text-12 text-secondary hover:text-primary"
          aria-label={t("time_calendar.next_week")}
          onClick={calendar.onNext}
        >
          {">"}
        </button>
        <button
          type="button"
          className="rounded-md border border-subtle px-2.5 py-1 text-12 font-medium text-secondary hover:text-primary"
          onClick={calendar.onToday}
        >
          {t("time_calendar.today")}
        </button>
      </div>
      {calendar.weekStart && calendar.weekEnd && (
        <span className="text-13 font-medium text-primary">
          {formatWeekRange(calendar.weekStart, calendar.weekEnd, props.locale)}
        </span>
      )}
      <span className="text-13 text-secondary">{total}</span>
      {calendar.zoneReady && (
        <span className="text-12 text-tertiary">
          {t("time_calendar.timezone_note", { timezone: timezoneLabel(calendar.timeZone, props.locale) })}
        </span>
      )}
      {calendar.members && (
        <label className="ml-auto flex items-center gap-2 text-12 text-tertiary">
          {t("time_calendar.member")}
          <select
            className="rounded-md border border-subtle bg-transparent px-2 py-1 text-12 text-primary"
            value={calendar.viewedUserId}
            onChange={(event) => calendar.onSelectUser(event.target.value)}
          >
            {calendar.members.map((member) => (
              <option key={member.id} value={member.id}>
                {member.label}
              </option>
            ))}
          </select>
        </label>
      )}
    </div>
  );
}

function TimeCalendarBody(props: { calendar: ReturnType<typeof useTimeCalendar>; locale: string }) {
  const { t } = useTranslation();
  const { calendar, locale } = props;
  if (calendar.forbidden) {
    return (
      <div className="flex h-64 items-center justify-center text-13 text-tertiary">{t("time_calendar.forbidden")}</div>
    );
  }
  if (calendar.hasError) {
    return (
      <div className="flex h-64 items-center justify-center text-13 text-tertiary">{t("time_calendar.load_error")}</div>
    );
  }
  return (
    <div className="flex min-h-0 flex-1 gap-3">
      <div className="min-h-0 min-w-0 flex-1">
        {calendar.grid ? (
          <TimeWeekGrid locale={locale} {...calendar.grid} />
        ) : (
          <div className="flex h-full items-center justify-center text-13 text-tertiary">{t("loading")}</div>
        )}
      </div>
      <TimeCalendarSidebar {...calendar.sidebar} />
    </div>
  );
}

export const TimeCalendarRoot = observer(function TimeCalendarRoot(props: Props) {
  const { currentLocale } = useTranslation();
  const calendar = useTimeCalendar(props);

  return (
    <div className="flex h-full min-h-0 w-full flex-col gap-3 px-page-x py-page-y">
      <TimeCalendarToolbar calendar={calendar} locale={currentLocale} />
      <TimeCalendarBody calendar={calendar} locale={currentLocale} />
    </div>
  );
});
