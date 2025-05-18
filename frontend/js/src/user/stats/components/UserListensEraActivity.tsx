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
import { COLOR_BLACK } from "../../../utils/constants";
import GlobalAppContext from "../../../utils/GlobalAppContext";

// Constants
const BAR_WIDTH = 30;
const PADDING = 0.3;
const MIN_CHART_WIDTH = 800;

export type UserListensEraActivityProps = {
  range: UserStatsAPIRange;
  user?: ListenBrainzUser;
};

export default function UserListensEraActivity({
  user,
  range,
}: UserListensEraActivityProps) {
  const { APIService } = React.useContext(GlobalAppContext);
  const scrollContainerRef = useRef(null);
  const [containerWidth, setContainerWidth] = useState(0);

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

  useEffect(() => {
    const adjustedWidth = BAR_WIDTH / (1 - PADDING);
    const chartData = rawData?.result || [];
    const totalWidth = Math.max(
      MIN_CHART_WIDTH,
      chartData.length * adjustedWidth
    );
    setContainerWidth(totalWidth);
  }, [rawData?.result]);

  const chartData = rawData?.result || [];
  const firstYear = chartData.length > 0 ? parseInt(chartData[0]?.year) : 0;

  const tickFormatter = (tick: string) => {
    const year = parseInt(tick);
    return year === firstYear || year % 5 === 0 ? tick : "";
  };

  return (
    <Card className="user-stats-card" data-testid="yearly-listening-activity">
      <div className="row">
        <div className="col-xs-10">
          <h3 className="capitalize-bold">Era Activity</h3>
        </div>
        <div className="col-xs-2 text-right">
          <h4 style={{ marginTop: 20 }}>
            <a href="#era-activity">
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
      <Loader isLoading={isLoading}>
        {hasError ? (
          <div className="flex-center" style={{ minHeight: "inherit" }}>
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
                  overflowX: "auto",
                  overflowY: "hidden",
                  fontSize: "11px",
                }}
              >
                <div style={{ width: `${containerWidth}px`, height: "100%" }}>
                  <ResponsiveBar
                    data={chartData}
                    indexBy="year"
                    keys={["count"]}
                    axisBottom={{
                      format: tickFormatter,
                      legend: "Year",
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
                    tooltip={({ indexValue, value }) => (
                      <BasicTooltip
                        id={String(indexValue)}
                        value={`${value} ${
                          Number(value) === 1 ? "listen" : "listens"
                        }`}
                      />
                    )}
                    margin={{ left: 60, bottom: 60, top: 30, right: 20 }}
                    enableGridY
                    gridYValues={5}
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
