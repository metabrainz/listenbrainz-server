import * as React from "react";

import { countBy, debounce, zipObject } from "lodash";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCalendarCheck } from "@fortawesome/free-solid-svg-icons";
import { startOfDay, format, closestTo, parseISO } from "date-fns";
import { formatReleaseDate, useMediaQuery } from "../utils";
import { SortDirection, SortOption } from "../FreshReleases";
import { COLOR_LB_BLUE } from "../../../utils/constants";

type ReleaseTimelineProps = {
  releases: Array<FreshReleaseItem>;
  order: SortOption;
  direction: SortDirection;
};

interface MappedMark {
  percent: number;
  shiftedPercent: number;
  label: React.ReactNode;
}

function calculateMapping(
  marks: Record<number, React.ReactNode>,
  minGap: number
) {
  const sortedPercents = Object.keys(marks)
    .map(Number)
    .sort((a, b) => a - b);

  if (sortedPercents.length === 0) return [];

  // Ensure 0 and 100 are in the mapping for better interpolation
  if (sortedPercents[0] !== 0) sortedPercents.unshift(0);
  if (sortedPercents[sortedPercents.length - 1] !== 100)
    sortedPercents.push(100);

  const uniquePercents = Array.from(new Set(sortedPercents)).sort(
    (a, b) => a - b
  );

  let lastShiftedPercent = -minGap;
  const mappedMarks: MappedMark[] = [];

  uniquePercents.forEach((percent) => {
    const shiftedPercent = Math.max(percent, lastShiftedPercent + minGap);
    mappedMarks.push({
      percent,
      shiftedPercent,
      label: marks[percent] || null,
    });
    lastShiftedPercent = shiftedPercent;
  });

  const maxShifted = mappedMarks[mappedMarks.length - 1].shiftedPercent;
  if (maxShifted > 100) {
    const scale = 100 / maxShifted;
    mappedMarks.forEach((m) => {
      m.shiftedPercent *= scale;
      // Ensure we don't accidentally shift things before 0
      m.shiftedPercent = Math.max(0, m.shiftedPercent);
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
    i++;
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
    i++;
  }

  const m1 = mapping[i];
  const m2 = mapping[i + 1];
  const t =
    (visualPercent - m1.shiftedPercent) /
    (m2.shiftedPercent - m1.shiftedPercent || 1);
  return m1.percent + t * (m2.percent - m1.percent);
}

function createMarks(
  releases: Array<FreshReleaseItem>,
  sortDirection: SortDirection,
  order: SortOption
) {
  const dataArr: Array<string | JSX.Element | number> = [];
  let percentArr: Array<number> = [];

  if (order === "release_date") {
    let releasesPerDate = countBy(
      releases,
      (item: FreshReleaseItem) => item.release_date
    );

    if (sortDirection === "descend") {
      const reversedReleasesPerDate = Object.keys(releasesPerDate).reverse();
      releasesPerDate = zipObject(
        reversedReleasesPerDate,
        Object.values(releasesPerDate).reverse()
      );
    }

    const totalReleases = Object.values(releasesPerDate).reduce(
      (sum, value) => sum + value,
      0
    );

    const cummulativeMap = new Map();
    let cummulativeSum = 0;

    Object.keys(releasesPerDate).forEach((date) => {
      cummulativeMap.set(date, (100 * cummulativeSum) / totalReleases);
      cummulativeSum += releasesPerDate[date];
    });

    let lastMonth = "";
    Object.keys(releasesPerDate).forEach((date) => {
      const parsedDate = parseISO(date);
      const day = format(parsedDate, "d");
      const month = format(parsedDate, "MMM").toUpperCase();
      let label = day;
      if (month !== lastMonth) {
        label = `${day} ${month}`;
        lastMonth = month;
      }
      dataArr.push(label);
      percentArr.push(cummulativeMap.get(date)!);
    });

    const dates = Object.keys(releasesPerDate).map((date) => parseISO(date));
    const recentDateStr = format(startOfDay(new Date()), "yyyy-MM-dd");
    const closestDateStr = dates.length
      ? format(closestTo(new Date(recentDateStr), dates)!, "yyyy-MM-dd")
      : recentDateStr;

    dataArr.push(recentDateStr === closestDateStr ? "Today" : "Recent");
    percentArr.push(cummulativeMap.get(closestDateStr)!);
  } else if (order === "artist_credit_name" || order === "release_name") {
    const counts = countBy(releases, (item: FreshReleaseItem) =>
      item[order].charAt(0).toUpperCase()
    );
    const initials = Object.keys(counts).sort();
    const totalCount = releases.length;
    let cummulativeSum = 0;

    initials.forEach((initial) => {
      percentArr.push((100 * cummulativeSum) / totalCount);
      dataArr.push(initial);
      cummulativeSum += counts[initial];
    });
  } else if (order === "confidence") {
    const counts = countBy(
      releases,
      (item: FreshReleaseItem) => item?.confidence
    );
    const confidences = Object.keys(counts).sort(
      (a, b) => Number(a) - Number(b)
    );
    const totalCount = releases.length;
    let cummulativeSum = 0;

    confidences.forEach((conf) => {
      percentArr.push((100 * cummulativeSum) / totalCount);
      dataArr.push(`${Math.round(Number(conf) * 100)}%`);
      cummulativeSum += counts[conf];
    });
  }

  if (sortDirection === "descend" && order !== "release_date") {
    dataArr.reverse();
    percentArr = percentArr.reverse().map((v) => (v <= 100 ? 100 - v : 0));
  }
  /*
   * We want the timeline dates or marks to start where the grid starts.
   * So the 0% should always have the first date. Therefore we use unshift(0) here.
   * With the same logic, we don't want the last date to be at 100% because
   * that will mean we're at the bottom of the grid.
   * The last date should start before 100%. That explains the pop().
   * For descending sort, the reverse computation above possibly already ensures that
   * the percentArr starts with 0 and ends with a non-100% value, which is desired.
   * Hence, we add a check to skip the unshift(0) and pop() operations in that case.
   */

  if (percentArr[0] !== 0 && order !== "release_date") {
    percentArr.unshift(0);
    percentArr.pop();
  }

  return zipObject(percentArr, dataArr);
}

/** Returns the element's stable page-level Y position (scroll-invariant). */
function getAbsoluteTop(el: HTMLElement): number {
  return el.getBoundingClientRect().top + window.scrollY;
}

export default function ReleaseTimeline(props: ReleaseTimelineProps) {
  const { releases, order, direction } = props;

  const [thumbSize, setThumbSize] = React.useState<number>(30);
  const [currentValue, setCurrentValue] = React.useState<number>(0);
  const [mappedMarks, setMappedMarks] = React.useState<MappedMark[]>([]);
  const [isDragging, setIsDragging] = React.useState(false);
  const trackRef = React.useRef<HTMLDivElement>(null);

  const screenMd = useMediaQuery("(max-width: 992px)");

  const minGap = screenMd ? 2.5 : 1.5;

  React.useEffect(() => {
    const rawMarks = createMarks(releases, direction, order) as Record<
      number,
      React.ReactNode
    >;
    setMappedMarks(calculateMapping(rawMarks, minGap));
  }, [releases, direction, order, minGap]);

  React.useEffect(() => {
    const updateThumbSize = () => {
      const container = document.getElementById("release-card-grids");
      if (!container || !trackRef.current) return;
      const trackLength = screenMd
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
    updateThumbSize();
    window.addEventListener("resize", updateThumbSize);
    return () => window.removeEventListener("resize", updateThumbSize);
  }, [releases, screenMd]);

  React.useEffect(() => {
    if (isDragging) {
      document.body.classList.add("is-timeline-dragging");
    } else {
      document.body.classList.remove("is-timeline-dragging");
    }
    return () => document.body.classList.remove("is-timeline-dragging");
  }, [isDragging]);

  const scrollToPosition = React.useCallback(
    (percent: number, behavior: ScrollBehavior = "smooth") => {
      const element = document.getElementById("release-card-grids");
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
    []
  );

  const handleMove = React.useCallback(
    (e: MouseEvent | TouchEvent) => {
      if (!trackRef.current || !mappedMarks.length) return;
      const rect = trackRef.current.getBoundingClientRect();
      const y =
        "touches" in e
          ? (e as TouchEvent).touches[0].clientY
          : (e as MouseEvent).clientY;
      let visualPercent = ((y - rect.top) / rect.height) * 100;
      visualPercent = Math.max(0, Math.min(100, visualPercent));

      const linearPercent = unmapVisualToLinear(visualPercent, mappedMarks);
      setCurrentValue(linearPercent);
      scrollToPosition(linearPercent, isDragging ? "auto" : "smooth");
    },
    [scrollToPosition, isDragging, mappedMarks]
  );

  const onStart = (e: React.MouseEvent | React.TouchEvent) => {
    setIsDragging(true);
    handleMove(e.nativeEvent as any);
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
      const container = document.getElementById("release-card-grids");
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
  }, [isDragging]);

  const getTooltipData = () => {
    if (!releases.length) return null;
    let index = Math.floor((currentValue / 100) * (releases.length - 1));

    if (direction === "descend") {
      index = releases.length - 1 - index;
    }

    const item = releases[Math.max(0, Math.min(releases.length - 1, index))];
    if (!item) return null;

    if (order === "release_date") {
      const date = parseISO(item.release_date);
      return {
        main: format(date, "d"),
        sub: format(date, "MMMM"),
      };
    }
    if (order === "artist_credit_name" || order === "release_name") {
      return {
        main: item[order].charAt(0).toUpperCase(),
        sub: "",
      };
    }
    if (order === "confidence") {
      return {
        main: `${Math.round((item.confidence ?? 0) * 100)}`,
        sub: "%",
      };
    }
    return null;
  };

  const tooltipData = getTooltipData();
  const visualPercent = mapLinearToVisual(currentValue, mappedMarks);

  return (
    <div className="releases-timeline">
      <div
        ref={trackRef}
        className="timeline-track vertical"
        onMouseDown={onStart}
        onTouchStart={onStart}
      >
        <div
          className="timeline-thumb vertical"
          style={{
            top: `${visualPercent}%`,
            height: `${thumbSize}px`,
            transition: isDragging ? "none" : "all 0.1s ease-out",
          }}
        />
        {isDragging && tooltipData && (
          <div
            className="timeline-tooltip vertical"
            style={{ top: `${visualPercent}%` }}
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
              key={mark.percent}
              className="timeline-mark vertical"
              style={{ top: `${mark.shiftedPercent}%` }}
            >
              <div className="tick-mark" />
              <span className="mark-label">{mark.label}</span>
            </div>
          ) : null
        )}
      </div>
    </div>
  );
}
