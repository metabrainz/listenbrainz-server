import React from "react";
import { PointTooltipProps, ResponsiveLine } from "@nivo/line";
import { COLOR_LB_ORANGE } from "../../utils/constants";

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
        <div
          style={{
            fontSize: "12px",
            fontWeight: "bold",
            marginBottom: "4px",
          }}
        >
          {point.data.x.toString()}
        </div>
        <div style={{ display: "flex", alignItems: "center" }}>
          <div
            style={{
              width: "12px",
              height: "12px",
              backgroundColor: point.serieColor,
              marginRight: "8px",
            }}
          />
          <span>
            Users: <strong>{point.data.y.toString()}</strong>
          </span>
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
          };
        }) ?? [],
    },
  ];

  return (
    <div style={{ height: "400px", width: "100%" }}>
      <ResponsiveLine
        data={chartData}
        margin={{ top: 50, right: 30, bottom: 50, left: 60 }}
        xScale={{ type: "point" }}
        xFormat="time:%Y"
        yScale={{
          type: "linear",
          min: 0,
          max: "auto",
        }}
        axisBottom={{
          legend: "Time Period",
          legendOffset: 45,
          legendPosition: "middle",
          tickRotation: -45,
          tickValues: "every 1 year",
        }}
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
