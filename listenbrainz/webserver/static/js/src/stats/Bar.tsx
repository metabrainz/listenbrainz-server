import * as React from "react";
import { ResponsiveBar, LabelFormatter } from "@nivo/bar";

export type BarProps = {
  data: UserEntityData;
  maxValue: number;
};

type Tick = {
  format: undefined | LabelFormatter;
  lineX: number;
  lineY: number;
  rotate: number;
  textAnchor: React.CSSProperties["textAnchor"];
  textBaseline: React.CSSProperties["dominantBaseline"];
  textX: number;
  textY: number;
  tickIndex: number;
  x: number;
  y: number;
  value: string;
};

export default function Bar(props: BarProps) {
  const { data, maxValue } = props;

  const renderTickValue = (tick: any): React.ReactNode => {
    const datum: UserEntityDatum = data[tick.tickIndex];
    const { idx } = datum;
    return (
      <g transform={`translate(${tick.x - 10}, ${tick.y + 7})`}>
        <text textAnchor="end">{idx}.</text>
      </g>
    );
  };

  const labelFormatter = (((label: string) => {
    return (
      <tspan x={5} textAnchor="start">
        {label}
      </tspan>
    );
  }) as unknown) as LabelFormatter;

  const customTooltip = (datum: any) => {
    return (
      <div>
        {datum.data.entity}: <strong>{datum.value} Listens</strong>
      </div>
    );
  };

  const theme = {
    labels: {
      text: {
        fontSize: "14px",
      },
    },
  };
  return (
    <ResponsiveBar
      data={data}
      maxValue={maxValue}
      layout="horizontal"
      colors="#EB743B"
      indexBy="id"
      enableGridY={false}
      padding={0.1}
      labelFormat={labelFormatter}
      labelSkipWidth={0}
      tooltip={customTooltip}
      margin={{
        top: -12,
        left: 35,
      }}
      axisLeft={{
        tickSize: 0,
        tickValues: data.length,
        tickPadding: 5,
        renderTick: renderTickValue,
      }}
      theme={theme}
      keys={["count"]}
      animate={false}
    />
  );
}
