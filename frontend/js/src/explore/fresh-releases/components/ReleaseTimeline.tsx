import * as React from "react";
import Slider from "rc-slider";
import { countBy, debounce, zipObject } from "lodash";
import { formatReleaseDate, useMediaQuery } from "../utils";
import { SortDirection } from "../FreshReleases";

type ReleaseTimelineProps = {
  releases: Array<FreshReleaseItem>;
  order: string;
  direction: SortDirection;
};

export default function ReleaseTimeline(props: ReleaseTimelineProps) {
  const { releases, order, direction } = props;

  const [currentValue, setCurrentValue] = React.useState<number | number[]>();
  const [marks, setMarks] = React.useState<{ [key: number]: string }>({});

  const screenMd = useMediaQuery("(max-width: 992px)"); // @screen-md

  const changeHandler = React.useCallback((percent: number | number[]) => {
    setCurrentValue(percent);
    const element: HTMLElement | null = document.getElementById(
      "release-card-grids"
    )!;
    const scrollHeight = ((percent as number) / 100) * element.scrollHeight;
    const scrollTo = scrollHeight + element.offsetTop;
    window.scrollTo({ top: scrollTo, behavior: "smooth" });
    return scrollTo;
  }, []);

  function createMarks(data: Array<FreshReleaseItem>, sortDirection: string) {
    let dataArr: Array<string> = [];
    let percentArr: Array<number> = [];
    // We want to filter out the keys that have less than 1.5% of the total releases
    const minReleasesThreshold = Math.floor(data.length * 0.015);
    if (order === "release_date") {
      const releasesPerDate = countBy(
        releases,
        (item: FreshReleaseItem) => item.release_date
      );
      const filteredDates = Object.keys(releasesPerDate).filter(
        (date) => releasesPerDate[date] >= minReleasesThreshold
      );

      if (sortDirection === "descend") {
        filteredDates.reverse();
      }

      dataArr = filteredDates.map((item) => formatReleaseDate(item));
      percentArr = filteredDates
        .map((item) => (releasesPerDate[item] / data.length) * 100)
        .map((_, index, arr) =>
          arr.slice(0, index + 1).reduce((prev, curr) => prev + curr)
        );
    } else if (order === "artist_credit_name") {
      const artistInitialsCount = countBy(data, (item: FreshReleaseItem) =>
        item.artist_credit_name.charAt(0).toUpperCase()
      );
      const filteredInitials = Object.keys(artistInitialsCount).filter(
        (initial) => artistInitialsCount[initial] >= minReleasesThreshold
      );

      dataArr = filteredInitials.sort();
      if (sortDirection === "descend") {
        dataArr.reverse();
      }

      percentArr = filteredInitials
        .map((item) => (artistInitialsCount[item] / data.length) * 100)
        .map((_, index, arr) =>
          arr.slice(0, index + 1).reduce((prev, curr) => prev + curr)
        );
    } else if (order === "release_name") {
      const releaseInitialsCount = countBy(data, (item: FreshReleaseItem) =>
        item.release_name.charAt(0).toUpperCase()
      );
      const filteredInitials = Object.keys(releaseInitialsCount).filter(
        (initial) => releaseInitialsCount[initial] >= minReleasesThreshold
      );

      dataArr = filteredInitials.sort();
      if (sortDirection === "descend") {
        dataArr.reverse();
      }

      percentArr = filteredInitials
        .map((item) => (releaseInitialsCount[item] / data.length) * 100)
        .map((_, index, arr) =>
          arr.slice(0, index + 1).reduce((prev, curr) => prev + curr)
        );
    } else {
      const confidenceInitialsCount = countBy(
        data,
        (item: FreshReleaseItem) => item?.confidence
      );

      dataArr = Object.keys(confidenceInitialsCount).sort();
      if (sortDirection === "descend") {
        dataArr.reverse();
      }

      percentArr = Object.values(confidenceInitialsCount)
        .map((item) => (item / data.length) * 100)
        .map((_, index, arr) =>
          arr.slice(0, index + 1).reduce((prev, curr) => prev + curr)
        );
    }

    /**
     * We want the timeline dates or marks to start where the grid starts.
     * So the 0% should always have the first date. Therefore we use unshift(0) here.
     * With the same logic, we don't want the last date to be at 100% because
     * that will mean we're at the bottom of the grid.
     * The last date should start before 100%. That explains the pop().
     */
    percentArr.unshift(0);
    percentArr.pop();

    return zipObject(percentArr, dataArr);
  }

  const handleScroll = React.useCallback(
    debounce(() => {
      // TODO change to relative position of #release-cards-grid instead of window
      const scrollPos =
        (window.scrollY / document.documentElement.scrollHeight) * 100;
      setCurrentValue(scrollPos);
    }, 300),
    []
  );

  React.useEffect(() => {
    setMarks(createMarks(releases, direction));
  }, [releases, direction]);

  React.useEffect(() => {
    window.addEventListener("scroll", handleScroll);
    return () => {
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
        value={currentValue}
        onChange={changeHandler}
      />
    </div>
  );
}
