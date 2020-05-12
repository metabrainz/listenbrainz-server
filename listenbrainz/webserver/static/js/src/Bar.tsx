import * as React from "react";
import { ResponsiveBar, LabelFormatter } from "@nivo/bar";

export type BarProps = {
  data: Array<object>;
  maxValue: number;
};

export type BarState = {
  marginLeft: number;
};

export default class Bar extends React.Component<BarProps, BarState> {
  constructor(props: BarProps) {
    super(props);

    this.state = {
      marginLeft: window.innerWidth / 5,
    };
  }

  componentDidMount() {
    window.addEventListener("resize", this.handleResize);
  }

  componentWillUnmount() {
    window.removeEventListener("resize", this.handleResize);
  }

  handleResize = () => {
    this.setState({
      marginLeft: window.innerWidth / 5,
    });
  };

  render() {
    const { data, maxValue } = this.props;
    const { marginLeft } = this.state;

    const leftAlignedTick = (tick: any) => {
      let { value } = tick;
      if (value.length > marginLeft / 10) {
        value = `${value.slice(0, marginLeft / 10)}...`;
      }

      return (
        <g transform={`translate(${tick.x - marginLeft}, ${tick.y})`}>
          <text textAnchor="start" dominantBaseline="middle">
            {value}
          </text>
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
      // Strip intial number
      const index = datum.indexValue.substring(
        datum.indexValue.indexOf(" ") + 1
      );

      return (
        <div>
          {index}: <strong>{datum.value} Listens</strong>
        </div>
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

    return (
      <ResponsiveBar
        data={data}
        maxValue={maxValue}
        layout="horizontal"
        colors="#FD8D3C"
        indexBy="id"
        enableGridY={false}
        padding={0.15}
        labelFormat={labelFormatter}
        labelSkipWidth={0}
        tooltip={customTooltip}
        margin={{
          left: marginLeft,
        }}
        axisLeft={{
          renderTick: leftAlignedTick,
        }}
        theme={theme}
        keys={["count"]}
      />
    );
  }
}
