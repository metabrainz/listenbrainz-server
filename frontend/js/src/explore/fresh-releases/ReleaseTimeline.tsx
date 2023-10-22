import * as React from "react";
import Slider from "rc-slider";
import { countBy, debounce, zipObject } from "lodash";
import { formatReleaseDate, useMediaQuery } from "./utils";

type ReleaseTimelineProps = {
  releases: Array<FreshReleaseItem>;
  order: string;
};

export default function ReleaseTimeline(props: ReleaseTimelineProps) {
  const { releases, order } = props;

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

  function createMarks(data: Array<FreshReleaseItem>) {
    let dataArr: Array<string> = [];
    let percentArr: Array<number> = [];
    if (order === "release_date") {
      const releasesPerDate = countBy(
        releases,
        (item: FreshReleaseItem) => item.release_date
      );

      dataArr = Object.keys(releasesPerDate).map((item) =>
        formatReleaseDate(item)
      );

      percentArr = Object.values(releasesPerDate)
        .map((item) => (item / data.length) * 100)
        .map((_, index, arr) =>
          arr.slice(0, index + 1).reduce((prev, curr) => prev + curr)
        );
    } else if (order === "artist_credit_name") {
      const artistInitialsCount = countBy(data, (item: FreshReleaseItem) =>
        item.artist_credit_name.charAt(0).toUpperCase()
      );

      dataArr = Object.keys(artistInitialsCount).sort();

      percentArr = Object.values(artistInitialsCount)
        .map((item) => (item / data.length) * 100)
        .map((_, index, arr) =>
          arr.slice(0, index + 1).reduce((prev, curr) => prev + curr)
        );
    } else {
      const releaseInitialsCount = countBy(data, (item: FreshReleaseItem) =>
        item.release_name.charAt(0).toUpperCase()
      );

      dataArr = Object.keys(releaseInitialsCount).sort();

      percentArr = Object.values(releaseInitialsCount)
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
    setMarks(createMarks(releases));
  }, [releases]);

  React.useEffect(() => {
    window.addEventListener("scroll", handleScroll);
    return () => {
      window.removeEventListener("scroll", handleScroll);
    };
  }, []);

  return (
    <div className="slider-container">
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
