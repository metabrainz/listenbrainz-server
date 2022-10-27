import * as React from "react";
import Slider from "rc-slider";
import { countBy, zipObject } from "lodash";
import { formattedReleaseDate, useMediaQuery } from "./utils";

type ReleaseTimelineProps = {
  releases: Array<FreshReleaseItem>;
};

export default function ReleaseTimeline(props: ReleaseTimelineProps) {
  const { releases } = props;

  const minDate = releases[0].release_date;
  const maxDate = releases[releases.length - 1].release_date;

  const [minSliderDate, setMinSliderDate] = React.useState<number>(0);
  const [maxSliderDate, setMaxSliderDate] = React.useState<number>(100);
  const [currentValue, setCurrentValue] = React.useState<number>();
  const [marks, setMarks] = React.useState<{ [key: number]: string }>({});

  const screenMd = useMediaQuery("(max-width: 992px)");

  function getDatesInRange(startDate: any, endDate: any) {
    const date = new Date(startDate.getTime());
    const dates = [];
    while (date <= endDate) {
      dates.push(new Date(date).toLocaleDateString("en-US"));
      date.setDate(date.getDate() + 1);
    }
    setMinSliderDate(new Date(dates[0]).getTime());
    setMaxSliderDate(new Date(dates[dates.length - 1]).getTime());
  }

  // let's keep the type to any until we figure out a proper one
  const changeHandler = React.useCallback((percent: any) => {
    setCurrentValue(percent);
    const element: HTMLElement | null = document.getElementById(
      "release-cards-grid"
    )!;
    const scrollHeight = (percent / 100) * element.scrollHeight;
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

  React.useEffect(() => {
    getDatesInRange(new Date(minDate), new Date(maxDate));
    setMarks(createMarks(releases));
  }, [releases]);

  function renderSlider() {
    if (minSliderDate && maxSliderDate) {
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
    return <div className="text-muted">Couldn&apos;t load timeline</div>;
  }

  return renderSlider();
}
