import * as React from "react";
import { useRef, useState, useEffect } from "react";
import { ResponsiveBar } from "@nivo/bar";
import { useMediaQuery } from "react-responsive";
import { BasicTooltip } from "@nivo/tooltip";
import { faExclamationCircle, faLink } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { useQuery } from "@tanstack/react-query";
import Card from "../../../components/Card";
import Loader from "../../../components/Loader";
import { COLOR_LB_ORANGE } from "../../../utils/constants";
import GlobalAppContext from "../../../utils/GlobalAppContext";

// Constants
const MIN_BAR_WIDTH = 60;
const PADDING = 0.3;

export type UserListensEraActivityProps = {
  range: UserStatsAPIRange;
  user?: ListenBrainzUser;
};

// Move the tooltip component outside of the render function
function CustomTooltip({
  indexValue,
  value,
}: {
  indexValue: string | number;
  value: number;
}) {
  return (
    <BasicTooltip
      id={String(indexValue)}
      value={`${value} ${Number(value) === 1 ? "listen" : "listens"}`}
    />
  );
}

const getDecade = (year: number): string => {
  const decade = Math.floor(year / 10) * 10;
  return `${decade}s`;
};

const processDataIntoDecades = (
  data: Array<{ year: number; listen_count?: number; count?: number }>
) => {
  if (!data || data.length === 0) return [];

  const decadeMap = new Map<string, number>();

  data.forEach((item) => {
    const decade = getDecade(item.year);
    const currentCount = decadeMap.get(decade) || 0;
    const itemCount = item.listen_count ?? item.count ?? 0;
    decadeMap.set(decade, currentCount + itemCount);
  });

  const years = data.map((item) => item.year);
  const minYear = Math.min(...years);
  const maxYear = Math.max(...years);

  const minDecade = Math.floor(minYear / 10) * 10;
  const maxDecade = Math.floor(maxYear / 10) * 10;

  const result = [];
  for (let decade = minDecade; decade <= maxDecade; decade += 10) {
    const decadeLabel = `${decade}s`;
    result.push({
      decade: decadeLabel,
      listen_count: decadeMap.get(decadeLabel) || 0,
    });
  }

  return result;
};

const getExpandedDecadeData = (
  data: Array<{ year: number; listen_count?: number; count?: number }>,
  selectedDecade: string
) => {
  const decadeStart = parseInt(selectedDecade.replace("s", ""), 10);
  const decadeEnd = decadeStart + 9;

  const yearMap = new Map<number, number>();
  data.forEach((item) => {
    if (item.year >= decadeStart && item.year <= decadeEnd) {
      const itemCount = item.listen_count ?? item.count ?? 0;
      yearMap.set(item.year, itemCount);
    }
  });

  const result = [];
  for (let year = decadeStart; year <= decadeEnd; year += 1) {
    result.push({
      decade: year.toString(),
      listen_count: yearMap.get(year) || 0,
    });
  }

  return result;
};

export default function UserListensEraActivity({
  user,
  range,
}: UserListensEraActivityProps) {
  const { APIService } = React.useContext(GlobalAppContext);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(0);
  const [selectedDecade, setSelectedDecade] = useState<string | null>(null);

  const { data: loaderData, isLoading } = useQuery({
    queryKey: ["userListensEraActivity", user?.name, range],
    queryFn: async () => {
      try {
        const queryData = await APIService.getUserListensEraActivity(
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

  // Process data based on whether a decade is selected
  const chartData = selectedDecade
    ? getExpandedDecadeData(rawData?.result || [], selectedDecade)
    : processDataIntoDecades(rawData?.result || []);

  useEffect(() => {
    const containerElement = scrollContainerRef.current;
    if (!containerElement) return undefined;

    const updateWidth = () => {
      const parentWidth =
        containerElement.parentElement?.offsetWidth || window.innerWidth;
      const availableWidth = parentWidth - 40;

      const minRequiredWidth =
        chartData.length * (MIN_BAR_WIDTH / (1 - PADDING));
      const finalWidth = Math.max(availableWidth, minRequiredWidth);
      setContainerWidth(finalWidth);
    };

    updateWidth();

    window.addEventListener("resize", updateWidth);
    return () => {
      window.removeEventListener("resize", updateWidth);
    };
  }, [rawData?.result, selectedDecade, chartData.length]);

  const handleBarClick = (data: {
    id: string | number;
    value: number | null;
    indexValue: string | number;
    data: {
      decade: string;
      listen_count: number;
    };
    color: string;
  }) => {
    const clickedDecade = data.data.decade;
    if (selectedDecade) {
      setSelectedDecade(null);
      return;
    }

    if (clickedDecade.endsWith("s")) {
      setSelectedDecade(clickedDecade);
    }
  };

  return (
    <Card className="user-stats-card" data-testid="yearly-listening-activity">
      <div className="row">
        <div className="col-xs-10">
          <h3 className="capitalize-bold">
            Era Activity
            {selectedDecade && (
              <span
                style={{ marginLeft: 10, fontSize: "0.8em", color: "#666" }}
              >
                - {selectedDecade} (click any bar to collapse)
              </span>
            )}
          </h3>
        </div>
      </div>
      <Loader isLoading={isLoading}>
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
                ref={scrollContainerRef}
                className="stats-full-width-graph yearly-listening-activity"
                data-testid="yearly-listening-activity-bar"
                style={{
                  height: "400px",
                  width: "100%",
                  overflowX:
                    containerWidth >
                    (scrollContainerRef.current?.parentElement?.offsetWidth ||
                      0) -
                      40
                      ? "auto"
                      : "hidden",
                  overflowY: "hidden",
                  fontSize: "11px",
                }}
              >
                <div style={{ width: `${containerWidth}px`, height: "100%" }}>
                  <ResponsiveBar
                    data={chartData}
                    indexBy="decade"
                    keys={["listen_count"]}
                    onClick={handleBarClick}
                    axisBottom={{
                      legend: selectedDecade ? "Year" : "Decade",
                      legendPosition: "middle",
                      legendOffset: 40,
                    }}
                    axisLeft={{
                      legend: "Number of listens",
                      legendPosition: "middle",
                      legendOffset: -40,
                      format: ".2~s",
                    }}
                    minValue={0}
                    padding={PADDING}
                    enableLabel={false}
                    tooltip={CustomTooltip}
                    margin={{ left: 60, bottom: 60, top: 30, right: 20 }}
                    enableGridY
                    gridYValues={5}
                    colors={() => COLOR_LB_ORANGE}
                    theme={{
                      grid: {
                        line: {
                          stroke: "#e0e0e0",
                          strokeWidth: 1,
                        },
                      },
                      axis: {
                        ticks: {
                          text: { fontSize: 11 },
                        },
                        legend: {
                          text: {
                            fontSize: 12,
                            fontWeight: "bold",
                          },
                        },
                      },
                    }}
                  />
                </div>
              </div>
            </div>
          </div>
        )}
      </Loader>
    </Card>
  );
}
