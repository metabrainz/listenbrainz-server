import * as React from "react";
import Slider from "rc-slider";
import { countBy, debounce, zipObject } from "lodash";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCalendarCheck } from "@fortawesome/free-solid-svg-icons";
import {
  startOfDay,
  format,
  closestTo,
  parseISO,
  differenceInCalendarDays,
  isEqual,
} from "date-fns";
import { formatReleaseDate, useMediaQuery } from "../utils";
import { SortDirection } from "../FreshReleases";
import { COLOR_LB_BLUE } from "../../../utils/constants";

type ReleaseTimelineProps = {
  releases: Array<FreshReleaseItem>;
  order: string;
  direction: SortDirection;
};

function createMarks(
  releases: Array<FreshReleaseItem>,
  sortDirection: string,
  order: string
) {
  let dataArr: Array<string | JSX.Element> = [];
  let percentArr: Array<number> = [];
  // We want to filter out the keys that have less than 1.5% of the total releases
  const minReleasesThreshold = Math.floor(releases.length * 0.015);
  if (order === "release_date") {
    const releasesPerDate = countBy(
      releases,
      (item: FreshReleaseItem) => item.release_date
    );
    const releasesperDateKeys = Object.keys(releasesPerDate);
    const parsedDates = releasesperDateKeys.map((d) => parseISO(d));
    const todaysDate = startOfDay(new Date());
    const closestDate = closestTo(todaysDate, parsedDates) ?? todaysDate;
    const closestDateStr = format(closestDate, "yyyy-MM-dd");
    const title = isEqual(closestDate, todaysDate) ? "Today" : "Nearest Date";

    const filteredDates = releasesperDateKeys.filter(
      (date, idx, arr) => {
        if (date === closestDateStr) {
          // Always keep the closest-to-now date to show a 'today' calendar icon
          return true;
        }
        if (releasesPerDate[date] > minReleasesThreshold) {
          // multiple releases that day, keep this date in the timeline
          return true;
        }
        if (idx === 0) {
          // keep the first date
          return true;
        }
        const daysSinceLastDate = differenceInCalendarDays(
          parseISO(date),
          parseISO(arr[idx - 1])
        );
        if (daysSinceLastDate >= 7) {
          // A week since the last date, show this one to keep the timeline useful
          return true;
        }
        return false;
      }
    );
    // Used to calculate the percentage on the timeline for dates placement
    const filteredReleasesTotal = filteredDates.reduce(
      (acc, date) => acc + releasesPerDate[date],
      0
    );

    dataArr = filteredDates.map((date) =>
      date === closestDateStr ? (
        <FontAwesomeIcon
          icon={faCalendarCheck}
          size="2xl"
          color={COLOR_LB_BLUE}
          title={title}
        />
      ) : (
        formatReleaseDate(date)
      )
    );
    percentArr = filteredDates
      .map((item) => (releasesPerDate[item] / filteredReleasesTotal) * 100)
      .map((_, index, arr) =>
        arr.slice(0, index + 1).reduce((prev, curr) => prev + curr)
      );
  } else if (order === "artist_credit_name") {
    const artistInitialsCount = countBy(releases, (item: FreshReleaseItem) =>
      item.artist_credit_name.charAt(0).toUpperCase()
    );
    const filteredInitials = Object.keys(artistInitialsCount).filter(
      (initial) => artistInitialsCount[initial] >= minReleasesThreshold
    );

    dataArr = filteredInitials.sort();
    percentArr = filteredInitials
      .map((item) => (artistInitialsCount[item] / releases.length) * 100)
      .map((_, index, arr) =>
        arr.slice(0, index + 1).reduce((prev, curr) => prev + curr)
      );
  } else if (order === "release_name") {
    const releaseInitialsCount = countBy(releases, (item: FreshReleaseItem) =>
      item.release_name.charAt(0).toUpperCase()
    );
    const filteredInitials = Object.keys(releaseInitialsCount).filter(
      (initial) => releaseInitialsCount[initial] >= minReleasesThreshold
    );

    dataArr = filteredInitials.sort();
    percentArr = filteredInitials
      .map((item) => (releaseInitialsCount[item] / releases.length) * 100)
      .map((_, index, arr) =>
        arr.slice(0, index + 1).reduce((prev, curr) => prev + curr)
      );
  } else {
    // conutBy gives us an asc-sorted Dict by confidence
    const confidenceInitialsCount = countBy(
      releases,
      (item: FreshReleaseItem) => item?.confidence
    );
    dataArr = Object.keys(confidenceInitialsCount);
    percentArr = Object.values(confidenceInitialsCount)
      .map((item) => (item / releases.length) * 100)
      .map((_, index, arr) =>
        arr.slice(0, index + 1).reduce((prev, curr) => prev + curr)
      );
  }

  if (sortDirection === "descend") {
    dataArr.reverse();
    percentArr = percentArr.reverse().map((v) => (v <= 100 ? 100 - v : 0));
  }

  /**
   * We want the timeline dates or marks to start where the grid starts.
   * So the 0% should always have the first date. Therefore we use unshift(0) here.
   * With the same logic, we don't want the last date to be at 100% because
   * that will mean we're at the bottom of the grid.
   * The last date should start before 100%. That explains the pop().
   * For descending sort, the reverse computation above possibly already ensures that
   * the percentArr starts with 0 and ends with a non-100% value, which is desired.
   * Hence, we add a check to skip the unshift(0) and pop() operations in that case.
   */
  if (percentArr[0] !== 0) {
    percentArr.unshift(0);
    percentArr.pop();
  }

  return zipObject(percentArr, dataArr);
}

export default function ReleaseTimeline(props: ReleaseTimelineProps) {
  const { releases, order, direction } = props;

  const [currentScrollValue, setCurrentScrollValue] = React.useState<number | number[]>();
  const [marks, setMarks] = React.useState<{ [key: number]: React.ReactNode }>(
    {}
  );

  const screenMd = useMediaQuery("(max-width: 992px)"); // @screen-md

  const changeHandler = React.useCallback((percent: number | number[]) => {
    setCurrentScrollValue(percent);
    const element: HTMLElement | null = document.getElementById(
      "release-card-grids"
    )!;
    const scrollHeight = ((percent as number) / 100) * element.scrollHeight;
    const scrollTo = scrollHeight + element.offsetTop;
    window.scrollTo({ top: scrollTo, behavior: "smooth" });
    return scrollTo;
  }, []);

  React.useEffect(() => {
    setMarks(createMarks(releases, direction, order));
  }, [releases, direction, order]);

  React.useEffect(() => {
    const handleScroll = debounce(() => {
      const container = document.getElementById("release-card-grids");
      if (!container) {
        return;
      }
      const scrollPos =
        ((window.scrollY - container.offsetTop) / container.scrollHeight) * 100;
      setCurrentScrollValue(scrollPos);
    }, 500);

    window.addEventListener("scroll", handleScroll);
    return () => {
      handleScroll.cancel();
      window.removeEventListener("scroll", handleScroll);
    };
  }, []);

  return (
    <div className="releases-timeline">
      <Slider
        className={screenMd ? "slider-horizontal" : "slider-vertical"}
        vertical={!screenMd}
        reverse={!screenMd}
        included={false}
        marks={marks}
        value={currentScrollValue}
        onChange={changeHandler}
      />
    </div>
  );
}
