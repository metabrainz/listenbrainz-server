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

const TIME_PERIODS = {
  Night: { timeOfDay: "12AM-6AM", hour: 3 },
  Morning: { timeOfDay: "6AM-12PM", hour: 9 },
  Afternoon: { timeOfDay: "12PM-6PM", hour: 15 },
  Evening: { timeOfDay: "6PM-12AM", hour: 21 },
};

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

const groupDataByTimePeriod = (
  data: GenreHourData[]
): ProcessedTimeframeData[] => {
  const grouped: Record<string, Record<string, number>> = {};

  // Initialize time periods
  Object.keys(TIME_PERIODS).forEach((period) => {
    grouped[period] = {};
  });

  // Group data by time period and genre
  data.forEach((item) => {
    const { timeRange } = getTimePeriod(item.hour);
    const { genre } = item;

    grouped[timeRange][genre] =
      (grouped[timeRange][genre] || 0) + item.listen_count;
  });

  // Convert to expected format
  return Object.entries(grouped).map(([timeRange, genres]) => {
    const allGenres = Object.entries(genres)
      .map(([name, listen_count]) => ({ name, listen_count }))
      .sort((a, b) => b.listen_count - a.listen_count);

    // Ensure at least one entry exists
    const finalGenres =
      allGenres.length > 0
        ? getTop5GenresWithTies(allGenres)
        : [{ name: "No Listens", listen_count: 0 }];

    return {
      timeOfDay: TIME_PERIODS[timeRange as keyof typeof TIME_PERIODS].timeOfDay,
      timeRange,
      genres: finalGenres,
    };
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
      {datum.data.timeframe}
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
    data: rawData = { result: [] },
    hasError = false,
    errorMessage = "",
  } = loaderData || {};

  const processData = React.useCallback(
    (data?: UserGenreDayActivityResponse) => {
      if (!data?.result?.length) return [];

      const groupedData = groupDataByTimePeriod(data.result);

      return groupedData.flatMap((timeframe) => {
        const total = timeframe.genres.reduce(
          (acc, genre) => acc + genre.listen_count,
          0
        );
        const baseHour =
          TIME_PERIODS[timeframe.timeRange as keyof typeof TIME_PERIODS].hour;

        return timeframe.genres.map((genre, index) => {
          const hourVariation = baseHour + ((index * 0.5) % 6);
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
            timeframe: timeframe.timeRange,
            timeRange: timeframe.timeRange,
            hour: hourVariation,
          };
        });
      });
    },
    [colorScale]
  );

  const chartData = React.useMemo(() => processData(rawData), [
    rawData,
    processData,
  ]);

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
                    key={index}
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
