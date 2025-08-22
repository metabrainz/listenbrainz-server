import { ResponsiveStream, TooltipProps } from "@nivo/stream";
import * as React from "react";
import { faExclamationCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { useQuery } from "@tanstack/react-query";
import { toPairs } from "lodash";
import {
  getDaysInMonth,
  eachYearOfInterval,
  startOfYear,
  endOfYear,
  format,
} from "date-fns";
import Card from "../../../components/Card";
import Loader from "../../../components/Loader";
import GlobalAppContext from "../../../utils/GlobalAppContext";
import { useMediaQuery } from "../../../explore/fresh-releases/utils";

export type UserArtistEvolutionActivityProps = {
  range: UserStatsAPIRange;
  user?: ListenBrainzUser;
};

export type StreamDataItem = {
  [key: string]: string | number;
};

// Transform function to convert API response to stream chart format
const transformArtistEvolutionActivityData = (
  rawData: UserArtistEvolutionActivityResponse["payload"]["artist_evolution_activity"]
) => {
  if (!rawData || !Array.isArray(rawData) || rawData.length === 0) {
    return { chartData: [], keys: [] };
  }

  // Calculate total listens per artist to get top 10
  const artistTotals = rawData
    .flatMap(toPairs)
    .reduce<Record<string, number>>((acc, [artist, count]) => {
      // Skip the 'id' field and only process actual artist data
      if (artist !== "id" && typeof count === "number") {
        return { ...acc, [artist]: (acc[artist] || 0) + count };
      }
      return acc;
    }, {});

  // Get top 10 artists by total listens
  const topArtists = Object.entries(artistTotals)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 10)
    .map(([name]) => name);

  // Transform the data for the stream chart
  const chartData = rawData.map((timeUnit, index) => {
    const result: StreamDataItem = {
      id: (timeUnit && (timeUnit as any).id) || index.toString(),
    };

    topArtists.forEach((artist) => {
      result[artist] =
        (timeUnit &&
          typeof timeUnit === "object" &&
          (timeUnit as any)[artist]) ||
        0;
    });

    return result;
  });

  return { chartData, keys: topArtists };
};

function getAllTimeYearLabels(opts: {
  offsetYear?: number;
  from_ts?: number;
  to_ts?: number;
}) {
  // Simpler + clearer: compute start/end with date-fns and cap end at the current year.
  const now = new Date();

  let start: Date;
  if (opts.from_ts) {
    start = startOfYear(new Date(opts.from_ts * 1000));
  } else if (opts.offsetYear) {
    start = startOfYear(new Date(opts.offsetYear, 0, 1));
  } else {
    start = startOfYear(now);
  }

  const endRaw = endOfYear(opts.to_ts ? new Date(opts.to_ts * 1000) : now);
  const end = endRaw > now ? endOfYear(now) : endRaw;

  return eachYearOfInterval({ start, end }).map((d) => format(d, "yyyy"));
}

const getAxisFormatter = (
  timeRange: UserStatsAPIRange,
  orderedTimeUnits: string[],
  isMobile: boolean = false
) => {
  return (index: number) => {
    const timeUnit = orderedTimeUnits[index];
    if (!timeUnit) return "";

    switch (timeRange) {
      case "week":
        return timeUnit.substring(0, 3);
      case "month":
        return timeUnit;
      case "year":
        return timeUnit.substring(0, 3);
      case "all_time": {
        if (isMobile) {
          const year = parseInt(timeUnit, 10);
          return year % 5 === 0 ? timeUnit : "";
        }
        return timeUnit;
      }
      default:
        return timeUnit;
    }
  };
};

const getOrderedTimeUnits = (
  timeRange: UserStatsAPIRange,
  offsetYear: number | undefined,
  from_ts?: number,
  to_ts?: number
) => {
  if (timeRange.includes("week")) {
    return [
      "Monday",
      "Tuesday",
      "Wednesday",
      "Thursday",
      "Friday",
      "Saturday",
      "Sunday",
    ];
  }
  if (timeRange.includes("month")) {
    const daysInCurrentMonth = getDaysInMonth(new Date());
    return Array.from({ length: daysInCurrentMonth }, (_, i) =>
      (i + 1).toString()
    );
  }
  if (timeRange.includes("year")) {
    return [
      "January",
      "February",
      "March",
      "April",
      "May",
      "June",
      "July",
      "August",
      "September",
      "October",
      "November",
      "December",
    ];
  }
  if (timeRange.includes("all_time")) {
    return getAllTimeYearLabels({ offsetYear, from_ts, to_ts });
  }
  return ["Period 1", "Period 2", "Period 3", "Period 4", "Period 5"];
};

const renderCustomTooltip = (tooltipProps: any, orderedTimeUnits: string[]) => {
  const { slice } = tooltipProps;

  if (!slice || typeof slice.index === "undefined") {
    return (
      <div
        style={{
          background: "white",
          padding: "9px 12px",
          border: "1px solid #ccc",
          borderRadius: "4px",
          fontSize: "12px",
          boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
          maxWidth: "200px",
        }}
      >
        <div>No data available</div>
      </div>
    );
  }

  return (
    <div
      style={{
        background: "white",
        padding: "9px 12px",
        border: "1px solid #ccc",
        borderRadius: "4px",
        fontSize: "12px",
        boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
        maxWidth: "200px",
      }}
    >
      <div style={{ marginBottom: "4px", fontWeight: "bold" }}>
        {orderedTimeUnits[slice.index] || `Period ${slice.index + 1}`}
      </div>
      {slice.stack &&
        slice.stack
          .filter((point: any) => point.data && point.data.value > 0)
          .map((point: any) => (
            <div
              key={`${point.id}-${point.data.value}`}
              style={{ marginBottom: "2px" }}
            >
              <span
                style={{
                  display: "inline-block",
                  width: "12px",
                  height: "12px",
                  backgroundColor: point.color,
                  marginRight: "6px",
                  borderRadius: "2px",
                }}
              />
              <span style={{ fontWeight: "bold" }}>{point.id}:</span>{" "}
              {point.data.value} listens
            </div>
          ))}
    </div>
  );
};

const getLegendText = (timeRange: UserStatsAPIRange) => {
  switch (timeRange) {
    case "week":
      return "Days of the week";
    case "month":
      return "Days of the month";
    case "year":
      return "Months";
    default:
      return "Years";
  }
};

export const artistEvolutionQueryKey = (
  userName: string | undefined,
  range: UserStatsAPIRange
) => ["userArtistEvolutionActivity", userName, range] as const;

export default function ArtistEvolutionActivityStreamGraph(
  props: UserArtistEvolutionActivityProps
) {
  const { APIService } = React.useContext(GlobalAppContext);
  const { user, range } = props;

  const { data: loaderData, isLoading: loading } = useQuery({
    queryKey: artistEvolutionQueryKey(user?.name, range),
    queryFn: async () => {
      try {
        const queryData = (await APIService.getUserArtistEvolutionActivity(
          user?.name,
          range
        )) as UserArtistEvolutionActivityResponse;
        return { data: queryData, hasError: false, errorMessage: "" };
      } catch (error) {
        return {
          data: {
            payload: {
              artist_evolution_activity: [],
              offset_year: 2020,
              range,
              from_ts: 0,
              to_ts: 0,
              last_updated: 0,
              user_id: user?.name ?? "",
            },
          } as UserArtistEvolutionActivityResponse,
          hasError: true,
          errorMessage: (error as Error).message,
        };
      }
    },
  });

  const {
    data: rawData = {
      payload: {
        artist_evolution_activity: [],
        offset_year: 2020,
        range,
        from_ts: 0,
        to_ts: 0,
        last_updated: 0,
        user_id: user?.name ?? "",
      },
    } as UserArtistEvolutionActivityResponse,
    hasError = false,
    errorMessage = "",
  } = loaderData || {};

  const isMobile = useMediaQuery("(max-width: 767px)");

  const { chartData = [], keys = [] } = transformArtistEvolutionActivityData(
    rawData.payload.artist_evolution_activity
  );

  const orderedTimeUnits = getOrderedTimeUnits(
    range,
    rawData.payload.offset_year,
    (rawData as any).payload.from_ts,
    (rawData as any).payload.to_ts
  );

  const tooltipRenderer = React.useCallback(
    (tooltipProps: TooltipProps) =>
      renderCustomTooltip(tooltipProps, orderedTimeUnits),
    [orderedTimeUnits]
  );

  if (hasError) {
    return (
      <Card className="user-stats-card" data-testid="artist-evolution">
        <div className="row">
          <div className="col-xs-10">
            <h3 className="capitalize-bold">Artist Evolution</h3>
          </div>
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            minHeight: "inherit",
          }}
        >
          <span style={{ fontSize: 24 }}>
            <FontAwesomeIcon icon={faExclamationCircle as IconProp} />{" "}
            {errorMessage}
          </span>
        </div>
      </Card>
    );
  }

  return (
    <Card className="user-stats-card" data-testid="artist-evolution">
      <div className="row">
        <div className="col-xs-10">
          <h3 className="capitalize-bold">Artist Evolution</h3>
        </div>
      </div>
      <Loader isLoading={loading}>
        {chartData.length === 0 ? (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              minHeight: "300px",
            }}
          >
            <span style={{ fontSize: 18 }}>
              No artist evolution data available for this time period
            </span>
          </div>
        ) : (
          <div className="row">
            <div className="col-xs-12">
              <div
                style={{ width: "100%", height: isMobile ? "500px" : "600px" }}
                data-testid="artist-evolution-stream"
                aria-label="artist-evolution-stream"
              >
                <ResponsiveStream
                  data={chartData}
                  keys={keys}
                  margin={
                    isMobile
                      ? { top: 20, right: 20, bottom: 120, left: 40 }
                      : { top: 20, right: 100, bottom: 60, left: 60 }
                  }
                  axisBottom={{
                    format: getAxisFormatter(range, orderedTimeUnits, isMobile),
                    tickSize: 5,
                    tickPadding: 5,
                    legend: getLegendText(range),
                    legendOffset: 40,
                    legendPosition: "middle",
                    tickRotation: isMobile ? -45 : 0,
                  }}
                  axisLeft={{ tickSize: 5, tickPadding: 5, tickRotation: 0 }}
                  enableGridX
                  enableGridY
                  offsetType="diverging"
                  colors={{ scheme: "nivo" }}
                  fillOpacity={0.85}
                  borderColor={{ theme: "background" }}
                  dotSize={8}
                  dotColor={{ from: "color" }}
                  dotBorderWidth={2}
                  dotBorderColor={{
                    from: "color",
                    modifiers: [["darker", 0.7]],
                  }}
                  theme={{
                    axis: {
                      ticks: {
                        text: {
                          fontSize: isMobile ? 10 : 12,
                          fill: "#333333",
                        },
                      },
                    },
                    grid: {
                      line: {
                        stroke: "#dddddd",
                        strokeWidth: 1,
                      },
                    },
                  }}
                  legends={[
                    {
                      anchor: isMobile ? "bottom" : "right",
                      direction: isMobile ? "row" : "column",
                      translateX: isMobile ? 0 : 100,
                      translateY: isMobile ? 80 : 0,
                      itemWidth: isMobile ? 60 : 80,
                      itemHeight: 20,
                      itemTextColor: "#333333",
                      symbolSize: 12,
                      symbolShape: "circle",
                      itemsSpacing: isMobile ? 5 : 0,
                      effects: [
                        {
                          on: "hover",
                          style: { itemTextColor: "#000000" },
                        },
                      ],
                    },
                  ]}
                  tooltip={tooltipRenderer}
                />
              </div>
            </div>
          </div>
        )}
      </Loader>
    </Card>
  );
}
