import { ResponsiveStream, TooltipProps } from "@nivo/stream";
import { format as d3Format } from "d3-format";
// eslint-disable-next-line import/no-extraneous-dependencies
import {  type OrdinalColorScaleConfig } from "@nivo/colors";
import * as React from "react";
import { faExclamationCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import Card from "../../../components/Card";
import Loader from "../../../components/Loader";
import GlobalAppContext from "../../../utils/GlobalAppContext";
import { useMediaQuery } from "../../../explore/fresh-releases/utils";

export type UserArtistEvolutionActivityProps = {
  range: UserStatsAPIRange;
  user?: ListenBrainzUser;
};

export type UserArtistEvolutionActivityGraphProps = {
  rawData: RawUserArtistEvolutionRow[];
  range: UserStatsAPIRange;
  colorPalette?: OrdinalColorScaleConfig;
  topN?: number;
};

export type StreamDataItem = {
  [key: string]: string | number;
};

const getLegendText = (timeRange: UserStatsAPIRange) => {
  switch (timeRange) {
    case "week":
    case "this_week":
      return "Days of the week";
    case "month":
    case "this_month":
      return "Days of the month";
    case "year":
    case "this_year":
      return "Months";
    default:
      return "Years";
  }
};

const renderCustomTooltip = (
  tooltipProps: any,
  orderedTimeUnits: string[],
  artistHref: (name: string) => string
) => {
  const { slice } = tooltipProps;

  if (!slice || typeof slice.index === "undefined") {
    return (
      <div
        className="bg-white p-2 border rounded"
        style={{
          fontSize: "12px",
          boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
          maxWidth: "240px",
        }}
      >
        <div>No data available</div>
      </div>
    );
  }

  return (
    <div
      className="bg-white p-2 border rounded"
      style={{
        fontSize: "12px",
        boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
        maxWidth: "240px",
      }}
    >
      <div className="mb-1 fw-bold">
        {orderedTimeUnits[slice.index] || `Period ${slice.index + 1}`}
      </div>
      {slice.stack &&
        slice.stack
          .filter((point: any) => point.data && point.data.value > 0)
          .map((point: any) => (
            <div key={`${point.id}-${point.data.value}`} className="mb-1">
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
              <a
                href={artistHref(point.id)}
                className="fw-bold text-decoration-none"
              >
                {point.id}
              </a>
              : {point.data.value} listens
            </div>
          ))}
    </div>
  );
};

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
      case "this_week":
        return timeUnit.substring(0, 3);
      case "month":
      case "this_month":
        return timeUnit;
      case "year":
      case "this_year":
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

const transformArtistEvolutionActivityData = (
  rawData: RawUserArtistEvolutionRow[] | undefined,
  statsRange: UserStatsAPIRange,
  topN: number = 10
): {
  chartData: StreamDataItem[];
  keys: string[];
  orderedTimeUnits: string[];
  offsetYear?: number;
  artistMap: Record<string, string>;
} => {
  if (!rawData || !Array.isArray(rawData) || rawData.length === 0) {
    return { chartData: [], keys: [], orderedTimeUnits: [], artistMap: {} };
  }

  const groupedByTime: Record<string, Record<string, number>> = {};
  const artistTotals: Record<string, number> = {};
  const artistMap: Record<string, string> = {};

  rawData.forEach((item) => {
    const timeUnit = String(item.time_unit);
    const name = item.artist_name;
    const count = item.listen_count || 0;
    if (!groupedByTime[timeUnit]) {
      groupedByTime[timeUnit] = {};
    }
    groupedByTime[timeUnit][name] = count;

    artistTotals[name] = (artistTotals[name] || 0) + count;
    artistMap[name] = item.artist_mbid;
  });

  const topArtists = Object.entries(artistTotals)
    .sort(([, a], [, b]) => b - a)
    .slice(0, topN)
    .reverse()
    .map(([name]) => name);

  let orderedTimeUnits: string[] = [];
  let offsetYear: number | undefined;

  if (statsRange.includes("week")) {
    orderedTimeUnits = [
      "Monday",
      "Tuesday",
      "Wednesday",
      "Thursday",
      "Friday",
      "Saturday",
      "Sunday",
    ];
  } else if (statsRange.includes("month")) {
    orderedTimeUnits = Array.from({ length: 31 }, (_, i) => String(i + 1));
  } else if (statsRange.includes("year")) {
    orderedTimeUnits = [
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
  } else {
    const nowYear = new Date().getFullYear();
    const yearsWithData = rawData.reduce<number[]>((acc, item) => {
      const y = parseInt(String(item.time_unit), 10);
      if (!Number.isNaN(y) && (item.listen_count || 0) > 0) {
        acc.push(y);
      }
      return acc;
    }, []);
    if (yearsWithData.length) {
      const firstYearWithData = Math.min(...yearsWithData);
      offsetYear = firstYearWithData - 1;
      const years: string[] = [];
      for (let y = offsetYear; y <= nowYear; y += 1) {
        years.push(String(y));
      }
      orderedTimeUnits = years;
    } else {
      orderedTimeUnits = [];
    }
  }

  const chartData: StreamDataItem[] = orderedTimeUnits.map((tu) => {
    const timeData = groupedByTime[tu] || {};
    const row: StreamDataItem = { id: tu };
    topArtists.forEach((artist) => {
      row[artist] = timeData[artist] ?? 0;
    });
    return row;
  });

  return {
    chartData,
    keys: topArtists,
    orderedTimeUnits,
    offsetYear,
    artistMap,
  };
};

export const artistEvolutionQueryKey = (
  userName: string | undefined,
  range: UserStatsAPIRange
) => ["userArtistEvolutionActivity", userName, range] as const;

export function UserArtistEvolutionActivityGraph(
  props: UserArtistEvolutionActivityGraphProps
) {
  const {
    rawData,
    range,
    topN = 10,
    colorPalette = { scheme: "nivo" },
  } = props;
  const navigate = useNavigate();
  const isMobile = useMediaQuery("(max-width: 767px)");

  const { chartData, keys, orderedTimeUnits, artistMap } = React.useMemo(
    () => transformArtistEvolutionActivityData(rawData, range, topN),
    [rawData, range, topN]
  );

  const artistHref = React.useCallback(
    (name: string) => {
      const mbid = artistMap[name];
      return mbid ? `/artist/${mbid}` : "#";
    },
    [artistMap]
  );

  const tooltipRenderer = React.useCallback(
    (tooltipProps: TooltipProps) =>
      renderCustomTooltip(tooltipProps as any, orderedTimeUnits, artistHref),
    [orderedTimeUnits, artistHref]
  );

  const maxValue = React.useMemo(() => {
    if (!chartData || chartData.length === 0) return 0;
    return Math.max(
      ...chartData.map((item) =>
        keys.reduce((sum, key) => sum + ((item[key] as number) || 0), 0)
      )
    );
  }, [chartData, keys]);

  const tickValues = React.useMemo(() => {
    return maxValue <= 10
      ? Array.from({ length: maxValue + 1 }, (_, i) => i)
      : undefined;
  }, [maxValue]);

  return (

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
            ? { top: 60, right: 20, bottom: 120, left: 40 }
            : { top: 60, right: 20, bottom: 60, left: 60 }
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
        axisLeft={{
          tickSize: 5,
          tickPadding: 5,
          tickRotation: 0,
          format: (value) => {
            if (!Number.isInteger(value)) return "";
            return value < 1000 ? value.toString() : d3Format(".2~s")(value);
          },
          tickValues,
        }}
        enableGridX
        enableGridY
        offsetType="none"
        order="ascending"
        curve="basis"
        colors={colorPalette}
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
          legends: { text: { fontSize: isMobile ? 10 : 12 } },
        }}
        legends={[
          {
            anchor: "top-left",
            direction: isMobile ? "row" : "column",
            translateX: 10,
            translateY: 10,
            itemWidth: isMobile ? 70 : 90,
            itemHeight: 18,
            itemTextColor: "#333333",
            symbolSize: 12,
            symbolShape: "circle",
            itemsSpacing: isMobile ? 6 : 2,
            itemBackground: "rgba(255,255,255,0.75)",
            itemOpacity: 1,
            effects: [
              {
                on: "hover",
                style: { itemTextColor: "#000000" },
              },
            ],
            onClick: (datum: any) => {
              const name = datum.label;
              const mbid = artistMap[name];
              if (mbid) navigate(`/artist/${mbid}`);
            },
          } as any,
        ]}
        tooltip={tooltipRenderer}
      />
    </div>
  );
}

export function UserArtistEvolutionActivityStats(
  props: UserArtistEvolutionActivityProps
) {
  const { APIService } = React.useContext(GlobalAppContext);
  const { user, range } = props;
  const isMobile = useMediaQuery("(max-width: 767px)");
  const [topN, setTopN] = React.useState<number>(10);
  const onTopNChange: React.ChangeEventHandler<HTMLSelectElement> = (e) => {
    setTopN(parseInt(e.target.value, 10));
  };

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

  if (hasError) {
    return (
      <Card className="user-stats-card" data-testid="artist-evolution">
        <div className="row">
          <div className="col-xs-10">
            <h3 className="capitalize-bold">Artist Evolution</h3>
          </div>
        </div>
        <div
          className="d-flex align-items-center justify-content-center"
          style={{ minHeight: "inherit" }}
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
      <div
        className={`d-flex align-items-center justify-content-between ${
          isMobile ? "mb-3" : ""
        } flex-wrap mt-3`}
      >
        <h3 className="capitalize-bold m-0">Artist Evolution</h3>
        <div className="d-flex align-items-center flex-shrink-0 gap-2">
          <label htmlFor="top-n-select" className="m-0">
            Top
          </label>
          <select
            id="top-n-select"
            className="form-select"
            value={topN}
            onChange={onTopNChange}
            aria-label="Select number of top artists to show"
            style={{ width: 80 }}
          >
            {[5, 10, 15].map((num) => (
              <option key={num} value={num}>
                {num}
              </option>
            ))}
          </select>
          <span>artists</span>
        </div>
      </div>
      <Loader isLoading={loading}>
        {rawData.payload.artist_evolution_activity.length === 0 ? (
          <div
            className="d-flex align-items-center justify-content-center"
            style={{ minHeight: "300px" }}
          >
            <span style={{ fontSize: 18 }}>
              No artist evolution data available for this time period
            </span>
          </div>
        ) : (
          <div className="row">
            <div className="col-xs-12">
              <UserArtistEvolutionActivityGraph
                rawData={rawData.payload.artist_evolution_activity}
                range={range}
                topN={topN}
              />
            </div>
          </div>
        )}
      </Loader>
    </Card>
  );
}

export default UserArtistEvolutionActivityStats;
