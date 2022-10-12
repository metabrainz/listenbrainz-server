import React, { useEffect, useState } from "react";
import Slider from "rc-slider";
import { formattedReleaseDate } from "./utils";

type ReleaseTimelineProps = {
  releases: Array<FreshReleaseItem>;
};

export default function ReleaseTimeline(props: ReleaseTimelineProps) {
  const { releases } = props;

  const minDate = releases[0].release_date;
  const maxDate = releases[releases.length - 1].release_date;

  const [minSliderDate, setMinSliderDate] = useState<number>(0);
  const [maxSliderDate, setMaxSliderDate] = useState<number>(100);
  const [currentValue, setCurrentValue] = useState<number>(
    new Date().getTime()
  );

  const MS_TO_DAY = 1000 * 60 * 60 * 24;

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

  const onDateChange = (newDate: any) => {
    setCurrentValue(newDate);
  };

  useEffect(() => {
    getDatesInRange(new Date(minDate), new Date(maxDate));
    setCurrentValue(currentValue);
  }, []);

  function renderSlider() {
    if (minSliderDate && maxSliderDate) {
      return (
        <div className="slider">
          <div className="slider-legend">{formattedReleaseDate(minDate)}</div>
          <Slider
            vertical
            included={false}
            step={MS_TO_DAY}
            min={minSliderDate}
            max={maxSliderDate}
            value={currentValue}
            onChange={onDateChange}
          />
          <div className="slider-legend">{formattedReleaseDate(maxDate)}</div>
        </div>
      );
    }
    return <div className="text-muted">Couldn&apos;t load timeline</div>;
  }

  return renderSlider();
}
