/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TTimeCalendarLog, TTimeCalendarScheduleDay } from "@/services/time-calendar.service";

const SNAP_SECONDS = 15 * 60;

export function wallTimeAsLocalDate(isoUtc: string, timeZone: string): Date {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone,
    hourCycle: "h23",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).formatToParts(new Date(isoUtc));
  const pick = (type: Intl.DateTimeFormatPartTypes) => Number(parts.find((part) => part.type === type)?.value ?? "0");
  const hour = pick("hour") === 24 ? 0 : pick("hour");
  return new Date(pick("year"), pick("month") - 1, pick("day"), hour, pick("minute"), pick("second"));
}

/** `datetime-local` value for an instant, in the display timezone. */
export function toDateTimeLocalValue(isoUtc: string, timeZone: string): string {
  const wall = wallTimeAsLocalDate(isoUtc, timeZone);
  const month = String(wall.getMonth() + 1).padStart(2, "0");
  const day = String(wall.getDate()).padStart(2, "0");
  const hours = String(wall.getHours()).padStart(2, "0");
  const minutes = String(wall.getMinutes()).padStart(2, "0");
  return `${wall.getFullYear()}-${month}-${day}T${hours}:${minutes}`;
}

export function localDateKey(date: Date): string {
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

export function parseDateKey(key: string): Date {
  const [year, month, day] = key.split("-").map(Number);
  return new Date(year, (month ?? 1) - 1, day ?? 1);
}

export function startOfWeekMonday(date: Date): Date {
  const start = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const weekday = start.getDay();
  const delta = weekday === 0 ? -6 : 1 - weekday;
  start.setDate(start.getDate() + delta);
  return start;
}

export function addDays(date: Date, days: number): Date {
  const next = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  next.setDate(next.getDate() + days);
  return next;
}

export function snapDurationSeconds(start: Date, end: Date): number {
  const raw = Math.max(0, Math.round((end.getTime() - start.getTime()) / 1000));
  const snapped = Math.round(raw / SNAP_SECONDS) * SNAP_SECONDS;
  return Math.max(60, snapped);
}

/** Align a dragged start to the 15-minute grid. */
export function snapStart(date: Date): Date {
  const snapped = new Date(date);
  snapped.setSeconds(0, 0);
  const minutes = snapped.getMinutes();
  const remainder = minutes % 15;
  const delta = remainder < 8 ? -remainder : 15 - remainder;
  snapped.setMinutes(minutes + delta);
  return snapped;
}

/**
 * A date-only log is stored at midnight UTC on its date. Anything else is a clock
 * time the user placed on the grid.
 */
export function hasPlacedStart(log: { date: string; started_at: string }): boolean {
  const started = new Date(log.started_at);
  if (Number.isNaN(started.getTime())) return false;
  const midnight =
    started.getUTCHours() === 0 &&
    started.getUTCMinutes() === 0 &&
    started.getUTCSeconds() === 0 &&
    started.getUTCMilliseconds() === 0;
  return !(midnight && log.started_at.slice(0, 10) === log.date);
}

/**
 * UTC instant for a wall-clock `YYYY-MM-DDTHH:mm` in `timeZone`.
 * The grid stores that wall clock on a Date, so `Date#toISOString` would treat it as the browser zone.
 */
export function zonedDateTimeToIso(value: string, timeZone: string): string | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/.exec(value);
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const hour = Number(match[4]);
  const minute = Number(match[5]);
  const desiredUtc = Date.UTC(year, month - 1, day, hour, minute);
  let instant = desiredUtc;
  for (let pass = 0; pass < 2; pass += 1) {
    const wall = wallTimeAsLocalDate(new Date(instant).toISOString(), timeZone);
    const wallAsUtc = Date.UTC(wall.getFullYear(), wall.getMonth(), wall.getDate(), wall.getHours(), wall.getMinutes());
    instant += desiredUtc - wallAsUtc;
  }
  const corrected = new Date(instant);
  return Number.isNaN(corrected.getTime()) ? null : corrected.toISOString();
}

/** ISO instant for a grid drop, snapped to the 15-minute grid in the workspace zone. */
export function placedInstant(start: Date, timeZone: string): string {
  const snapped = snapStart(start);
  const month = String(snapped.getMonth() + 1).padStart(2, "0");
  const day = String(snapped.getDate()).padStart(2, "0");
  const hours = String(snapped.getHours()).padStart(2, "0");
  const minutes = String(snapped.getMinutes()).padStart(2, "0");
  const wall = `${snapped.getFullYear()}-${month}-${day}T${hours}:${minutes}`;
  return zonedDateTimeToIso(wall, timeZone) ?? snapped.toISOString();
}

export function formatDuration(seconds: number): string {
  const safe = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(safe / 3600);
  const minutes = Math.floor((safe % 3600) / 60);
  if (hours > 0 && minutes > 0) return `${hours}h ${minutes}m`;
  if (hours > 0) return `${hours}h`;
  return `${minutes}m`;
}

export function formatWeekRange(start: Date, end: Date, locale = "en"): string {
  const sameMonth = start.getMonth() === end.getMonth() && start.getFullYear() === end.getFullYear();
  const startLabel = start.toLocaleDateString(locale, { month: "short", day: "numeric" });
  const endLabel = end.toLocaleDateString(locale, {
    month: sameMonth ? undefined : "short",
    day: "numeric",
  });
  return `${startLabel} – ${endLabel}`;
}

/** A running timer, or a log the timer already closed. */
export function isClockLog(log: Pick<TTimeCalendarLog, "stopped_at" | "stop_reason">): boolean {
  if (!log.stopped_at) return true;
  return log.stop_reason === "state_change" || log.stop_reason === "working_hours";
}

export function logTitle(log: TTimeCalendarLog): string {
  return `${log.issue.project_identifier}-${log.issue.sequence_id} ${log.issue.name}`;
}

export function parseHHMM(value: string | null): number | null {
  if (!value) return null;
  const [hours, minutes] = value.split(":");
  const hour = Number(hours);
  const minute = Number(minutes);
  if (Number.isNaN(hour) || Number.isNaN(minute)) return null;
  return hour * 60 + minute;
}

const DEFAULT_WORK_START = 9 * 60;
const DEFAULT_WORK_END = 18 * 60;
const DINNER_BREAK_START = 13 * 60;
const DINNER_BREAK_END = 14 * 60;

/** Localized zone name plus offset, for example "Moscow Standard Time (GMT+3)". */
export function timezoneLabel(timeZone: string, locale: string): string {
  let name = timeZone;
  try {
    name =
      new Intl.DateTimeFormat(locale, { timeZone, timeZoneName: "longGeneric" })
        .formatToParts(new Date())
        .find((part) => part.type === "timeZoneName")?.value ?? timeZone;
  } catch {
    name = timeZone;
  }
  let offset = "";
  try {
    offset =
      new Intl.DateTimeFormat(locale, { timeZone, timeZoneName: "shortOffset" })
        .formatToParts(new Date())
        .find((part) => part.type === "timeZoneName")?.value ?? "";
  } catch {
    offset = "";
  }
  return offset ? `${name} (${offset})` : name;
}

/** 09:00–18:00 on weekdays, with 13:00–14:00 left unmarked as the dinner break. Uses the saved schedule when it is enabled. */
export function isWorkSlot(
  date: Date,
  scheduleByDate: Record<string, TTimeCalendarScheduleDay>,
  enabled: boolean
): boolean {
  const minutes = date.getHours() * 60 + date.getMinutes();
  if (minutes >= DINNER_BREAK_START && minutes < DINNER_BREAK_END) return false;
  if (enabled) return !isOffHours(date, scheduleByDate, true);
  const weekday = date.getDay();
  if (weekday === 0 || weekday === 6) return false;
  return minutes >= DEFAULT_WORK_START && minutes < DEFAULT_WORK_END;
}

export function isOffHours(
  date: Date,
  scheduleByDate: Record<string, TTimeCalendarScheduleDay>,
  enabled: boolean
): boolean {
  if (!enabled) return false;
  const day = scheduleByDate[localDateKey(date)];
  if (!day?.working) return true;
  const start = parseHHMM(day.start);
  const end = parseHHMM(day.end);
  if (start == null || end == null) return true;
  const minutes = date.getHours() * 60 + date.getMinutes();
  return minutes < start || minutes >= end;
}

/** Seconds in a working window, with the 13:00–14:00 lunch break removed where it overlaps. */
function scheduledSeconds(start: number, end: number): number {
  const lunchStart = Math.max(start, DINNER_BREAK_START);
  const lunchEnd = Math.min(end, DINNER_BREAK_END);
  const lunch = lunchEnd > lunchStart ? lunchEnd - lunchStart : 0;
  return (end - start - lunch) * 60;
}

export function capacitySeconds(schedule: TTimeCalendarScheduleDay[], enabled: boolean): number {
  if (!enabled) return 0;
  return schedule.reduce((total, day) => {
    if (!day.working) return total;
    const start = parseHHMM(day.start);
    const end = parseHHMM(day.end);
    if (start == null || end == null || end <= start) return total;
    return total + scheduledSeconds(start, end);
  }, 0);
}

/** Working seconds for one schedule day. `null` when the workspace schedule is off. */
export function dayCapacitySeconds(day: TTimeCalendarScheduleDay | undefined, enabled: boolean): number | null {
  if (!enabled) return null;
  if (!day?.working) return 0;
  const start = parseHHMM(day.start);
  const end = parseHHMM(day.end);
  if (start == null || end == null || end <= start) return 0;
  return scheduledSeconds(start, end);
}

export function loggedSecondsOnDay(logs: TTimeCalendarLog[], day: Date, timeZone: string, now: Date): number {
  const key = localDateKey(day);
  const dayStart = new Date(day.getFullYear(), day.getMonth(), day.getDate());
  const dayEnd = addDays(dayStart, 1);
  return logs.reduce((total, log) => {
    if (!log.stopped_at) {
      const start = wallTimeAsLocalDate(log.started_at, timeZone);
      const from = Math.max(start.getTime(), dayStart.getTime());
      const to = Math.min(now.getTime(), dayEnd.getTime());
      return total + Math.max(0, Math.floor((to - from) / 1000));
    }
    return log.date === key ? total + log.duration_seconds : total;
  }, 0);
}

export function loggedSeconds(logs: TTimeCalendarLog[], weekStart: Date, timeZone: string, now: Date): number {
  const weekStartKey = localDateKey(weekStart);
  const weekEnd = addDays(weekStart, 7);
  const weekEndKey = localDateKey(addDays(weekStart, 6));
  return logs.reduce((total, log) => {
    if (!log.stopped_at) {
      const start = wallTimeAsLocalDate(log.started_at, timeZone);
      const from = Math.max(start.getTime(), weekStart.getTime());
      const to = Math.min(now.getTime(), weekEnd.getTime());
      return total + Math.max(0, Math.floor((to - from) / 1000));
    }
    if (log.date >= weekStartKey && log.date <= weekEndKey) return total + log.duration_seconds;
    return total;
  }, 0);
}
