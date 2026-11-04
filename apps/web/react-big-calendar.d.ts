declare module "react-big-calendar" {
  export interface CalendarProps<TEvent extends { start: Date; end: Date }> {
    localizer: object;
    events?: TEvent[];
    date?: Date;
    view?: string;
    views?: string[];
    toolbar?: boolean;
    selectable?: boolean | "ignoreEvents";
    step?: number;
    timeslots?: number;
    showMultiDayTimes?: boolean;
    scrollToTime?: Date;
    getNow?: () => Date;
    onNavigate?: () => void;
    onView?: () => void;
    culture?: string;
    formats?: object;
    draggableAccessor?: (event: TEvent) => boolean;
    resizableAccessor?: (event: TEvent) => boolean;
    onSelectEvent?: (event: TEvent) => void;
    onSelectSlot?: (slot: {
      start: Date | string;
      end: Date | string;
      slots?: Array<Date | string>;
      action?: "select" | "click" | "doubleClick";
    }) => void;
    onEventDrop?: (args: { event: TEvent; start: Date | string; end: Date | string }) => void;
    onEventResize?: (args: { event: TEvent; start: Date | string; end: Date | string }) => void;
    dayPropGetter?: (date: Date) => { className?: string };
    slotPropGetter?: (date: Date) => { className?: string };
    eventPropGetter?: (event: TEvent) => { className?: string };
    components?: {
      dateCellWrapper?: (props: { value: Date; children?: JSX.Element }) => JSX.Element;
    };
  }

  export function Calendar<TEvent extends { start: Date; end: Date }>(props: CalendarProps<TEvent>): JSX.Element;
  export function dateFnsLocalizer(config: object): object;
  export const Views: { WEEK: "week" };
}

declare module "react-big-calendar/lib/addons/dragAndDrop" {
  import type { CalendarProps } from "react-big-calendar";

  function withDragAndDrop<TEvent extends { start: Date; end: Date }>(
    calendar: (props: CalendarProps<TEvent>) => JSX.Element
  ): (props: CalendarProps<TEvent>) => JSX.Element;
  export default withDragAndDrop;
}
