/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { createContext, useContext, useMemo } from "react";
import { format, getDay, parse, startOfWeek } from "date-fns";
import { cs, de, enUS, es, fr, id, it, ja, ko, pl, ptBR, ro, ru, sk, tr, uk, vi, zhCN, zhTW } from "date-fns/locale";
import { Calendar, dateFnsLocalizer, Views } from "react-big-calendar";
import type { DateLocalizer, Formats } from "react-big-calendar";
import dragAndDropAddon from "react-big-calendar/lib/addons/dragAndDrop";
// eslint-disable-next-line import/no-unassigned-import
import "react-big-calendar/lib/css/react-big-calendar.css";
// eslint-disable-next-line import/no-unassigned-import
import "react-big-calendar/lib/addons/dragAndDrop/styles.css";
// eslint-disable-next-line import/no-unassigned-import
import "@/styles/time-calendar.css";
import type { TTimeCalendarLog, TTimeCalendarScheduleDay } from "@/services/time-calendar.service";
import {
  dayCapacitySeconds,
  formatDuration,
  isClockLog,
  loggedSecondsOnDay,
  isWorkSlot,
  localDateKey,
  logTitle,
  parseHHMM,
  placedInstant,
  snapDurationSeconds,
  snapStart,
  wallTimeAsLocalDate,
} from "./time";

const DATE_LOCALES: Record<string, typeof enUS> = {
  en: enUS,
  "en-US": enUS,
  ru,
  cs,
  de,
  es,
  fr,
  id,
  it,
  ja,
  ko,
  pl,
  pt: ptBR,
  "pt-BR": ptBR,
  ro,
  sk,
  tr,
  "tr-TR": tr,
  ua: uk,
  uk,
  vi,
  "vi-VN": vi,
  "zh-CN": zhCN,
  "zh-TW": zhTW,
};

const localizer = dateFnsLocalizer({
  format,
  parse,
  startOfWeek: (date: Date) => startOfWeek(date, { weekStartsOn: 1 }),
  getDay,
  locales: DATE_LOCALES,
});

function formatClock(gridLocalizer: DateLocalizer | undefined, date: Date, culture?: string) {
  return gridLocalizer ? gridLocalizer.format(date, "HH:mm", culture) : "";
}

const formats: Formats = {
  timeGutterFormat: (date, culture, gridLocalizer) => formatClock(gridLocalizer, date, culture),
  dayFormat: (date, culture, gridLocalizer) => (gridLocalizer ? gridLocalizer.format(date, "dd EEE", culture) : ""),
  selectRangeFormat: (range, culture, gridLocalizer) =>
    `${formatClock(gridLocalizer, range.start, culture)}–${formatClock(gridLocalizer, range.end, culture)}`,
  eventTimeRangeFormat: (range, culture, gridLocalizer) =>
    `${formatClock(gridLocalizer, range.start, culture)}–${formatClock(gridLocalizer, range.end, culture)}`,
};

function calendarCulture(locale: string): string {
  if (DATE_LOCALES[locale]) return locale;
  const base = locale.split("-")[0] ?? "";
  return DATE_LOCALES[base] ? base : "en";
}

export type TCalendarEvent = {
  id: string;
  title: string;
  start: Date;
  end: Date;
  allDay: boolean;
  resource: TTimeCalendarLog;
};

// The addon is CommonJS. Vite's default import is sometimes `{ default: fn }`.
function resolveDragAndDrop(mod: unknown): typeof dragAndDropAddon {
  let current = mod;
  while (current && typeof current !== "function" && typeof current === "object" && "default" in current) {
    current = (current as { default: unknown }).default;
  }
  return current as typeof dragAndDropAddon;
}

const DnDCalendar = resolveDragAndDrop(dragAndDropAddon)<TCalendarEvent>(Calendar);

type DayTotals = {
  logs: TTimeCalendarLog[];
  now: Date;
  timeZone: string;
  scheduleByDate: Record<string, TTimeCalendarScheduleDay>;
  workingHoursEnabled: boolean;
};

const DayTotalsContext = createContext<DayTotals>({
  logs: [],
  now: new Date(0),
  timeZone: "UTC",
  scheduleByDate: {},
  workingHoursEnabled: false,
});

function DateCellWrapper({ value, children }: { value: Date; children?: JSX.Element }) {
  const totals = useContext(DayTotalsContext);
  const logged = loggedSecondsOnDay(totals.logs, value, totals.timeZone, totals.now);
  const capacity = dayCapacitySeconds(totals.scheduleByDate[localDateKey(value)], totals.workingHoursEnabled);
  const label = capacity == null ? formatDuration(logged) : `${formatDuration(logged)} / ${formatDuration(capacity)}`;
  return (
    <div className="time-allday-slot">
      {children}
      <span className="time-day-hours">{label}</span>
    </div>
  );
}

const calendarComponents = {
  dateCellWrapper: DateCellWrapper,
};

type Props = {
  logs: TTimeCalendarLog[];
  weekStart: Date;
  timeZone: string;
  now: Date;
  schedule: TTimeCalendarScheduleDay[];
  workingHoursEnabled: boolean;
  locale: string;
  onCreateRange: (date: string, durationSeconds: number, startedAt: string) => void;
  onMoveDuration: (log: TTimeCalendarLog, date: string, startedAt: string) => void;
  onResizeDuration: (log: TTimeCalendarLog, date: string, durationSeconds: number, startedAt: string) => void;
  onSelectLog: (log: TTimeCalendarLog) => void;
};

const toDate = (value: Date | string) => (value instanceof Date ? value : new Date(value));

export function TimeWeekGrid(props: Props) {
  const {
    logs,
    weekStart,
    timeZone,
    now,
    schedule,
    workingHoursEnabled,
    locale,
    onCreateRange,
    onMoveDuration,
    onResizeDuration,
    onSelectLog,
  } = props;

  const scheduleByDate = useMemo(() => {
    const map: Record<string, TTimeCalendarScheduleDay> = {};
    for (const day of schedule) map[day.date] = day;
    return map;
  }, [schedule]);

  const events = useMemo<TCalendarEvent[]>(
    () =>
      logs.map((log) => {
        const title = logTitle(log);
        const start = wallTimeAsLocalDate(log.started_at, timeZone);
        const end = log.stopped_at ? wallTimeAsLocalDate(log.stopped_at, timeZone) : now;
        return {
          id: log.id,
          title: isClockLog(log) ? title : `${title} · ${formatDuration(log.duration_seconds)}`,
          start,
          end: end.getTime() <= start.getTime() ? new Date(start.getTime() + 60_000) : end,
          allDay: false,
          resource: log,
        };
      }),
    [logs, now, timeZone]
  );

  const dayTotals = useMemo(
    () => ({ logs, now, timeZone, scheduleByDate, workingHoursEnabled }),
    [logs, now, scheduleByDate, timeZone, workingHoursEnabled]
  );

  const scrollToTime = useMemo(() => {
    const first = schedule.find((day) => day.working && day.start);
    const minutes = parseHHMM(first?.start ?? "09:00") ?? 9 * 60;
    return new Date(1970, 0, 1, Math.floor(minutes / 60), minutes % 60);
  }, [schedule]);

  return (
    <DayTotalsContext.Provider value={dayTotals}>
      <div className="time-calendar h-full min-h-0">
        <DnDCalendar
          localizer={localizer}
          culture={calendarCulture(locale)}
          formats={formats}
          components={calendarComponents}
          events={events}
          date={weekStart}
          view={Views.WEEK}
          views={[Views.WEEK]}
          onNavigate={() => undefined}
          onView={() => undefined}
          toolbar={false}
          selectable
          step={15}
          timeslots={1}
          showMultiDayTimes
          scrollToTime={scrollToTime}
          getNow={() => now}
          draggableAccessor={(event) => !!event.resource.stopped_at && event.resource.can_manage}
          resizableAccessor={(event) => !!event.resource.stopped_at && event.resource.can_manage}
          onSelectEvent={(event) => onSelectLog(event.resource)}
          onEventDrop={({ event, start }) => {
            const log = event.resource;
            if (!log.stopped_at || !log.can_manage) return;
            const slotStart = snapStart(toDate(start));
            if (slotStart.getTime() === snapStart(event.start).getTime()) return;
            onMoveDuration(log, localDateKey(slotStart), placedInstant(slotStart, timeZone));
          }}
          onEventResize={({ event, start, end }) => {
            const log = event.resource;
            if (!log.stopped_at || !log.can_manage) return;
            const slotStart = snapStart(toDate(start));
            const durationSeconds = snapDurationSeconds(slotStart, toDate(end));
            const sameStart = slotStart.getTime() === snapStart(event.start).getTime();
            if (sameStart && durationSeconds === log.duration_seconds) return;
            onResizeDuration(log, localDateKey(slotStart), durationSeconds, placedInstant(slotStart, timeZone));
          }}
          onSelectSlot={({ start, end, slots, action }) => {
            const slotStart = snapStart(toDate(start));
            const slotEnd = toDate(end);
            const span = Math.max(0, slotEnd.getTime() - slotStart.getTime());
            const singleClick = action === "click" || (span >= 24 * 60 * 60 * 1000 && (slots?.length ?? 1) <= 1);
            const durationSeconds = singleClick ? 3600 : snapDurationSeconds(slotStart, slotEnd);
            onCreateRange(localDateKey(slotStart), durationSeconds, placedInstant(slotStart, timeZone));
          }}
          dayPropGetter={(date) => {
            if (!workingHoursEnabled) return {};
            const day = scheduleByDate[localDateKey(date)];
            return day && !day.working ? { className: "time-day-off" } : {};
          }}
          slotPropGetter={(date) => ({
            className: isWorkSlot(date, scheduleByDate, workingHoursEnabled) ? "time-slot-work" : "time-slot-off",
          })}
          eventPropGetter={(event) => ({
            className: isClockLog(event.resource) ? "time-event-clock" : "time-event-duration",
          })}
        />
      </div>
    </DayTotalsContext.Provider>
  );
}
