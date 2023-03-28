import * as React from "react";
import {
  ResponsiveBar,
  LabelFormatter,
  BarDatum,
  BarTooltipProps,
} from "@nivo/bar";
import type { AxisTickProps } from "@nivo/axes";
import { omit } from "lodash";
import { BasicTooltip } from "@nivo/tooltip";
import { COLOR_LB_ORANGE } from "../utils/constants";

export type BarProps = {
  data: UserEntityData;
  maxValue: number;
};

export default function Bar(props: BarProps) {
  const { data, maxValue } = props;

  const renderTickValue = (tick: AxisTickProps<any>): JSX.Element => {
    const datum: UserEntityDatum = data?.[tick.tickIndex];
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

  const customTooltip = (tooltipProps: BarTooltipProps<BarDatum>) => {
    const { data: datum, value, color } = tooltipProps;
    return (
      <BasicTooltip
        id={datum.entity}
        value={`${value} ${Number(value) === 1 ? "listen" : "listens"}`}
        color={color}
      />
    );
  };

  const theme = {
    labels: {
      text: {
        fontSize: "14px",
      },
    },
  };
  const typescriptCompliantData: BarDatum[] = data?.map((datum) =>
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
      colors={COLOR_LB_ORANGE}
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
        tickValues: data?.length,
        tickPadding: 5,
        renderTick: renderTickValue,
      }}
      theme={theme}
      keys={["count"]}
      animate={false}
    />
  );
}
