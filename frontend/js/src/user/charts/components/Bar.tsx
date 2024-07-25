import * as React from "react";
import {
  ResponsiveBar,
  BarDatum,
  BarTooltipProps,
  BarSvgProps,
} from "@nivo/bar";
import { TooltipWrapper } from "@nivo/tooltip";
import { COLOR_LB_ORANGE } from "../../../utils/constants";

export type BarProps = {
  data: UserEntityData;
  maxValue: number;
  isMobileSize?: boolean;
} & Partial<BarSvgProps<any>>;

export default function Bar(props: BarProps) {
  const { data, maxValue, isMobileSize, ...barProps } = props;

  const customTooltip = (tooltipProps: BarTooltipProps<BarDatum>) => {
    const { data: datum, value } = tooltipProps;
    return (
      <TooltipWrapper anchor="center" position={[0, 0]}>
        <div className="graph-tooltip" id={datum.entity.toString()}>
          <span className="badge badge-info">#{datum.idx}</span> {datum.entity}
          :&nbsp;
          <b>
            {value} {Number(value) === 1 ? "listen" : "listens"}
          </b>
          {datum.artist && <div>{datum.artist}</div>}
        </div>
      </TooltipWrapper>
    );
  };

  const theme = {
    labels: {
      text: {
        fontSize: "15px",
        fontFamily: "'Sintony', sans-serif",
      },
    },
  };
  const numberOfTicks = isMobileSize
    ? Math.min(5, maxValue)
    : Math.min(9, maxValue);

  const horizontalAxis = {
    tickSize: 5,
    tickValues: numberOfTicks,
    tickPadding: 5,
    legend: "Number of listens",
    legendOffset: 30,
  };

  return (
    <ResponsiveBar
      data={data}
      maxValue={maxValue}
      layout="horizontal"
      colors={COLOR_LB_ORANGE}
      indexBy="id"
      enableGridY={false}
      enableGridX
      gridXValues={numberOfTicks}
      padding={0.1}
      label={(x: any) => x.data.entity}
      labelSkipWidth={0}
      tooltip={customTooltip}
      margin={{
        bottom: 40,
        left: 15,
        right: 15,
      }}
      axisBottom={{ ...horizontalAxis, legendPosition: "middle" }}
      axisTop={{
        ...horizontalAxis,
        legendPosition: "middle",
        legendOffset: -30,
      }}
      axisLeft={null}
      theme={theme}
      keys={["count"]}
      animate={false}
      {...barProps}
    />
  );
}
