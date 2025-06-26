import { ResponsivePie } from "@nivo/pie";
import * as React from "react";
import { faExclamationCircle, faLink } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { useQuery } from "@tanstack/react-query";
import Card from "../../../components/Card";
import Loader from "../../../components/Loader";
import { COLOR_BLACK } from "../../../utils/constants";
import GlobalAppContext from "../../../utils/GlobalAppContext";

export type UserGenreDayActivityProps = {
  range: UserStatsAPIRange;
  user?: ListenBrainzUser;
};

// Updated type for the new API response format
export type GenreHourData = {
  genre: string;
  hour: string;
  listen_count: number;
};

export type UserGenreDayActivityResponse = {
  result: GenreHourData[];
};

// Updated type for processed timeframe data
export type ProcessedTimeframeData = {
  timeOfDay: string;
  timeRange: string;
  genres: Array<{
    name: string;
    listen_count: number;
  }>;
};

// Function to map hour to time period
const getTimePeriod = (
  hour: number
): { timeOfDay: string; timeRange: string } => {
  if (hour >= 0 && hour <= 5)
    return { timeOfDay: "12AM-6AM", timeRange: "Night" };
  if (hour >= 6 && hour <= 11)
    return { timeOfDay: "6AM-12PM", timeRange: "Morning" };
  if (hour >= 12 && hour <= 17)
    return { timeOfDay: "12PM-6PM", timeRange: "Afternoon" };
  return { timeOfDay: "6PM-12AM", timeRange: "Evening" };
};

const getTop5GenresWithTies = (
  genres: Array<{ name: string; listen_count: number }>
) => {
  if (genres.length <= 5) return genres;
  const sorted = [...genres].sort((a, b) => b.listen_count - a.listen_count);
  const fifthHighestCount = sorted[4].listen_count;
  return sorted.filter((genre) => genre.listen_count >= fifthHighestCount);
};

// Function to group hourly data into time periods
const groupDataByTimePeriod = (
  data: GenreHourData[]
): ProcessedTimeframeData[] => {
  const grouped: Record<string, Record<string, number>> = {};

  // Initialize time periods
  const timePeriods = ["Night", "Morning", "Afternoon", "Evening"];
  timePeriods.forEach((period) => {
    grouped[period] = {};
  });

  // Group data by time period and genre
  data.forEach((item) => {
    const hour = parseInt(item.hour, 10);
    const { timeRange } = getTimePeriod(hour);
    const { genre } = item;

    if (!grouped[timeRange][genre]) {
      grouped[timeRange][genre] = 0;
    }
    grouped[timeRange][genre] += item.listen_count;
  });

  // Convert to the expected format
  return Object.entries(grouped)
    .map(([timeRange, genres]) => {
      const timeOfDayMap: Record<string, string> = {
        Night: "12AM-6AM",
        Morning: "6AM-12PM",
        Afternoon: "12PM-6PM",
        Evening: "6PM-12AM",
      };

      const allGenres = Object.entries(genres)
        .filter(([_, count]) => count > 0)
        .map(([name, listen_count]) => ({
          name,
          listen_count,
        }))
        .sort((a, b) => b.listen_count - a.listen_count); // Sort by listen count descending

      const topGenres = getTop5GenresWithTies(allGenres);

      return {
        timeOfDay: timeOfDayMap[timeRange],
        timeRange,
        genres: topGenres,
      };
    })
    .filter((timeframe) => timeframe.genres.length > 0); // Only include time periods with data
};

// Custom tooltip component for pie chart
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
      {datum.data.timeframe}
    </div>
  );
}

export default function UserGenreDayActivity(props: UserGenreDayActivityProps) {
  const { APIService } = React.useContext(GlobalAppContext);

  // Props
  const { user, range } = props;

  const { data: loaderData, isLoading: loading } = useQuery({
    queryKey: ["userGenreDayActivity", user?.name, range],
    queryFn: async () => {
      try {
        const queryData = await APIService.getUserGenreDayActivity(
          user?.name,
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
  });

  const {
    data: rawData = { result: [] } as UserGenreDayActivityResponse,
    hasError = false,
    errorMessage = "",
  } = loaderData || {};

  const processData = (data?: UserGenreDayActivityResponse) => {
    if (!data || !data.result || data.result.length === 0) {
      return [];
    }

    const groupedData = groupDataByTimePeriod(data.result);

    return groupedData.flatMap((timeframe) => {
      const total = timeframe.genres.reduce(
        (acc, genre) => acc + genre.listen_count,
        0
      );
      return timeframe.genres.map((genre) => ({
        id: `${genre.name}-${timeframe.timeOfDay}`,
        label: `${genre.name}-${timeframe.timeOfDay}`,
        displayName: genre.name,
        actualValue: genre.listen_count,
        value: (genre.listen_count / total) * 100,
        color: `hsl(${Math.random() * 360}, 70%, 60%)`,
        timeframe: timeframe.timeRange,
        timeRange: timeframe.timeRange,
      }));
    });
  };

  const [chartData, setChartData] = React.useState<any[]>([]);

  React.useEffect(() => {
    if (rawData && "result" in rawData && rawData.result.length > 0) {
      if (rawData && "result" in rawData) {
        const processedData = processData(rawData);
        setChartData(processedData);
      }
    }
  }, [rawData]);

  // Position markers for clock-like arrangement
  const timeframePositions = {
    top: { label: "12AM", value: "Night" },
    right: { label: "6AM", value: "Morning" },
    bottom: { label: "12PM", value: "Afternoon" },
    left: { label: "6PM", value: "Evening" },
  };

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
              <FontAwesomeIcon icon={faExclamationCircle as IconProp} />{" "}
              {errorMessage}
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
                {/* Time markers positioned around the chart */}
                <div
                  style={{
                    position: "absolute",
                    top: "5px",
                    left: "50%",
                    transform: "translateX(-50%)",
                    fontWeight: "bold",
                    fontSize: 20,
                    zIndex: 10,
                  }}
                >
                  {timeframePositions.top.label}
                </div>
                <div
                  style={{
                    position: "absolute",
                    top: "50%",
                    right: "25%",
                    transform: "translateY(-50%)",
                    fontWeight: "bold",
                    fontSize: 20,
                    zIndex: 10,
                  }}
                >
                  {timeframePositions.right.label}
                </div>
                <div
                  style={{
                    position: "absolute",
                    bottom: "5px",
                    left: "50%",
                    transform: "translateX(-50%)",
                    fontWeight: "bold",
                    fontSize: 20,
                    zIndex: 10,
                  }}
                >
                  {timeframePositions.bottom.label}
                </div>
                <div
                  style={{
                    position: "absolute",
                    top: "50%",
                    left: "25%",
                    transform: "translateY(-50%)",
                    fontWeight: "bold",
                    fontSize: 20,
                    zIndex: 10,
                  }}
                >
                  {timeframePositions.left.label}
                </div>
                {/* Pie Chart */}
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
