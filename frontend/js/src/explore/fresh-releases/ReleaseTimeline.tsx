import * as React from "react";
import Slider from "rc-slider";
import { countBy, debounce, zipObject } from "lodash";
import { formatReleaseDate, useMediaQuery } from "./utils";

type ReleaseTimelineProps = {
  releases: Array<FreshReleaseItem>;
};

export default function ReleaseTimeline(props: ReleaseTimelineProps) {
  const { releases } = props;

  const [currentValue, setCurrentValue] = React.useState<number | number[]>();
  const [marks, setMarks] = React.useState<{ [key: number]: string }>({});

  const screenMd = useMediaQuery("(max-width: 992px)"); // @screen-md
  // Clicking on a date will trigger the changeHandler() function that accepts a percentage value from the
  // slider’s current position and returns the position to scroll to on the page.
  // This scrolls the page to the respective date.
  // This was made possible by the createMarks() function that calculates a percent value for
  // the number of releases per date in the releases list. This function creates an object that
  // the slider uses to create the marks on the slider. The handleScroll() is a debounced function
  //  triggered every time the user manually changes the scroll position.

  const { createSliderWithTooltip } = Slider;
  const Range = createSliderWithTooltip(Slider.Range);
  const { Handle } = Slider;

  const changeHandler = React.useCallback((percent: number | number[]) => {
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
    const percentArr1 = Object.values(releasesPerDate).map(
      (item) => (item / data.length) * 100
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
    percentArr.splice(-2, 1);
    // percentArr.pop();
    const middle = percentArr[Math.floor(percentArr.length / 2)];

    // Scroll to the current date
    setCurrentValue(middle);
    window.scrollTo({ top: changeHandler(middle), behavior: "smooth" });
    console.log("zipobject", zipObject(percentArr, datesArr));
    return zipObject(percentArr, datesArr);
  }

  const handleScroll = React.useCallback(
    debounce(() => {
      // TODO change to relative position of #release-cards-grid instead of window
      // calculate as per the height of the card
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
        // tipProps={{
        //   visible: true,
        //   placement: "top",
        //   prefixCls: "rc-slider-tooltip",
        // }}
      />
    </div>
  );
}
