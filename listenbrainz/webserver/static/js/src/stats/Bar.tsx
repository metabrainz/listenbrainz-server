import * as React from "react";
import { ResponsiveBar, LabelFormatter } from "@nivo/bar";

export type BarProps = {
  data: UserEntityData;
  maxValue: number;
  width?: number;
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

  getReleaseLink = (data: UserEntityDatum, release: string) => {
    if (data.release && data.releaseMBID) {
      const res = (
        <a
          href={`http://musicbrainz.org/artist/${data.releaseMBID}`}
          target="_blank"
          rel="noopener noreferrer"
        >
          {release}
        </a>
      );
      return res;
    }
    return release;
  };

  render() {
    const { data, maxValue, width } = this.props;
    const marginLeft = Math.min((width || window.innerWidth) / 2, 400);
    const tableDigitWidth = data[0]?.idx.toString().length;

    const leftAlignedTick = (tick: Tick) => {
      const datum = data[tick.tickIndex];
      const { entity, artist, release, idx } = datum;

      return (
        <g transform={`translate(${tick.x - marginLeft}, ${tick.y})`}>
          <foreignObject
            height="3em"
            width={marginLeft}
            y={datum.entityType === "artist" ? -10 : -20}
          >
            <table
              style={{
                width: "90%",
                textAlign: "start",
                whiteSpace: "nowrap",
                tableLayout: "fixed",
              }}
            >
              <tbody>
                <tr style={{ color: "black" }}>
                  <td
                    style={{ width: `${tableDigitWidth}em`, textAlign: "end" }}
                  >
                    {idx}.&nbsp;
                  </td>
                  <td
                    style={{
                      textOverflow: "ellipsis",
                      overflow: "hidden",
                    }}
                  >
                    {this.getEntityLink(datum, entity)}
                  </td>
                </tr>
                {artist && (
                  <tr>
                    <td />
                    <td
                      style={{
                        fontSize: 12,
                        textOverflow: "ellipsis",
                        overflow: "hidden",
                      }}
                    >
                      {this.getArtistLink(datum, artist)}
                      {release && (
                        <span>
                          &nbsp;-&nbsp;{this.getReleaseLink(datum, release)}
                        </span>
                      )}
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
          {datum.data.entity}: <strong>{datum.value} Listens</strong>
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
        colors="#EB743B"
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
        animate={false}
      />
    );
  }
}
