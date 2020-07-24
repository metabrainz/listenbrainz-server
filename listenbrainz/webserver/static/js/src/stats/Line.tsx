import * as React from "react";
import { ResponsiveLine } from "@nivo/line";

export type LineProps = {
  data: UserDailyActivityData;
};

export default function Line(props: LineProps) {
  const { data } = props;

  return (
    <ResponsiveLine
      data={data}
      xScale={{
        type: "time",
        format: "%H",
      }}
      xFormat="time:%H"
      axisBottom={{
        format: "%H",
        tickValues: "every hour",
      }}
      colors={{ scheme: "oranges", size: 7 }}
      curve="monotoneX"
      enableGridX={false}
      enableGridY={false}
      margin={{
        top: 20,
        bottom: 40,
        right: 20,
        left: 40,
      }}
      enableSlices="x"
      enablePoints={false}
    />
  );
}
