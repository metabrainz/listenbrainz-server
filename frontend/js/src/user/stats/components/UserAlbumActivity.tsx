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

// Define CustomTooltip outside of the main component
function CustomTooltip({
  id,
  value,
  color,
}: {
  id: string;
  value: number;
  color: string;
}) {
  return (
    <div
      style={{
        padding: "10px",
        background: "white",
        border: `1px solid ${color}`,
        borderRadius: "4px",
        boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
      }}
    >
      <strong>
        {id}: {value}
      </strong>
    </div>
  );
}

export default function ArtistEvolutionStreamGraph(
  props: UserArtistEvolutionProps
) {
  // This will manipulate the original data to inject negative values
  // which can be used to create space below the x-axis
  const processDataWithNegatives = (data: StreamDataItem[]) => {
    if (!data || data.length === 0) return [];

    // Create a deep copy to avoid mutating the original data
    return data.map((dayData) => {
      const result = { ...dayData };

      // Add a negative value field that will create space below the axis
      // This is a visual trick to make the chart extend below the x-axis
      result._negative_space = -150; // Adjustable value to control space below

      return result;
    });
  };

  const { APIService } = React.useContext(GlobalAppContext);

  // Props
  const { user, range } = props;

  // API data fetching
  const { data: loaderData, isLoading: loading } = useQuery({
    queryKey: ["ArtistEvolution", user?.name, range],
    queryFn: async () => {
      try {
        const queryData = await APIService.getUserAlbumActivity(
          user?.name,
          range
        );
        return { data: queryData, hasError: false, errorMessage: "" };
      } catch (error) {
        return {
          data: { result: [] },
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

  const [chartData, setChartData] = React.useState<StreamDataItem[]>([]);
  const [keys, setKeys] = React.useState<string[]>([]);
  const [maxValue, setMaxValue] = React.useState<number>(0);

  React.useEffect(() => {
    if (rawData?.result && rawData.result.length > 0) {
      // Process the data and exclude metadata fields
      const processedData = rawData.result.map((item: any, index: number) => {
        // Create a new object without the metadata field
        const { release_group_mbid, day, ...artistData } = item;

        // Add numeric index for proper x-axis labeling
        return {
          ...artistData,
          index, // Use numeric index instead of day
        };
      });

      // Extract all unique artist keys across all days
      const allArtistKeys = new Set<string>();
      let dayMax = 0;

      processedData.forEach((dayData: any) => {
        let dailyTotal = 0;

        Object.keys(dayData).forEach((key) => {
          if (key !== "index") {
            allArtistKeys.add(key);
            dailyTotal += Number(dayData[key]) || 0;
          }
        });

        if (dailyTotal > dayMax) {
          dayMax = dailyTotal;
        }
      });

      setMaxValue(dayMax);

      // Sort keys to match the order in the second image
      const preferredKeyOrder = [
        "Jacques",
        "Paul",
        "René",
        "Marcel",
        "Josiane",
        "Raoul",
      ];
      const sortedKeys = [...preferredKeyOrder].filter((key) =>
        allArtistKeys.has(key)
      );

      // Add any missing keys from the data
      Array.from(allArtistKeys).forEach((key) => {
        if (!sortedKeys.includes(key) && key !== "_negative_space") {
          sortedKeys.push(key);
        }
      });

      // Add the negative space key at the bottom of the stack
      setKeys(sortedKeys);

      // Apply the negative space transformation to create room below x-axis
      const dataWithNegatives = processDataWithNegatives(processedData);
      setChartData(dataWithNegatives);
    }
  }, [rawData]);

  // Define the tooltip function

  return (
    <Card className="user-stats-card" data-testid="artist-evolution">
      <div className="row">
        <div className="col-xs-10">
          <h3 className="capitalize-bold">Artist Evolution</h3>
        </div>
        <div className="col-xs-2 text-right">
          <h4 style={{ marginTop: 20 }}>
            <a href="#artist-evolution">
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
        ) : chartData.length === 0 ? (
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
                style={{
                  width: "100%",
                  height: "600px",
                }}
              >
                <ResponsiveStream
                  data={chartData}
                  keys={keys}
                  margin={{ top: 20, right: 100, bottom: 60, left: 60 }}
                  axisBottom={{
                    format: (index) => {
                      const days = [
                        "Monday",
                        "Tuesday",
                        "Wednesday",
                        "Thursday",
                        "Friday",
                        "Saturday",
                        "Sunday",
                      ];
                      return days[index % 7];
                    },
                    tickSize: 5,
                    tickPadding: 5,
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
                          fontSize: 12,
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
                  defs={[
                    // Create a translucent fill pattern for the negative space
                    {
                      id: "negativeSpace",
                      type: "patternLines",
                      background: "transparent",
                      color: "transparent",
                      rotation: 0,
                      lineWidth: 0,
                      spacing: 0,
                    },
                  ]}
                  fill={[
                    // Apply the transparent pattern to the negative space
                    {
                      match: { id: "_negative_space" },
                      id: "negativeSpace",
                    },
                  ]}
                  legends={[
                    {
                      anchor: "right",
                      direction: "column",
                      translateX: 100,
                      itemWidth: 80,
                      itemHeight: 20,
                      itemTextColor: "#333333",
                      symbolSize: 12,
                      symbolShape: "circle",
                      effects: [
                        {
                          on: "hover",
                          style: {
                            itemTextColor: "#000000",
                          },
                        },
                      ],
                      // Don't show the negative space in the legend
                      data: keys
                        .filter((key) => key !== "_negative_space")
                        .map((key) => ({
                          id: key,
                          label: key,
                          color: "inherit", // This will match the color used in the stream
                        })),
                    },
                  ]}
                />
              </div>
            </div>
          </div>
        )}
      </Loader>
    </Card>
  );
}
