import { ResponsiveStream } from "@nivo/stream";
import * as React from "react";
import { faExclamationCircle, faLink } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { useQuery } from "@tanstack/react-query";
import Card from "../../../components/Card";
import Loader from "../../../components/Loader";
import { COLOR_BLACK } from "../../../utils/constants";
import GlobalAppContext from "../../../utils/GlobalAppContext";

export type UserArtistEvolutionProps = {
  range: UserStatsAPIRange;
  user?: ListenBrainzUser;
};

export type StreamDataItem = {
  [key: string]: string | number;
};

// Transform function to convert API response to stream chart format
// Transform function to convert API response to stream chart format
const transformArtistEvolutionData = (
  rawData: any[] | null | undefined,
  timeRange: UserStatsAPIRange
) => {
  if (!rawData || !Array.isArray(rawData) || rawData.length === 0) {
    return { chartData: [], keys: [] };
  }

  // First, extract all unique artist names across all time units
  // Exclude 'id' field which is metadata, not artist data
  const allArtistNames = new Set<string>();
  rawData.forEach((timeUnit) => {
    if (timeUnit && typeof timeUnit === "object") {
      Object.keys(timeUnit).forEach((key) => {
        // Skip the 'id' field - it's metadata, not an artist
        if (key !== "id") {
          allArtistNames.add(key);
        }
      });
    }
  });

  // Calculate total listens per artist to get top 5
  const artistTotals: Record<string, number> = {};
  rawData.forEach((timeUnit) => {
    if (timeUnit && typeof timeUnit === "object") {
      Object.entries(timeUnit).forEach(([artist, count]) => {
        // Skip the 'id' field and only process actual artist data
        if (artist !== "id" && typeof count === "number") {
          if (!artistTotals[artist]) {
            artistTotals[artist] = 0;
          }
          artistTotals[artist] += count;
        }
      });
    }
  });

  // Get top 5 artists by total listens
  const topArtists = Object.entries(artistTotals)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 5)
    .map(([name]) => name);

  // Transform the data for the stream chart
  const chartData = rawData.map((timeUnit, index) => {
    const result: StreamDataItem = {
      // Use the id from the backend data if available, otherwise fall back to index
      id: (timeUnit && timeUnit.id) || index.toString(),
    };

    // Add each top artist's data for this time unit
    topArtists.forEach((artist) => {
      result[artist] =
        (timeUnit && typeof timeUnit === "object" && timeUnit[artist]) || 0;
    });

    return result;
  });

  return { chartData, keys: topArtists };
};

// Format function for axis labels based on range with mobile responsiveness
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
      case "all_time":
        // For mobile, show only every 5th year
        if (isMobile) {
          const year = parseInt(timeUnit, 10);
          if (year % 5 === 0) {
            return timeUnit;
          }
          return "";
        }
        return timeUnit;
      default:
        return timeUnit;
    }
  };
};

// Helper function to get ordered time units
const getOrderedTimeUnits = (
  timeRange: UserStatsAPIRange,
  offsetYear: number | undefined
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
    return Array.from({ length: 30 }, (_, i) => (i + 1).toString());
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
    const currentYear = new Date().getFullYear();
    const safeOffsetYear = offsetYear || 2020;
    const yearRange = currentYear - safeOffsetYear + 1;
    return Array.from({ length: yearRange }, (_, i) =>
      (safeOffsetYear + i).toString()
    );
  }
  return ["Period 1", "Period 2", "Period 3", "Period 4", "Period 5"];
};

// Custom tooltip function moved outside of render
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
        {orderedTimeUnits[slice.index] || `Time Unit ${slice.index + 1}`}
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

export default function ArtistEvolutionStreamGraph(
  props: UserArtistEvolutionProps
) {
  const { APIService } = React.useContext(GlobalAppContext);

  // Props
  const { user, range } = props;

  // Mobile detection hook
  const [isMobile, setIsMobile] = React.useState(false);

  // Check for mobile screen size
  React.useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth <= 768);
    };

    checkMobile();
    window.addEventListener("resize", checkMobile);

    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  // API data fetching
  const { data: loaderData, isLoading: loading } = useQuery({
    queryKey: ["ArtistEvolution", user?.name, range],
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
            result: [],
            offset_year: 2020,
          } as UserArtistEvolutionActivityResponse,
          hasError: true,
          errorMessage: error.message,
        };
      }
    },
  });

  const {
    data: rawData = {
      result: [],
      offset_year: 2020,
    } as UserArtistEvolutionActivityResponse,
    hasError = false,
    errorMessage = "",
  } = loaderData || {};

  const [chartData, setChartData] = React.useState<StreamDataItem[]>([]);
  const [keys, setKeys] = React.useState<string[]>([]);
  const [orderedTimeUnits, setOrderedTimeUnits] = React.useState<string[]>([]);

  // Create memoized tooltip function to prevent recreation on each render
  const tooltipRenderer = React.useCallback(
    (tooltipProps: any) => renderCustomTooltip(tooltipProps, orderedTimeUnits),
    [orderedTimeUnits]
  );

  // Transform data when raw data changes
  React.useEffect(() => {
    if (
      rawData?.result &&
      Array.isArray(rawData.result) &&
      rawData.result.length > 0
    ) {
      const {
        chartData: transformedData,
        keys: transformedKeys,
      } = transformArtistEvolutionData(rawData.result, range);

      setChartData(transformedData);
      setKeys(transformedKeys);
      setOrderedTimeUnits(getOrderedTimeUnits(range, rawData.offset_year));
    } else {
      setChartData([]);
      setKeys([]);
      setOrderedTimeUnits([]);
    }
  }, [rawData, range]);

  // Helper functions for rendering different legend texts
  const getLegendText = (timeRange: UserStatsAPIRange) => {
    if (timeRange === "week") return "Days of Week";
    if (timeRange === "month") return "Days of Month";
    if (timeRange === "year") return "Months";
    return "Years";
  };

  let content;
  if (hasError) {
    content = (
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
    );
  } else if (chartData.length === 0) {
    content = (
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
    );
  } else {
    content = (
      <div className="row">
        <div className="col-xs-12">
          <div style={{ width: "100%", height: isMobile ? "500px" : "600px" }}>
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
              axisLeft={{
                tickSize: 5,
                tickPadding: 5,
                tickRotation: 0,
              }}
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
                      style: {
                        itemTextColor: "#000000",
                      },
                    },
                  ],
                },
              ]}
              tooltip={tooltipRenderer}
            />
          </div>
        </div>
      </div>
    );
  }

  return (
    <Card className="user-stats-card" data-testid="artist-evolution">
      <div className="row">
        <div className="col-xs-10">
          <h3 className="capitalize-bold">Artist Evolution</h3>
        </div>
      </div>
      <Loader isLoading={loading}>{content}</Loader>
    </Card>
  );
}
