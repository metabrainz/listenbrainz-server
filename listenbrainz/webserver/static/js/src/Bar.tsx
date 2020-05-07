/* eslint-disable */
import React from "react";
import { ResponsiveBar } from "@nivo/bar";

export type BarProps = {
  data: Array<object>;
};

export default class Bar extends React.Component<BarProps> {
  render() {
    const { data } = this.props;

    return (
      <ResponsiveBar
        data={data}
        layout="horizontal"
        colors="#FD8D3C"
        indexBy="id"
        enableGridY={false}
        margin={{
          left: 300,
        }}
        axisLeft={{
          tickPadding: 115,
        }}
        keys={["Listens"]}
      />
    );
  }
}
