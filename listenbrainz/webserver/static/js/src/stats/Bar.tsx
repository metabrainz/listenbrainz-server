import * as React from "react";
import { ResponsiveBar, LabelFormatter } from "@nivo/bar";

export type BarProps = {
  data: UserEntityData;
  maxValue: number;
};

export type BarState = {
  marginLeft: number;
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

  getEntityLink = (data: UserEntityDatum, entity: string) => {
    if (data.entityMBID) {
      return (
        <a
          href={`http://musicbrainz.org/${data.entityType}/${data.entityMBID}`}
          target="_blank"
          rel="noopener noreferrer"
        >
          {entity}
        </a>
      );
    }
    return entity;
  };

  getArtistLink = (data: UserEntityDatum, artist: string) => {
    if (data.artistMBID && data.artistMBID.length) {
      return (
        <a
          href={`http://musicbrainz.org/artist/${data.artistMBID[0]}`}
          target="_blank"
          rel="noopener noreferrer"
        >
          {artist}
        </a>
      );
    }
    return artist;
  };

  render() {
    const { data, maxValue } = this.props;
    const { marginLeft } = this.state;

    const leftAlignedTick = (tick: Tick) => {
      const datum = data[tick.tickIndex];
      let { entity, artist } = datum;
      const { idx } = datum;

      if (entity.length + String(idx).length + 3 > marginLeft / 10) {
        entity = `${entity.slice(0, marginLeft / 10)}...`;
      }
      if (artist && artist.length + String(idx).length + 3 > marginLeft / 10) {
        artist = `${artist.slice(0, marginLeft / 10)}...`;
      }
      return (
        <g transform={`translate(${tick.x - marginLeft}, ${tick.y})`}>
          <foreignObject
            height="100%"
            width="100%"
            y={datum.entityType === "artist" ? -10 : -20}
          >
            <table style={{ color: "black", textAlign: "start" }}>
              <tbody>
                <tr>
                  <td>{idx}.&nbsp;</td>
                  <td>{this.getEntityLink(datum, entity)}</td>
                </tr>
                {artist && (
                  <tr>
                    <td />
                    <td style={{ fontSize: 12 }}>
                      {this.getArtistLink(datum, artist)}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </foreignObject>
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
          {datum.indexValue}: <strong>{datum.value} Listens</strong>
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
        indexBy="entity"
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
        animate={false}
      />
    );
  }
}
