import * as React from "react";

import { ResponsiveLine, Serie } from "@nivo/line";

export type LineDualToneProps = {
  data: Serie[];
};

export default class LineDualTone extends React.Component {
  render() {
    const { data } = this.props;

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
          {(point.data.x as Date).toLocaleString("en-us", {
            day: "2-digit",
            month: "long",
            year: "numeric",
            timeZone: "UTC",
          })}
          : <strong>{point.data.y} Listens</strong>
        </div>
      );
    };

    return (
      <ResponsiveLine
        data={data}
        xScale={{ type: "time", format: "%s", useUTC: true }}
        xFormat="time:%s"
        yScale={{
          type: "linear",
          stacked: false,
        }}
        axisLeft={null}
        axisBottom={{
          format: "%A",
          tickSize: 5,
          tickPadding: 5,
          tickValues: "every 1 day",
        }}
        margin={{
          top: 20,
          left: 30,
          right: 30,
          bottom: 60,
        }}
        colors={({ id }) =>
          id.toLowerCase().includes("this") ? "#EB743B" : "#353070"
        }
        curve="natural"
        enableCrosshair={false}
        layers={["axes", "lines", "points", "mesh"]}
        tooltip={customTooltip}
        useMesh
      />
    );
  }
}
