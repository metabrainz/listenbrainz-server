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

  const screenMd = useMediaQuery("(max-width: 992px)"); // @screen-md

  const formatTooltip = (value: number): string => {
    let result = "";
    Object.entries(marks)
      .reverse()
      .forEach(([key, val]) => {
        if (value >= +key && result === "") {
          result = val;
        }
      });
    return result;
  };

  const tooltipHandle = (props: any) => {
    const { value, dragging, index, ...restProps } = props;
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
    setCurrentValue(percent);
    const element: HTMLElement | null = document.getElementById(
      "release-cards-grid"
    )!;
    const scrollHeight = ((percent as number) / 100) * element.scrollHeight;
    const scrollTo = scrollHeight + element.offsetTop;
    window.scrollTo({ top: scrollTo, behavior: "smooth" });
    return scrollTo;
  }, []);

  function createMarks(data: Array<FreshReleaseItem>) {
    const releasesPerDate = countBy(
      releases,
      (item: FreshReleaseItem) => item.release_date
    );
    const datesArr = Object.keys(releasesPerDate).map((item) =>
      formatReleaseDate(item)
    );
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
    setCurrentValue(middle);
    window.scrollTo({ top: changeHandler(middle), behavior: "smooth" });
    return zipObject(percentArr, datesArr);
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
        handle={tooltipHandle}
      />
    </div>
  );
}
