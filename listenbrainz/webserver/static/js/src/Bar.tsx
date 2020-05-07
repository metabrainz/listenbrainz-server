/* eslint-disable */
import React from "react";
import { ResponsiveBar, LabelFormatter } from "@nivo/bar";

export type BarProps = {
  data: Array<object>;
};

export default class Bar extends React.Component<BarProps> {
  render() {
    const { data } = this.props;
    const marginLeft = 150;

    const leftAlignedTick = (tick: any) => {
      return (
        <g transform={`translate(${tick.x - marginLeft}, ${tick.y})`}>
          <text textAnchor="start" dominantBaseline="middle">
            {tick.value}
          </text>
        </g>
      );
    };

    const theme = {
      axis: {
        ticks: {
          text: {
            fontSize: "14px",
          },
        },
      },
      labels: {
        text: {
          fontSize: "14px",
        },
      },
    };

    const labelFormatter = (((label: string) => {
      return (
        <tspan x={5} textAnchor="start">
          {label}
        </tspan>
      );
    }) as unknown) as LabelFormatter;

    return (
      <ResponsiveBar
        data={data}
        layout="horizontal"
        colors="#FD8D3C"
        indexBy="id"
        enableGridY={false}
        padding={0.15}
        labelFormat={labelFormatter}
        labelSkipWidth={0}
        margin={{
          left: marginLeft,
        }}
        axisLeft={{
          renderTick: leftAlignedTick,
        }}
        theme={theme}
        keys={["Listens"]}
      />
    );
  }
}
