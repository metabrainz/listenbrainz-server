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

export type UserGenreDayActivityProps = {
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

// Circular time markers placed around the pie chart to indicate major time labels.
const timeMarkers = [
  {
    position: { top: "5px", left: "50%", transform: "translateX(-50%)" },
    label: "12AM",
  },
  {
    position: { top: "50%", right: "25%", transform: "translateY(-50%)" },
    label: "6AM",
  },
  {
    position: { bottom: "5px", left: "50%", transform: "translateX(-50%)" },
    label: "12PM",
  },
  {
    position: { top: "50%", left: "25%", transform: "translateY(-50%)" },
    label: "6PM",
  },
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
    <div
      style={{
        background: "white",
        padding: "12px",
        border: "1px solid #ccc",
        borderRadius: "4px",
        boxShadow: "0 2px 4px rgba(0,0,0,0.2)",
        textAlign: "center",
        opacity: 0.9,
      }}
    >
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
}: {
  position: React.CSSProperties;
  label: string;
}) {
  return (
    <div
      style={{
        position: "absolute",
        fontWeight: "bold",
        fontSize: 20,
        zIndex: 10,
        ...position,
      }}
    >
      {label}
    </div>
  );
}

export default function UserGenreDayActivity({
  user,
  range,
}: UserGenreDayActivityProps) {
  const { APIService } = React.useContext(GlobalAppContext);
  const colorScale = scaleSequential(interpolateRainbow).domain([0, 24]);
  const timezoneOffset = React.useMemo(() => getRoundedTimezoneOffset(), []);

  const { data: loaderData, isLoading: loading } = useQuery({
    queryKey: ["userGenreDayActivity", user?.name, range],
    queryFn: async () => {
      try {
        // Fix: Handle undefined user name
        if (!user?.name) {
          throw new Error("User name is required");
        }

        const queryData = await APIService.getUserGenreDayActivity(
          user.name,
          range
        );
        return { data: queryData, hasError: false, errorMessage: "" };
      } catch (error) {
        return {
          data: { result: [] } as UserGenreDayActivityResponse,
          hasError: true,
          errorMessage: error.message,
        };
      }
    },
    enabled: !!user?.name, // Only run query if user name exists
  });

  const {
    data: rawData = { result: [] },
    hasError = false,
    errorMessage = "",
  } = loaderData || {};

  const chartData = React.useMemo(() => {
    if (!rawData?.result?.length) return [];
    const groupedData = groupDataByTimePeriod(rawData.result, timezoneOffset);

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

  return (
    <Card className="user-stats-card" data-testid="user-genre-day-activity">
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
            <span style={{ fontSize: 24 }}>
              <FontAwesomeIcon icon={faExclamationCircle} /> {errorMessage}
            </span>
          </div>
        ) : (
          <div className="row">
            <div className="col-xs-12">
              <div
                style={{
                  position: "relative",
                  height: "600px",
                  width: "100%",
                  margin: "0 auto",
                }}
              >
                {timeMarkers.map((marker, index) => (
                  <TimeMarker
                    key={marker.label}
                    position={marker.position}
                    label={marker.label}
                  />
                ))}
                <ResponsivePie
                  data={chartData}
                  margin={{ top: 75, right: 80, bottom: 75, left: 80 }}
                  innerRadius={0.4}
                  padAngle={0.7}
                  activeOuterRadiusOffset={8}
                  cornerRadius={10}
                  colors={(d) => d.data.color}
                  arcLabel={(d) => `${d.data.actualValue}`}
                  arcLinkLabel={(d) => d.data.displayName}
                  arcLabelsSkipAngle={10}
                  arcLabelsTextColor="#333333"
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
