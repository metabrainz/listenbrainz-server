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

export type GenreTimeframeData = {
  timeOfDay: string;
  timeRange: string;
  genres: Array<{
    name: string;
    listen_count: number;
  }>;
};

export type UserGenreDayActivityResponse = {
  result: GenreTimeframeData[];
};

// Define a color mapping for genres
const genreColors: Record<string, string> = {
  Pop: "#f47560",
  Rock: "#61cdbb",
  Jazz: "#97e3d5",
  HipHop: "#e8c1a0",
  Classical: "#f1e15b",
  Electronic: "#82ca9d",
  Metal: "#8884d8",
  Folk: "#a4de6c",
  Country: "#d0ed57",
  RB: "#ffc658",
  Indie: "#ff8042",
  Alternative: "#83a6ed",
};

// Get color for a genre, with fallback for unknown genres
const getGenreColor = (genre: string): string => {
  return genreColors[genre] || `hsl(${Math.random() * 360}, 70%, 60%)`;
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

  // Prepare data with correct percentages for pie sizing
  const processData = (data?: UserGenreDayActivityResponse) => {
    if (!data || !data.result || data.result.length === 0) {
      return [];
    }

    return data.result.flatMap((timeframe) => {
      const total = timeframe.genres.reduce(
        (acc, genre) => acc + genre.listen_count,
        0
      );
      return timeframe.genres.map((genre) => ({
        id: `${genre.name}-${timeframe.timeOfDay}`,
        label: `${genre.name}-${timeframe.timeOfDay}`,
        displayName: genre.name,
        actualValue: genre.listen_count,
        value: (genre.listen_count / total) * 100, // Percentage for pie sizing
        color: getGenreColor(genre.name),
        timeframe: timeframe.timeOfDay,
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
          <h3 className="capitalize-bold">Genre Activity by Time of Day</h3>
        </div>
        <div className="col-xs-2 text-right">
          <h4 style={{ marginTop: 20 }}>
            <a href="#genre-day-activity">
              <FontAwesomeIcon
                icon={faLink as IconProp}
                size="sm"
                color={COLOR_BLACK}
                style={{ marginRight: 20 }}
              />
            </a>
          </h4>
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
