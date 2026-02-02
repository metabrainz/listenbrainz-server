import * as React from "react";
import { ResponsiveHeatMap } from "@nivo/heatmap";
import { useMediaQuery } from "react-responsive";

export type HeatMapProps = {
  data: UserDailyActivityData;
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

  const { data } = props;
  return (
    <div
      className="stats-full-width-graph user-listen-heatmap"
      data-testid="heatmap"
    >
      <ResponsiveHeatMap
        data={data}
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
    </div>
  );
}
