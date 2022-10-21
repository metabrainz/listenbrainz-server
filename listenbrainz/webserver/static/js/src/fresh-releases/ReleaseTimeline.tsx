import React, { useEffect, useState } from "react";
import Slider from "rc-slider";
import { countBy, zipObject } from "lodash";
import formattedReleaseDate from "./utils";

type ReleaseTimelineProps = {
  releases: Array<FreshReleaseItem>;
};

export default function ReleaseTimeline(props: ReleaseTimelineProps) {
  const { releases } = props;

  const minDate = releases[0].release_date;
  const maxDate = releases[releases.length - 1].release_date;

  const [minSliderDate, setMinSliderDate] = useState<number>(0);
  const [maxSliderDate, setMaxSliderDate] = useState<number>(100);
  const [currentValue, setCurrentValue] = useState<number>(51);
  const [marks, setMarks] = useState<{ [key: number]: string }>({});

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

  function createMarks(data: Array<FreshReleaseItem>) {
    const releasesPerDate = countBy(releases, (item) => item.release_date);
    const datesArr = Object.keys(releasesPerDate).map((item) =>
      formattedReleaseDate(item)
    );
    const percentArr = Object.values(releasesPerDate)
      .map((item) => Math.floor((item / data.length) * 100))
      .map((_, index, arr) =>
        arr.slice(0, index + 1).reduce((prev, curr) => prev + curr)
      );
    percentArr.unshift(0);
    percentArr.pop();
    return zipObject(percentArr, datesArr);
  }

  // let's keep the type to any until we figure out a proper one
  function changeHandler(percent: any) {
    setCurrentValue(percent);
    const pageScrollHeight = document.documentElement.scrollHeight;
    const scrollYPx = (percent / 100) * pageScrollHeight;
    window.scrollTo(0, Math.round(scrollYPx));
  }

  useEffect(() => {
    getDatesInRange(new Date(minDate), new Date(maxDate));
    setMarks(createMarks(releases));
  }, [releases]);

  function renderSlider() {
    if (minSliderDate && maxSliderDate) {
      return (
        <div className="slider">
          <div className="slider-legend">{formattedReleaseDate(minDate)}</div>
          <Slider
            vertical
            reverse
            included={false}
            marks={marks}
            value={currentValue}
            onChange={() => changeHandler}
          />
          <div className="slider-legend">{formattedReleaseDate(maxDate)}</div>
        </div>
      );
    }
    return <div className="text-muted">Couldn&apos;t load timeline</div>;
  }

  return renderSlider();
}
