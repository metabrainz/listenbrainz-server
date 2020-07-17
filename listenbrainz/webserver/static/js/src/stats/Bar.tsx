import * as React from "react";
import { ResponsiveBar, LabelFormatter } from "@nivo/bar";

import getEntityLink from "./utils";

export type BarProps = {
  data: UserEntityData;
  maxValue: number;
  width?: number;
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
  const { data, maxValue, width } = props;
  const marginLeft = Math.min((width || window.innerWidth) / 2, 400);
  const tableDigitWidth = data[0]?.idx.toString().length;

  const leftAlignedTick = <Tick extends any>(tick: Tick) => {
    const datum = data[tick.tickIndex];
    const {
      entityType,
      entity: entityName,
      entityMBID,
      artist: artistName,
      artistMBID: artistMBIDs,
      release: releaseName,
      releaseMBID,
      idx,
    } = datum;

    let artistMBID;
    if (artistMBIDs) {
      [artistMBID] = artistMBIDs;
    }

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
              whiteSpace: "nowrap",
              tableLayout: "fixed",
            }}
          >
            <tbody>
              <tr style={{ color: "black" }}>
                <td style={{ width: `${tableDigitWidth}em`, textAlign: "end" }}>
                  {idx}.&nbsp;
                </td>
                <td
                  style={{
                    textOverflow: "ellipsis",
                    overflow: "hidden",
                  }}
                >
                  {getEntityLink(entityType, entityName, entityMBID)}
                </td>
              </tr>
              {artistName && (
                <tr>
                  <td />
                  <td
                    style={{
                      fontSize: 12,
                      textOverflow: "ellipsis",
                      overflow: "hidden",
                    }}
                  >
                    {getEntityLink("artist", artistName, artistMBID)}
                    {releaseName && (
                      <span>
                        &nbsp;-&nbsp;
                        {getEntityLink("release", releaseName, releaseMBID)}
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
