import * as React from "react";
import { ResponsiveBar, LabelFormatter, BarDatum } from "@nivo/bar";
import type { AxisTickProps } from "@nivo/axes";
import { omit } from "lodash";

export type BarProps = {
  data: UserEntityData;
  maxValue: number;
};

export default function Bar(props: BarProps) {
  const { data, maxValue } = props;

  const renderTickValue = (tick: AxisTickProps<any>): JSX.Element => {
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
  const typescriptCompliantData: BarDatum[] = data.map((datum) =>
    omit(datum, [
      "entityMBID",
      "artist",
      "artistMBID",
      "release",
      "releaseMBID",
    ])
  );
  return (
    <ResponsiveBar
      data={typescriptCompliantData}
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
