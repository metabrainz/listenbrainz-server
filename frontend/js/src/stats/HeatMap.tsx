import * as React from "react";
import { HeatMap } from "@nivo/heatmap";
import { useMediaQuery } from "react-responsive";

export type HeatMapProps = {
  data: UserDailyActivityData;
  width: number;
};

export default function Heatmap(props: HeatMapProps) {
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
      width={width}
      height={height}
      enableLabels={false}
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
      hoverTarget="cell"
      colors={{ type: "sequential", scheme: "oranges" }}
      opacity={0.85}
      inactiveOpacity={0.85}
      activeOpacity={1}
      xInnerPadding={0.05}
      yInnerPadding={0.1}
      margin={isMobile ? margin.mobile : margin.desktop}
      forceSquare
    />
  );
}
