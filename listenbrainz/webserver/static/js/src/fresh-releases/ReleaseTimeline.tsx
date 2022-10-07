import React, { useEffect, useState } from "react";
import Slider from "rc-slider";
import { formattedReleaseDate } from "./utils";

type ReleaseTimelineProps = {
  minDate: string;
  maxDate: string;
};

const style: React.CSSProperties = {
  height: "48rem",
  marginBottom: "10rem",
  marginLeft: "1rem",
};

const parentStyle = { overflow: "hidden" };

export default function ReleaseTimeline(props: ReleaseTimelineProps) {
  const { minDate, maxDate } = props;

  const [dateRange, setDateRange] = useState<Array<string>>([]);
  const [currentValue, setCurrentValue] = useState<number>(0);
  const [maxRange, setMaxRange] = useState<number>(3);

  function getDatesInRange(startDate: any, endDate: any) {
    const date = new Date(startDate.getTime());
    const dates = [];
    while (date <= endDate) {
      dates.push(new Date(date).toLocaleDateString());
      date.setDate(date.getDate() + 1);
    }
    setMaxRange(dates.length);
    setDateRange(dates);
  }

  const onDateChange = (newDate: any) => {
    setCurrentValue(newDate);
  };

  function fakeApiCall() {
    setCurrentValue(currentValue);
  }

  useEffect(() => {
    getDatesInRange(new Date(minDate), new Date(maxDate));
    setCurrentValue(currentValue);
  }, []);

  return (
    <div style={parentStyle}>
      <div style={style}>
        <div className="slider-legend">{formattedReleaseDate(minDate)}</div>
        <Slider
          vertical
          included={false}
          min={0}
          max={2}
          value={currentValue}
          defaultValue={1}
          onChange={onDateChange}
        />
        <div className="slider-legend">{formattedReleaseDate(maxDate)}</div>
      </div>
    </div>
  );
}
