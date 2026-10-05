import * as React from "react";

import { debounce } from "lodash";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCalendarCheck } from "@fortawesome/free-solid-svg-icons";
import { startOfDay, format, closestTo, isSameDay, parseISO } from "date-fns";
import type { SortOption } from "../EventsExplorer";
import { getEventGroupKey } from "../utils";

type EventTimelineProps = {
  events: Array<ExplorerEventItem>;
  order: SortOption;
  eventCardGridRef?: React.RefObject<HTMLDivElement>;
  onDraggingChange?: (isDragging: boolean) => void;
};

interface MappedMark {
  percent: number;
  shiftedPercent: number;
  label: React.ReactNode;
  groupKey?: string;
}

interface TimelineMark {
  percent: number;
  label: React.ReactNode;
  groupKey?: string;
}

const HORIZONTAL_DATE_MARK_WIDTH_PX = 25;
const HORIZONTAL_BREAKPOINT_PX = 992; // equivalent to the Bootstrap "lg" breakpoint
const COMPACT_HORIZONTAL_RATIO = 0.45;
const LANDSCAPE_HORIZONTAL_RATIO = 1.4;

type TimelineOrientation = "horizontal" | "vertical";

function getHorizontalDateMarkCapacity() {
  if (typeof window === "undefined") return 1;
  return Math.max(
    1,
    Math.floor(window.innerWidth / HORIZONTAL_DATE_MARK_WIDTH_PX)
  );
}

function getTimelineOrientation(): TimelineOrientation {
  if (typeof window === "undefined") return "vertical";
  const { innerWidth, innerHeight } = window;
  const viewportRatio = innerWidth / innerHeight;
  return (innerWidth < HORIZONTAL_BREAKPOINT_PX &&
    viewportRatio > COMPACT_HORIZONTAL_RATIO) ||
    viewportRatio > LANDSCAPE_HORIZONTAL_RATIO
    ? "horizontal"
    : "vertical";
}

function isMonthNameDateMark(mark: TimelineMark) {
  return typeof mark.label === "string" && mark.label.includes(" ");
}

function calculateMapping(marks: TimelineMark[], minGap: number) {
  const marksByPercent = new Map<number, TimelineMark>();
  marks
    .slice()
    .sort((a, b) => a.percent - b.percent)
    .forEach((mark) => marksByPercent.set(mark.percent, mark));

  const sortedMarks = Array.from(marksByPercent.values()).sort(
    (a, b) => a.percent - b.percent
  );

  if (sortedMarks.length === 0) return [];

  // Ensure 0 and 100 are in the mapping for better interpolation
  if (sortedMarks[0].percent !== 0)
    sortedMarks.unshift({ percent: 0, label: null });
  if (sortedMarks[sortedMarks.length - 1].percent !== 100)
    sortedMarks.push({ percent: 100, label: null });

  let lastShiftedPercent = -minGap;
  const mappedMarks: MappedMark[] = [];

  sortedMarks.forEach((mark) => {
    const { percent } = mark;
    const shiftedPercent = Math.max(percent, lastShiftedPercent + minGap);
    mappedMarks.push({
      percent,
      shiftedPercent,
      label: mark.label,
      groupKey: mark.groupKey,
    });
    lastShiftedPercent = shiftedPercent;
  });

  const maxShifted = mappedMarks[mappedMarks.length - 1].shiftedPercent;
  if (maxShifted > 100) {
    const scale = 100 / maxShifted;
    mappedMarks.forEach((m) => {
      /* eslint-disable no-param-reassign */
      m.shiftedPercent *= scale;
      // Ensure we don't accidentally shift things before 0
      m.shiftedPercent = Math.max(0, m.shiftedPercent);
      /* eslint-enable no-param-reassign */
    });
  }

  return mappedMarks;
}

function mapLinearToVisual(linearPercent: number, mapping: MappedMark[]) {
  if (mapping.length < 2) return linearPercent;
  const first = mapping[0];
  const last = mapping[mapping.length - 1];

  if (linearPercent <= first.percent) return first.shiftedPercent;
  if (linearPercent >= last.percent) return last.shiftedPercent;

  let i = 0;
  while (i < mapping.length - 1 && mapping[i + 1].percent < linearPercent) {
    i += 1;
  }

  const m1 = mapping[i];
  const m2 = mapping[i + 1];
  const t = (linearPercent - m1.percent) / (m2.percent - m1.percent || 1);
  return m1.shiftedPercent + t * (m2.shiftedPercent - m1.shiftedPercent);
}

function unmapVisualToLinear(visualPercent: number, mapping: MappedMark[]) {
  if (mapping.length < 2) return visualPercent;
  const first = mapping[0];
  const last = mapping[mapping.length - 1];

  if (visualPercent <= first.shiftedPercent) return first.percent;
  if (visualPercent >= last.shiftedPercent) return last.percent;

  let i = 0;
  while (
    i < mapping.length - 1 &&
    mapping[i + 1].shiftedPercent < visualPercent
  ) {
    i += 1;
  }

  const m1 = mapping[i];
  const m2 = mapping[i + 1];
  const t =
    (visualPercent - m1.shiftedPercent) /
    (m2.shiftedPercent - m1.shiftedPercent || 1);
  return m1.percent + t * (m2.percent - m1.percent);
}

// the events arrive sorted in the chosen direction, so each group's mark goes where its first event is
function createMarks(events: Array<ExplorerEventItem>, order: SortOption) {
  const marks: Array<TimelineMark> = [];
  let lastGroupKey: string | undefined;
  let lastMonth = "";

  events.forEach((event, index) => {
    const groupKey = getEventGroupKey(order, event);
    if (groupKey === lastGroupKey || !groupKey) {
      return;
    }
    lastGroupKey = groupKey;
    let label = groupKey;
    if (order === "date" && groupKey.length > 4) {
      const parsedDate = parseISO(groupKey);
      const month = format(parsedDate, "MMM").toUpperCase();
      label = groupKey.length === 7 ? month : format(parsedDate, "d");
      if (groupKey.length !== 7 && month !== lastMonth) {
        label = `${label} ${month}`;
      }
      lastMonth = month;
    } else if (order === "listen_count" || order === "user_listen_count") {
      label = groupKey.replace(" listens", "");
    } else if (groupKey === "Unknown artist") {
      label = "?";
    }
    marks.push({ percent: (100 * index) / events.length, label, groupKey });
  });

  if (order === "date") {
    const today = startOfDay(new Date());
    const dateMarks = marks.filter((mark) => mark.groupKey!.length === 10);
    const closestDate = closestTo(
      today,
      dateMarks.map((mark) => parseISO(mark.groupKey!))
    );
    if (closestDate) {
      const closestMark = dateMarks.find((mark) =>
        isSameDay(parseISO(mark.groupKey!), closestDate)
      )!;
      let todayLabel = "Today";
      if (!isSameDay(closestDate, today)) {
        todayLabel = closestDate > today ? "Next" : "Recent";
      }
      marks.push({
        percent: closestMark.percent,
        label: (
          <span className="mark-label-today">
            <FontAwesomeIcon icon={faCalendarCheck} className="calendar-icon" />
            {todayLabel}
          </span>
        ),
        groupKey: closestMark.groupKey,
      });
    }
  }

  return marks;
}

function filterHorizontalDateMarks(
  marks: TimelineMark[],
  isHorizontal: boolean,
  order: SortOption,
  maxVisibleDateMarks: number
) {
  if (
    !isHorizontal ||
    order !== "date" ||
    marks.length <= maxVisibleDateMarks
  ) {
    return marks;
  }

  const dateMarks = marks.filter((mark) => !React.isValidElement(mark.label));
  const visibleDateGroupKeys = new Set<string | undefined>();
  const step = Math.ceil(dateMarks.length / maxVisibleDateMarks);

  dateMarks.forEach((mark, index) => {
    if (
      index === 0 ||
      index === dateMarks.length - 1 ||
      index % step === 0 ||
      isMonthNameDateMark(mark)
    ) {
      visibleDateGroupKeys.add(mark.groupKey);
    }
  });

  return marks.filter(
    (mark) =>
      React.isValidElement(mark.label) ||
      visibleDateGroupKeys.has(mark.groupKey)
  );
}

/** Returns the page-level Y position; use non-sticky elements as scroll targets. */
function getAbsoluteTop(el: HTMLElement): number {
  return el.getBoundingClientRect().top + window.scrollY;
}

export default function EventTimeline(props: EventTimelineProps) {
  const { events, order, onDraggingChange, eventCardGridRef } = props;

  const [thumbSize, setThumbSize] = React.useState<number>(30);
  const [currentValue, setCurrentValue] = React.useState<number>(0);
  const [mappedMarks, setMappedMarks] = React.useState<MappedMark[]>([]);
  const [isDragging, setIsDragging] = React.useState(false);
  const [
    horizontalDateMarkCapacity,
    setHorizontalDateMarkCapacity,
  ] = React.useState(getHorizontalDateMarkCapacity);
  const [orientation, setOrientation] = React.useState<TimelineOrientation>(
    getTimelineOrientation
  );
  const trackRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (onDraggingChange) {
      onDraggingChange(isDragging);
    }
  }, [isDragging, onDraggingChange]);

  const isHorizontal = orientation === "horizontal";

  const minGap = isHorizontal ? 2.5 : 1.5;

  const allMarks = React.useMemo(
    () => createMarks(events, order).sort((a, b) => a.percent - b.percent),
    [events, order]
  );

  React.useEffect(() => {
    const visibleMarks = filterHorizontalDateMarks(
      allMarks,
      isHorizontal,
      order,
      horizontalDateMarkCapacity
    );
    setMappedMarks(calculateMapping(visibleMarks, minGap));
  }, [allMarks, order, isHorizontal, horizontalDateMarkCapacity, minGap]);

  React.useEffect(() => {
    const updateTimelineLayout = () => {
      const nextOrientation = getTimelineOrientation();
      setOrientation(nextOrientation);
      const nextIsHorizontal = nextOrientation === "horizontal";
      if (nextIsHorizontal) {
        setHorizontalDateMarkCapacity(getHorizontalDateMarkCapacity());
      }

      const container =
        eventCardGridRef?.current ||
        document.getElementById("events-explorer-grids");
      if (!container || !trackRef.current) return;
      const trackLength = nextIsHorizontal
        ? trackRef.current.offsetWidth
        : trackRef.current.offsetHeight;
      const containerTop = getAbsoluteTop(container);
      const pageMaxScroll = Math.max(
        1,
        document.documentElement.scrollHeight - window.innerHeight
      );
      const containerMaxScroll = Math.max(1, pageMaxScroll - containerTop);
      const ratio = Math.min(window.innerHeight / containerMaxScroll, 0.05);
      const size = Math.max(20, ratio * trackLength);
      setThumbSize(size);
    };
    const debouncedUpdateTimelineLayout = debounce(updateTimelineLayout, 100);

    updateTimelineLayout();
    window.addEventListener("resize", debouncedUpdateTimelineLayout);
    return () => {
      debouncedUpdateTimelineLayout.cancel();
      window.removeEventListener("resize", debouncedUpdateTimelineLayout);
    };
  }, [events, eventCardGridRef]);

  React.useEffect(() => {
    if (isDragging) {
      document.body.classList.add("is-events-timeline-dragging");
    } else {
      document.body.classList.remove("is-events-timeline-dragging");
    }
    return () => document.body.classList.remove("is-events-timeline-dragging");
  }, [isDragging]);

  const scrollToPosition = React.useCallback(
    (percent: number, behavior: ScrollBehavior = "smooth") => {
      const element =
        eventCardGridRef?.current ||
        document.getElementById("events-explorer-grids");
      if (!element) return;
      const containerTop = getAbsoluteTop(element);
      const pageMaxScroll = Math.max(
        1,
        document.documentElement.scrollHeight - window.innerHeight
      );
      // The scrollable distance from when the container enters the viewport
      // to the absolute page bottom. Using this as the denominator ensures
      // the thumb reaches 100% exactly at the page bottom on any page size.
      const containerMaxScroll = Math.max(1, pageMaxScroll - containerTop);
      window.scrollTo({
        top: containerTop + (percent / 100) * containerMaxScroll,
        behavior,
      });
    },
    [eventCardGridRef]
  );

  const scrollToGroup = React.useCallback(
    (groupKey: string, behavior: ScrollBehavior = "smooth") => {
      const container =
        eventCardGridRef?.current ||
        document.getElementById("events-explorer-grids");
      if (!container) return false;

      const groupAnchor = Array.from(
        container.querySelectorAll<HTMLElement>(
          ".events-explorer-grid-anchor[data-group-key]"
        )
      ).find((anchor) => anchor.dataset.groupKey === groupKey);

      if (!groupAnchor) return false;

      window.scrollTo({
        top: getAbsoluteTop(groupAnchor),
        behavior,
      });
      return true;
    },
    [eventCardGridRef]
  );

  const activateMark = React.useCallback(
    (mark: MappedMark, behavior: ScrollBehavior = "smooth") => {
      setCurrentValue(mark.percent);
      if (
        mark.groupKey !== undefined &&
        scrollToGroup(mark.groupKey, behavior)
      ) {
        return;
      }
      scrollToPosition(mark.percent, behavior);
    },
    [scrollToGroup, scrollToPosition]
  );

  const handleMove = React.useCallback(
    (e: MouseEvent | TouchEvent) => {
      if (!trackRef.current || !mappedMarks.length) return;
      const rect = trackRef.current.getBoundingClientRect();
      const touchOrMouseEvent =
        "touches" in e ? (e as TouchEvent).touches[0] : (e as MouseEvent);
      const cursorPosition = isHorizontal
        ? touchOrMouseEvent.clientX - rect.left
        : touchOrMouseEvent.clientY - rect.top;
      const trackSize = isHorizontal ? rect.width : rect.height;
      let visualPercent = (cursorPosition / trackSize) * 100;
      visualPercent = Math.max(0, Math.min(100, visualPercent));

      const linearPercent = unmapVisualToLinear(visualPercent, mappedMarks);
      setCurrentValue(linearPercent);
      scrollToPosition(linearPercent, isDragging ? "auto" : "smooth");
    },
    [isHorizontal, scrollToPosition, isDragging, mappedMarks]
  );

  const onStart = (e: React.MouseEvent | React.TouchEvent) => {
    setIsDragging(true);
    handleMove(e.nativeEvent as any);
  };

  const onMarkStart = (
    e: React.MouseEvent | React.TouchEvent,
    mark: MappedMark
  ) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    activateMark(mark);
  };

  React.useEffect(() => {
    const onMove = (e: MouseEvent | TouchEvent) => {
      if (isDragging) handleMove(e as any);
    };
    const onEnd = () => setIsDragging(false);

    if (isDragging) {
      window.addEventListener("mousemove", onMove as any);
      window.addEventListener("mouseup", onEnd);
      window.addEventListener("touchmove", onMove as any, { passive: false });
      window.addEventListener("touchend", onEnd);
    }
    return () => {
      window.removeEventListener("mousemove", onMove as any);
      window.removeEventListener("mouseup", onEnd);
      window.removeEventListener("touchmove", onMove as any);
      window.removeEventListener("touchend", onEnd);
    };
  }, [isDragging, handleMove]);

  React.useEffect(() => {
    const handleScroll = debounce(() => {
      const container =
        eventCardGridRef?.current ||
        document.getElementById("events-explorer-grids");
      if (!container || isDragging) return;
      const containerTop = getAbsoluteTop(container);
      const pageMaxScroll = Math.max(
        1,
        document.documentElement.scrollHeight - window.innerHeight
      );
      const containerMaxScroll = Math.max(1, pageMaxScroll - containerTop);
      const scrollPos =
        ((window.scrollY - containerTop) / containerMaxScroll) * 100;
      setCurrentValue(Math.max(0, Math.min(100, scrollPos)));
    }, 50);

    window.addEventListener("scroll", handleScroll);
    return () => {
      handleScroll.cancel();
      window.removeEventListener("scroll", handleScroll);
    };
  }, [isDragging, eventCardGridRef]);

  const visualPercent = mapLinearToVisual(currentValue, mappedMarks);

  const getTooltipData = () => {
    if (!events.length) return null;

    const activeMark = allMarks.reduce<TimelineMark | undefined>(
      (active, mark) => {
        if (!mark.label || mark.groupKey === undefined) return active;
        if (!active || mark.percent <= currentValue) return mark;
        return active;
      },
      undefined
    );

    if (!activeMark || activeMark.groupKey === undefined) return null;

    if (order === "date" && activeMark.groupKey.length > 4) {
      const date = parseISO(activeMark.groupKey);
      return activeMark.groupKey.length === 7
        ? { main: format(date, "MMM"), sub: format(date, "yyyy") }
        : { main: format(date, "d"), sub: format(date, "MMMM") };
    }
    return {
      main: activeMark.label,
      sub: "",
    };
  };

  const tooltipData = getTooltipData();
  const isProminentHorizontalMark = (mark: MappedMark) =>
    isHorizontal &&
    (React.isValidElement(mark.label) || isMonthNameDateMark(mark));
  const getMarkClassName = (mark: MappedMark) => {
    return `timeline-mark ${orientation}${
      isProminentHorizontalMark(mark) ? " full-date" : ""
    }`;
  };

  return (
    <div className={`events-timeline ${orientation}`}>
      <div
        ref={trackRef}
        role="slider"
        tabIndex={0}
        aria-valuenow={Number(visualPercent.toFixed(0)) || 0}
        aria-valuemin={0}
        aria-valuemax={100}
        className={`timeline-track ${orientation}`}
        onMouseDown={onStart}
        onTouchStart={onStart}
      >
        <div className={`timeline-hit-area ${orientation}`} />
        <div
          className={`timeline-thumb ${orientation}`}
          style={{
            [isHorizontal ? "left" : "top"]: `${visualPercent}%`,
            [isHorizontal ? "width" : "height"]: `${thumbSize}px`,
            transition: isDragging ? "none" : "all 0.1s ease-out",
          }}
        />
        {isDragging && tooltipData && (
          <div
            className={`timeline-tooltip ${orientation}`}
            style={{ [isHorizontal ? "left" : "top"]: `${visualPercent}%` }}
          >
            <div className="tooltip-content">
              <div className="tooltip-day">{tooltipData.main}</div>
              <div className="tooltip-month">{tooltipData.sub}</div>
            </div>
          </div>
        )}
        {mappedMarks.map((mark: MappedMark) =>
          mark.label ? (
            <div
              key={`${mark.percent}-${mark.groupKey ?? ""}`}
              className={getMarkClassName(mark)}
              role="presentation"
              data-testid="timeline-mark"
              style={{
                [isHorizontal ? "left" : "top"]: `${mark.shiftedPercent}%`,
              }}
              onMouseDown={(event) => onMarkStart(event, mark)}
              onTouchStart={(event) => onMarkStart(event, mark)}
            >
              <div className="tick-mark" />
              <span
                className={`mark-label${
                  isProminentHorizontalMark(mark) ? " full-date" : ""
                }`}
              >
                {mark.label}
              </span>
            </div>
          ) : null
        )}
      </div>
    </div>
  );
}
