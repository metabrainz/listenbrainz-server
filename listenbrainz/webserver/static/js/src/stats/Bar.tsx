import * as React from "react";
import { ResponsiveBar, LabelFormatter } from "@nivo/bar";

import getEntityLink from "./utils";
import ListenCard from "../listens/ListenCard";

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

    const listenFormat: BaseListenFormat = {
      listened_at: -1,
      track_metadata: {
        track_name: entityName,
        artist_name: artistName ?? "",
        release_name: releaseName,
        additional_info: {
          artist_mbids: artistMBIDs,
          recording_mbid: entityType === "recording" ? entityMBID : undefined,
          release_mbid: releaseMBID,
        },
      },
    };

    let artistMBID;
    if (artistMBIDs) {
      [artistMBID] = artistMBIDs;
    }
    const thumbnail = <>{idx}.&nbsp;</>;

    const listenDetails = (
      <>
        <div title={entityName} className="ellipsis">
          {getEntityLink(entityType, entityName, entityMBID)}
        </div>

        <div
          className="small text-muted ellipsis"
          title={`${artistName || ""}, ${releaseName || ""}`}
        >
          {artistName && getEntityLink("artist", artistName, artistMBID)}
          {releaseName && (
            <span>
              &nbsp;-&nbsp;
              {getEntityLink("release", releaseName, releaseMBID)}
            </span>
          )}
        </div>
      </>
    );

    return (
      <g transform={`translate(${tick.x - marginLeft}, ${tick.y})`}>
        <foreignObject
          height="3.5em"
          width={marginLeft}
          y={datum.entityType === "artist" ? -10 : -20}
        >
          <ListenCard
            thumbnail={thumbnail}
            mini
            listenDetails={listenDetails}
            listen={listenFormat}
            showTimestamp={false}
            showUsername={false}
            currentFeedback={0}
            isCurrentListen={false}
            playListen={() => {
              console.log("Play this song, would you?");
            }}
            newAlert={(...args) => {
              console.log("Alert!", ...args);
            }}
          />
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
