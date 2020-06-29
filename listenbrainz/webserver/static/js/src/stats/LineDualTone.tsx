/* eslint-disable react/prefer-stateless-function */
import * as React from "react";

import { ResponsiveLine } from "@nivo/line";
import { LegendProps } from "@nivo/legends";

export type LineDualToneProps = {
  data: UserListeningActivityData;
  dateFormat: {};
  showLegend?: boolean;
};

export default class LineDualTone extends React.Component<LineDualToneProps> {
  render() {
    const { data, dateFormat, showLegend } = this.props;

    const customTooltip = (datum: any) => {
      const { point } = datum;
      return (
        <div
          style={{
            background: "white",
            padding: "3px 6px",
            border: "1px solid #ccc",
          }}
        >
          {(point.data.date as Date).toLocaleString("en-us", {
            ...dateFormat,
            timeZone: "UTC",
          })}
          : <strong>{point.data.y} Listens</strong>
        </div>
      );
    };

    return (
      <ResponsiveLine
        data={data}
        xScale={{ type: "point" }}
        yScale={{
          type: "linear",
          stacked: false,
          min: 0,
        }}
        axisBottom={{
          tickSize: 5,
          tickPadding: 5,
        }}
        margin={{
          top: showLegend ? 30 : 20,
          left: 50,
          right: 30,
          bottom: 40,
        }}
        colors={({ id }) =>
          id.toLowerCase().includes("this") || id.toLowerCase() === "all time"
            ? "#EB743B"
            : "#353070"
        }
        lineWidth={2.7}
        curve="natural"
        enableCrosshair={false}
        layers={["axes", "lines", "points", "mesh", "legends"]}
        tooltip={customTooltip}
        legends={
          showLegend
            ? [
                {
                  anchor: "top-right",
                  symbolShape: "circle",
                  symbolSize: 10,
                  direction: "row",
                  itemWidth: 90,
                  itemHeight: 10,
                  translateX: 20,
                  translateY: -20,
                } as LegendProps,
              ]
            : []
        }
        useMesh
      />
    );
  }
}
