import * as React from "react";
import { useRef, useState, useEffect, useMemo, useCallback } from "react";
import { ResponsiveBar } from "@nivo/bar";
import { useMediaQuery } from "react-responsive";
import { BasicTooltip } from "@nivo/tooltip";
import {
  faExclamationCircle,
  faSearchPlus,
  faSearchMinus,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { useQuery } from "@tanstack/react-query";
import Card from "../../../components/Card";
import Loader from "../../../components/Loader";
import { COLOR_LB_ORANGE, COLOR_LB_GREEN } from "../../../utils/constants";
import GlobalAppContext from "../../../utils/GlobalAppContext";

// Constants
const MIN_BAR_WIDTH_PX = 60;
const BAR_PADDING_RATIO = 0.3;

export type UserEraActivityProps = {
  range: UserStatsAPIRange;
  user?: ListenBrainzUser;
};

// Move the tooltip component outside of the render function
function CustomTooltip({
  indexValue,
  value,
  formatLabel,
}: {
  indexValue: string | number;
  value: number;
  formatLabel: (decade: number) => string;
}) {
  return (
    <BasicTooltip
      id={formatLabel(Number(indexValue))}
      value={`${value} ${Number(value) === 1 ? "listen" : "listens"}`}
    />
  );
}

const getDecade = (year: number): number => {
  return Math.floor(year / 10) * 10;
};

const getCount = (item: {
  year: number;
  listen_count?: number;
  count?: number;
}): number => {
  return item.listen_count || item.count || 0;
};

const processDataIntoDecades = (
  data: Array<{ year: number; listen_count?: number; count?: number }>
) => {
  if (!data || data.length === 0) return [];

  const decadeMap = new Map<number, number>();

  data.forEach((item) => {
    const decade = getDecade(item.year);
    const currentCount = decadeMap.get(decade) || 0;
    const itemCount = getCount(item);
    decadeMap.set(decade, currentCount + itemCount);
  });

  const years = data.map((item) => item.year);
  const minYear = Math.min(...years);
  const maxYear = Math.max(...years);

  const minDecade = getDecade(minYear);
  const maxDecade = getDecade(maxYear);

  const result = [];
  for (let decade = minDecade; decade <= maxDecade; decade += 10) {
    result.push({
      decade,
      listen_count: decadeMap.get(decade) || 0,
    });
  }

  return result;
};

const getExpandedDecadeData = (
  data: Array<{ year: number; listen_count?: number; count?: number }>,
  selectedDecade: number
) => {
  const decadeEnd = selectedDecade + 9;

  const yearMap = new Map<number, number>();
  data.forEach((item) => {
    if (item.year >= selectedDecade && item.year <= decadeEnd) {
      const itemCount = getCount(item);
      yearMap.set(item.year, itemCount);
    }
  });

  const result = [];
  for (let year = selectedDecade; year <= decadeEnd; year += 1) {
    result.push({
      decade: year,
      listen_count: yearMap.get(year) || 0,
    });
  }

  return result;
};

export default function UserEraActivity({ user, range }: UserEraActivityProps) {
  const { APIService } = React.useContext(GlobalAppContext);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(0);
  const [selectedDecade, setSelectedDecade] = useState<number | null>(null);

  const { data: loaderData, isLoading } = useQuery({
    queryKey: ["userEraActivity", user?.name, range],
    queryFn: async () => {
      try {
        const queryData = await APIService.getUserEraActivity(
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
  const chartData = useMemo(() => {
    const dataResult = rawData?.result || [];
    return selectedDecade
      ? getExpandedDecadeData(dataResult, selectedDecade)
      : processDataIntoDecades(dataResult);
  }, [rawData?.result, selectedDecade]);

  const selectedDecadeTotal = useMemo(() => {
    if (!selectedDecade || !rawData?.result) return 0;
    const dataResult = rawData.result;
    const decadeEnd = selectedDecade + 9;

    return dataResult
      .filter((item) => item.year >= selectedDecade && item.year <= decadeEnd)
      .reduce((total, item) => total + getCount(item), 0);
  }, [selectedDecade, rawData?.result]);

  const firstDecade = useMemo(() => {
    const dataResult = rawData?.result || [];
    if (dataResult.length === 0) return null;
    const years = dataResult.map((item) => item.year);
    const minYear = Math.min(...years);
    return getDecade(minYear);
  }, [rawData?.result]);

  useEffect(() => {
    const containerElement = scrollContainerRef.current;
    if (!containerElement) return undefined;

    const updateWidth = () => {
      const parentWidth =
        containerElement.parentElement?.offsetWidth || window.innerWidth;
      const availableWidth = parentWidth - 40;

      const minRequiredWidth =
        chartData.length * (MIN_BAR_WIDTH_PX / (1 - BAR_PADDING_RATIO));
      const finalWidth = Math.max(availableWidth, minRequiredWidth);
      setContainerWidth(finalWidth);
    };

    updateWidth();

    window.addEventListener("resize", updateWidth);
    return () => {
      window.removeEventListener("resize", updateWidth);
    };
  }, [chartData.length]);

  const handleBarClick = useCallback(
    (data: {
      id: string | number;
      value: number | null;
      indexValue: string | number;
      data: {
        decade: number;
        listen_count: number;
      };
      color: string;
    }) => {
      const clickedDecade = data.data.decade;
      if (selectedDecade) {
        setSelectedDecade(null);
        return;
      }

      // Only allow expansion for decades (multiples of 10)
      if (clickedDecade % 10 === 0 && clickedDecade !== clickedDecade % 10) {
        setSelectedDecade(clickedDecade);
      }
    },
    [selectedDecade]
  );

  const handleZoomIn = useCallback(() => {
    if (firstDecade && !selectedDecade) {
      setSelectedDecade(firstDecade);
    }
  }, [firstDecade, selectedDecade]);

  const handleZoomOut = useCallback(() => {
    setSelectedDecade(null);
  }, []);

  // Format function for display
  const formatDecadeLabel = useCallback(
    (decade: number): string => {
      return selectedDecade ? decade.toString() : `${decade}s`;
    },
    [selectedDecade]
  );

  // Memoize tooltip component to prevent recreation on every render
  const renderTooltip = useCallback(
    (props: any) => (
      <CustomTooltip
        indexValue={props.indexValue}
        value={Number(props.value)}
        formatLabel={formatDecadeLabel}
      />
    ),
    [formatDecadeLabel]
  );

  return (
    <Card className="user-stats-card" data-testid="user-era-activity">
      <div className="d-flex align-items-start justify-content-between mb-3 mt-3">
        <div className="flex-grow-1 min-w-0">
          <h3 style={{ margin: 0, marginBottom: "5px" }}>
            <span className="capitalize-bold">Era Activity</span>
          </h3>
          <div className="small text-secondary lh-sm">
            {selectedDecade && (
              <span>
                {selectedDecade}s - {selectedDecadeTotal.toLocaleString()}{" "}
                {selectedDecadeTotal === 1 ? "listen" : "listens"} (Click any
                bar to zoom out)
              </span>
            )}
            {!selectedDecade && (
              <span>Click any bar to zoom in and see individual years</span>
            )}
          </div>
        </div>
        {!isLoading && !hasError && chartData.length > 0 && (
          <div className="d-flex gap-1 ms-3 flex-shrink-0">
            <button
              type="button"
              onClick={handleZoomIn}
              disabled={selectedDecade !== null || firstDecade === null}
              className="lb-icon-btn"
              title="Zoom in to first decade"
            >
              <FontAwesomeIcon icon={faSearchPlus as IconProp} />
            </button>
            <button
              type="button"
              onClick={handleZoomOut}
              disabled={selectedDecade === null}
              className="lb-icon-btn"
              title="Zoom out to decades view"
            >
              <FontAwesomeIcon icon={faSearchMinus as IconProp} />
            </button>
          </div>
        )}
      </div>
      <Loader isLoading={isLoading}>
        {hasError ? (
          <div className="d-flex gap-1 ms-3 flex-shrink-0">
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
                      format: formatDecadeLabel,
                    }}
                    axisLeft={{
                      legend: "Number of listens",
                      legendPosition: "middle",
                      legendOffset: -40,
                      format: ".2~s",
                    }}
                    minValue={0}
                    padding={BAR_PADDING_RATIO}
                    enableLabel={false}
                    tooltip={renderTooltip}
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
