import * as React from "react";
import { ResponsiveLine } from "@nivo/line";
import { useMediaQuery } from "react-responsive";

export type LineProps = {
  data: UserDailyActivityData;
};

export default function Line(props: LineProps) {
  const isMobile = useMediaQuery({ maxWidth: 767 });

  const { data } = props;

  return (
    <ResponsiveLine
      data={data}
      xScale={{
        type: "time",
        format: "%H",
      }}
      yScale={{
        type: "linear",
        min: 0,
      }}
      xFormat="time:%H"
      axisBottom={{
        format: "%H",
        tickValues: isMobile ? "every 3 hours" : "every hour",
        legend: `Hour (${Intl.DateTimeFormat().resolvedOptions().timeZone})`,
        legendOffset: 36,
        legendPosition: "middle",
      }}
      axisLeft={{
        format: ".2~s",
      }}
      colors={({ color }) => color}
      curve="monotoneX"
      enableGridX={false}
      enableGridY={false}
      margin={{
        top: 10,
        bottom: 50,
        right: 20,
        left: 40,
      }}
      enableSlices="x"
      enablePoints={false}
      legends={[
        {
          anchor: "top-right",
          direction: "column",
          justify: false,
          itemDirection: "left-to-right",
          itemWidth: 80,
          itemHeight: 20,
          itemOpacity: 0.75,
          symbolSize: 12,
          onClick: (datum) => alert(JSON.stringify(datum)),
          effects: [
            {
              on: "hover",
              style: {
                itemBackground: "rgba(0, 0, 0, .03)",
                itemOpacity: 1,
              },
            },
          ],
        },
      ]}
    />
  );
}
