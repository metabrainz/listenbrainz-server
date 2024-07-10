import * as React from "react";
import {
  ResponsiveBar,
  BarDatum,
  BarTooltipProps,
  BarSvgProps,
} from "@nivo/bar";
import { omit } from "lodash";
import { BasicTooltip } from "@nivo/tooltip";
import { COLOR_LB_ORANGE } from "../../../utils/constants";

export type BarProps = {
  data: UserEntityData;
  maxValue: number;
} & Partial<BarSvgProps<any>>;

export default function Bar(props: BarProps) {
  const { data, maxValue, ...barProps } = props;

  const customTooltip = (tooltipProps: BarTooltipProps<BarDatum>) => {
    const { data: datum, value, color } = tooltipProps;
    return (
      <div className="graph-tooltip" style={{ zIndex: 150 }}>
        <BasicTooltip
          id={datum.entity}
          value={`${value} ${Number(value) === 1 ? "listen" : "listens"}`}
          color={color}
        />
      </div>
    );
  };

  const theme = {
    labels: {
      text: {
        fontSize: "16px",
        fontWeight: "bold",
        fill: "white",
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
      "artists",
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
      label={(x: any) => x.data.entity}
      labelSkipWidth={0}
      tooltip={customTooltip}
      margin={{
        bottom: 40,
        left: 15,
        right: 15,
      }}
      axisBottom={{
        tickSize: 0,
        tickValues: data?.length,
        tickPadding: 5,
        legend: "Number of listens",
        legendOffset: 30,
        legendPosition: "middle",
      }}
      axisLeft={null}
      theme={theme}
      keys={["count"]}
      animate={false}
      {...barProps}
    />
  );
}
