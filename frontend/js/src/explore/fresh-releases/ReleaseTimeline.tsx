import * as React from "react";
import Slider from "rc-slider";
import { countBy, debounce, zipObject } from "lodash";
import { formatReleaseDate, useMediaQuery } from "./utils";

type ReleaseTimelineProps = {
  releases: Array<FreshReleaseItem>;
};

export default function ReleaseTimeline(props: ReleaseTimelineProps) {
  const { releases } = props;
  const { Handle } = Slider;
  const [currentValue, setCurrentValue] = React.useState<number>();
  const [marks, setMarks] = React.useState<{ [key: number]: string }>({});
  const [tooltipMarks, setTooltipMarks] = React.useState<{
    [key: number]: string;
  }>({});

  const screenMd = useMediaQuery("(max-width: 992px)"); // @screen-md

  const formatTooltip = (value: number): string => {
    let result = "";
    Object.entries(tooltipMarks)
      .reverse()
      .forEach(([key, val]) => {
        if (value >= +key && result === "") {
          result = val;
        }
      });
    return result;
  };

  const tooltipHandle = (handleprops: any) => {
    const { value, dragging, index, ...restProps } = handleprops;
    const tooltipDate = formatTooltip(value);
    return (
      <Handle value={value} {...restProps}>
        {dragging && (
          <div className="rc-custom-tooltip">
            <div className="tooltip-text">
              <h3>{tooltipDate.slice(0, 2)}</h3>
              <h4>{tooltipDate.slice(2)}</h4>
            </div>
          </div>
        )}
      </Handle>
    );
  };

  const changeHandler = React.useCallback((percent: number) => {
    const element: HTMLElement | null = document.getElementById(
      "release-cards-grid"
    )!;
    const scrollPosition = ((percent as number) / 100) * element.scrollHeight;
    element.scrollTo({ top: scrollPosition, behavior: "smooth" });
    setCurrentValue(percent);
  }, []);

  function createMarks(data: Array<FreshReleaseItem>) {
    const releasesPerDate = countBy(
      releases,
      (item: FreshReleaseItem) => item.release_date
    );
    const dates = Object.keys(releasesPerDate).map((item) =>
      formatReleaseDate(item)
    );

    const datesArr = dates.map((date) => date.slice(0, 6));

    const percentArr = Object.values(releasesPerDate)
      .map((item) => (item / data.length) * 100)
      .map((_, index, arr) =>
        arr.slice(0, index + 1).reduce((prev, curr) => prev + curr)
      );

    /**
     * We want the timeline dates or marks to start where the grid starts.
     * So the 0% should always have the first date. Therefore we use unshift(0) here.
     * With the same logic, we don't want the last date to be at 100% because
     * that will mean we're at the bottom of the grid.
     * The last date should start before 100%. That explains the pop().
     */
    percentArr.unshift(0);
    percentArr.pop();
    const middle = percentArr[Math.floor(percentArr.length / 2)];

    // Scroll to the current date
    changeHandler(middle);

    setMarks(zipObject(percentArr, datesArr));
    setTooltipMarks(zipObject(percentArr, dates));
  }

  const handleScroll = React.useCallback(
    debounce(() => {
      // TODO change to relative position of #release-cards-grid instead of window
      const scrollPos =
        (window.scrollY / document.documentElement.scrollHeight) * 100;
      changeHandler(scrollPos);
    }, 300),
    []
  );

  React.useEffect(() => {
    createMarks(releases);
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
        handle={tooltipHandle}
      />
    </div>
  );
}
