import { ResponsivePie } from "@nivo/pie";
import * as React from "react";
import { faExclamationCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { useQuery } from "@tanstack/react-query";
import { scaleSequential } from "d3-scale";
import { interpolateRainbow } from "d3-scale-chromatic";
import Card from "../../../components/Card";
import Loader from "../../../components/Loader";
import GlobalAppContext from "../../../utils/GlobalAppContext";
import { useMediaQuery } from "../../../explore/fresh-releases/utils";

export type UserGenreActivityProps = {
  range: UserStatsAPIRange;
  user?: ListenBrainzUser;
};

type ProcessedTimeframeData = {
  timeOfDay: string;
  timeRange: string;
  genres: Array<{
    name: string;
    listen_count: number;
  }>;
};

// Define the chart data item type for better type safety
type ChartDataItem = {
  id: string;
  label: string;
  displayName: string;
  actualValue: number;
  value: number;
  color: string;
  timeRange: string;
  hour: number;
};

const TIME_PERIODS = [
  { timeRange: "Night", timeOfDay: "12AM-6AM", hour: 3, from: 0, to: 5 },
  { timeRange: "Morning", timeOfDay: "6AM-12PM", hour: 9, from: 6, to: 11 },
  { timeRange: "Afternoon", timeOfDay: "12PM-6PM", hour: 15, from: 12, to: 17 },
  { timeRange: "Evening", timeOfDay: "6PM-12AM", hour: 21, from: 18, to: 23 },
];

const getRoundedTimezoneOffset = (): number => {
  const offsetMinutes = -new Date().getTimezoneOffset();
  const offsetHours = offsetMinutes / 60;
  return offsetMinutes % 60 <= 30
    ? Math.floor(offsetHours)
    : Math.ceil(offsetHours);
};

const convertUTCToLocalHour = (
  utcHour: number,
  timezoneOffset: number
): number => {
  return (utcHour + timezoneOffset + 24) % 24;
};

const getTimePeriod = (hour: number) => {
  return (
    TIME_PERIODS.find((p) => hour >= p.from && hour <= p.to) ?? TIME_PERIODS[0]
  );
};

const getTop5GenresWithTies = (
  genres: Array<{ name: string; listen_count: number }>
) => {
  const sorted = [...genres].sort((a, b) => b.listen_count - a.listen_count);
  const topGenres = sorted.slice(0, 5);
  const fifthCount = topGenres.at(-1)?.listen_count ?? 0;
  return sorted.filter((g) => g.listen_count >= fifthCount);
};

const groupDataByTimePeriod = (
  data: GenreHourData[],
  timezoneOffset: number
): ProcessedTimeframeData[] => {
  const grouped: Record<string, Record<string, number>> = {};
  TIME_PERIODS.forEach((p) => {
    grouped[p.timeRange] = {};
  });

  data.forEach((item) => {
    const localHour = convertUTCToLocalHour(item.hour, timezoneOffset);
    const period = getTimePeriod(localHour);
    grouped[period.timeRange][item.genre] =
      (grouped[period.timeRange][item.genre] || 0) + item.listen_count;
  });

  return TIME_PERIODS.map(({ timeRange, timeOfDay }) => {
    const genres = Object.entries(grouped[timeRange] || {})
      .map(([name, listen_count]) => ({ name, listen_count }))
      .sort((a, b) => b.listen_count - a.listen_count);

    const finalGenres =
      genres.length > 0
        ? getTop5GenresWithTies(genres)
        : [{ name: "No Listens", listen_count: 0 }];

    return { timeOfDay, timeRange, genres: finalGenres };
  });
};

function CustomTooltip({ datum }: { datum: any }) {
  return (
    <div className="custom-tooltip-genre-stats">
      <strong>{datum.data.displayName}</strong>
      <br />
      {datum.data.actualValue} plays
      <br />
      {datum.data.timeRange}
    </div>
  );
}

function TimeMarker({
  position,
  label,
  isMobile,
}: {
  position: React.CSSProperties;
  label: string;
  isMobile: boolean;
}) {
  return (
    <div
      style={{
        position: "absolute",
        fontWeight: "bold",
        fontSize: isMobile ? 12 : 16,
        zIndex: 10,
        color: "#666",
        ...position,
      }}
    >
      {label}
    </div>
  );
}

export default function UserGenreActivity({
  user,
  range,
}: UserGenreActivityProps) {
  const { APIService } = React.useContext(GlobalAppContext);
  const colorScale = scaleSequential(interpolateRainbow).domain([0, 24]);
  const timezoneOffset = React.useMemo(() => getRoundedTimezoneOffset(), []);

  // Detect mobile screen size
  const isMobile = useMediaQuery("(max-width: 767px)");

  const { data: loaderData, isLoading: loading } = useQuery({
    queryKey: ["userGenreActivity", user?.name, range],
    queryFn: async () => {
      try {
        if (!user?.name) throw new Error("User name is required");
        const queryData = await APIService.getUserGenreActivity(
          user.name,
          range
        );
        return { data: queryData, hasError: false, errorMessage: "" };
      } catch (error) {
        return {
          data: {
            payload: {
              genre_activity: [],
              from_ts: 0,
              to_ts: 0,
              last_updated: 0,
              user_id: user?.name ?? "",
              range,
            },
          },
          hasError: true,
          errorMessage: error?.message ?? "Failed to load genre activity",
        };
      }
    },
    enabled: !!user?.name,
  });

  const {
    data: rawData = {
      payload: {
        genre_activity: [],
        from_ts: 0,
        to_ts: 0,
        last_updated: 0,
        user_id: user?.name ?? "",
        range,
      },
    },
    hasError = false,
    errorMessage = "",
  } = loaderData || {};

  const chartData = React.useMemo(() => {
    const { payload } = rawData as UserGenreActivityResponse;
    const genre_activity: GenreHourData[] = payload?.genre_activity ?? [];
    if (!genre_activity.length) return [];
    const groupedData = groupDataByTimePeriod(genre_activity, timezoneOffset);

    return groupedData.flatMap((timeframe) => {
      // Calculate the total number of listens for all genres in this time period.
      // This is used to compute percentage shares for each genre in the pie chart.
      const total = timeframe.genres.reduce(
        (acc, genre) => acc + genre.listen_count,
        0
      );

      // Get the representative base hour for this time period (e.g., 3AM for "Night").
      // This is used to map genre slices to specific positions and colors on the circular timeline.
      const baseHour =
        TIME_PERIODS.find((p) => p.timeRange === timeframe.timeRange)?.hour ??
        0;

      return timeframe.genres.map((genre, index) => {
        const hourVariation = baseHour + ((index * 0.5) % 6);

        // Calculate the percentage value for the pie chart slice.
        // - If the genre has 0 listens, use a neutral gray color and a value of 100
        //   so that it still renders visibly in the pie chart.
        // - Otherwise, calculate the percentage of listens and use a time-based color.

        const value =
          genre.listen_count === 0 ? 100 : (genre.listen_count / total) * 100;
        const color =
          genre.listen_count === 0 ? "#f7f7f7" : colorScale(hourVariation);

        return {
          id: `${genre.name}-${timeframe.timeOfDay}`,
          label: `${genre.name}-${timeframe.timeOfDay}`,
          displayName: genre.name,
          actualValue: genre.listen_count,
          value,
          color,
          timeRange: timeframe.timeRange,
          hour: hourVariation,
        };
      });
    });
  }, [colorScale, rawData, timezoneOffset]);

  // Responsive time markers - all four markers with mobile-optimized positioning
  const getTimeMarkersConfig = () => {
    const margin = isMobile ? 40 : 80;

    return [
      {
        position: {
          top: `calc(50% - ${margin}px)`,
          left: "50%",
          transform: "translateX(-50%)",
        },
        label: "12AM",
      },
      {
        position: {
          top: "50%",
          right: `calc(50% - ${margin}px)`,
          transform: "translateY(-50%)",
        },
        label: "6AM",
      },
      {
        position: {
          bottom: `calc(50% - ${margin}px)`,
          left: "50%",
          transform: "translateX(-50%)",
        },
        label: "12PM",
      },
      {
        position: {
          top: "50%",
          left: `calc(50% - ${margin}px)`,
          transform: "translateY(-50%)",
        },
        label: "6PM",
      },
    ];
  };

  // Responsive chart dimensions and margins
  const getChartConfig = () => {
    if (isMobile) {
      return {
        height: 400,
        margin: { top: 50, right: 40, bottom: 50, left: 40 },
        innerRadius: 0.3,
        arcLabelsSkipAngle: 15,
      };
    }
    return {
      height: 600,
      margin: { top: 75, right: 80, bottom: 75, left: 80 },
      innerRadius: 0.4,
      arcLabelsSkipAngle: 10,
    };
  };

  const chartConfig = getChartConfig();
  const timeMarkersConfig = getTimeMarkersConfig();

  return (
    <Card className="user-stats-card" data-testid="user-genre-activity">
      <div className="row">
        <div className="col-xs-10">
          <h3 className="capitalize-bold">Genre Activity</h3>
        </div>
      </div>
      <Loader isLoading={loading}>
        {hasError ? (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              minHeight: "inherit",
            }}
          >
            <span style={{ fontSize: isMobile ? 18 : 24 }}>
              <FontAwesomeIcon icon={faExclamationCircle} /> {errorMessage}
            </span>
          </div>
        ) : (
          <div className="row">
            <div className="col-xs-12">
              <div
                style={{
                  position: "relative",
                  height: `${chartConfig.height}px`,
                  width: "100%",
                  margin: "0 auto",
                  overflow: "hidden",
                }}
              >
                {timeMarkersConfig.map((marker, index) => (
                  <TimeMarker
                    key={marker.label}
                    position={marker.position}
                    label={marker.label}
                    isMobile={isMobile}
                  />
                ))}
                <ResponsivePie
                  data={chartData}
                  margin={chartConfig.margin}
                  innerRadius={chartConfig.innerRadius}
                  padAngle={0.7}
                  activeOuterRadiusOffset={isMobile ? 4 : 8}
                  cornerRadius={isMobile ? 6 : 10}
                  colors={(d) => d.data.color}
                  arcLabel={(d) => `${d.data.actualValue}`}
                  arcLinkLabel={(d) => d.data.displayName}
                  arcLabelsSkipAngle={chartConfig.arcLabelsSkipAngle}
                  arcLabelsTextColor="#333333"
                  arcLinkLabelsSkipAngle={isMobile ? 20 : 10}
                  arcLinkLabelsTextColor="#333333"
                  arcLinkLabelsThickness={isMobile ? 1 : 2}
                  arcLinkLabelsOffset={isMobile ? -5 : 0}
                  tooltip={CustomTooltip}
                  animate
                  motionConfig="gentle"
                  legends={[]}
                />
              </div>
            </div>
          </div>
        )}
      </Loader>
    </Card>
  );
}
