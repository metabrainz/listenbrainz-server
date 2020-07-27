import * as React from "react";
import { HeatMap } from "@nivo/heatmap";
import { useMediaQuery } from "react-responsive";

export type HeatMapProps = {
  data: UserDailyActivityData;
  width: number;
};

export default function Heatmap(props: any) {
  const isMobile = useMediaQuery({ maxWidth: 767 });

  const margin = {
    desktop: {
      left: 80,
      bottom: 50,
      top: 10,
      right: 20,
    },
    mobile: {
      left: 40,
      right: 10,
      bottom: 40,
    },
  };

  const { data, width } = props;
  const height = (isMobile ? width / 2.7 : width / 3) + 10;

  return (
    <HeatMap
      data={data}
      indexBy="day"
      colors="oranges"
      keys={Array.from(Array(24).keys()).map((elem) => String(elem))}
      width={width}
      height={height}
      enableLabels={false}
      padding={1}
      cellOpacity={1}
      axisBottom={{
        legend: `Hour (${Intl.DateTimeFormat().resolvedOptions().timeZone})`,
        legendPosition: "middle",
        legendOffset: 35,
        format: isMobile
          ? (tick: any) => {
              return Number(tick) % 3 === 0 ? tick : "";
            }
          : undefined,
      }}
      axisLeft={{
        format: isMobile
          ? (tick: any) => {
              if (tick === "Average") {
                return "Avg";
              }
              return tick.slice(0, 3);
            }
          : undefined,
      }}
      axisTop={null}
      theme={{
        axis: {
          legend: {
            text: {
              fontWeight: "bold",
            },
          },
        },
      }}
      hoverTarget="column"
      margin={isMobile ? margin.mobile : margin.desktop}
      forceSquare
    />
  );
}
