import * as React from "react";
import Slider from "rc-slider";
import { countBy, debounce, zipObject } from "lodash";
import { formattedReleaseDate, useMediaQuery } from "./utils";

type ReleaseTimelineProps = {
  releases: Array<FreshReleaseItem>;
};

export default function ReleaseTimeline(props: ReleaseTimelineProps) {
  const { releases } = props;

  const [currentValue, setCurrentValue] = React.useState<number | number[]>();
  const [marks, setMarks] = React.useState<{ [key: number]: string }>({});

  const screenMd = useMediaQuery("(max-width: 992px)"); // @screen-md

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
      formattedReleaseDate(item)
    );
    const percentArr = Object.values(releasesPerDate)
      .map((item) => (item / data.length) * 100)
      .map((_, index, arr) =>
        arr.slice(0, index + 1).reduce((prev, curr) => prev + curr)
      );
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
      const scrollPos = (scrollY / document.documentElement.scrollHeight) * 100;
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
