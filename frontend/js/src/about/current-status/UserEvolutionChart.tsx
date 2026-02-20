import React from "react";
import { PointTooltipProps, ResponsiveLine } from "@nivo/line";
import { COLOR_LB_ORANGE } from "../../utils/constants";
import { useMediaQuery } from "../../explore/fresh-releases/utils";

export type UserEvolutionData = {
  period: string; // ISO date string
  new_users: number;
  total_users: number;
};

function UserEvolutionChart({
  userCountEvolution,
}: {
  userCountEvolution: UserEvolutionData[];
}) {
  const isMobile = useMediaQuery("(max-width: 767px)");
  const getTooltip = React.useCallback(({ point }: PointTooltipProps) => {
    return (
      <div
        style={{
          background: "white",
          padding: "9px 12px",
          border: "1px solid #ccc",
          borderRadius: "4px",
          color: "#333",
        }}
      >
        <b className="mb-2">{point.data.x.toString()}</b>
        <div>
          New users:{" "}
          {/* @ts-ignore arbitrary properties can be added to the point data */}
          <strong>{Intl.NumberFormat().format(point.data.newUsers)}</strong>
        </div>
        <div>
          Total: <strong>{point.data.yFormatted}</strong>
        </div>
      </div>
    );
  }, []);

  if (!userCountEvolution?.length) {
    return <div>No data available</div>;
  }

  const chartData = [
    {
      id: "Total Users",
      data:
        userCountEvolution?.map(({ period, total_users, new_users }) => {
          const date = new Date(period);
          return {
            x: date.toLocaleDateString(undefined, {
              month: "short",
              year: "2-digit",
            }),
            y: total_users,
            newUsers: new_users,
          };
        }) ?? [],
    },
  ];
  const allLabels = chartData[0].data.map((d) => d.x);
  const everyXMonths = isMobile ? 6 : 3;
  const tickValuesFunction = allLabels.filter((_, i) => i % everyXMonths === 0);

  return (
    <div style={{ height: "400px", width: "100%" }}>
      <ResponsiveLine
        data={chartData}
        margin={{ top: 30, right: 30, bottom: 60, left: 60 }}
        xScale={{ type: "point" }}
        xFormat="time:%Y"
        axisBottom={{
          legend: "Time Period",
          legendOffset: 45,
          legendPosition: "middle",
          tickValues: tickValuesFunction,
          tickRotation: -45,
          tickPadding: 10,
        }}
        yScale={{
          type: "linear",
          min: 0,
          max: "auto",
        }}
        yFormat=".4s"
        enableGridX={false}
        useMesh
        tooltip={getTooltip}
        colors={COLOR_LB_ORANGE}
        pointSize={2}
        enableArea
        curve="monotoneX"
      />
    </div>
  );
}

export default UserEvolutionChart;
