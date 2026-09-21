import React from "react";
import {
  CustomLayerProps,
  ResponsiveLine,
  SliceTooltipProps,
} from "@nivo/line";
import { scaleLinear } from "d3-scale";
import { COLOR_LB_BLUE, COLOR_LB_ORANGE } from "../../utils/constants";
import { useMediaQuery } from "../../explore/fresh-releases/utils";

export type UserEvolutionData = {
  period: string;
  new_users: number;
  total_users: number;
};

export type ListenEvolutionData = {
  period: string;
  new_listens: number;
  total_listens: number;
};

type Count = { period: string; total: number; newCount: number };

// Carry cumulative totals through internal gaps, but never extend a series beyond
// its known date range (the two caches may have been refreshed at different times).
export function alignMonths(data: Count[], months: string[]) {
  const byMonth = new Map(data.map((row) => [row.period.slice(0, 7), row]));
  const available = Array.from(byMonth.keys()).sort();
  let total = 0;
  return months.map((month) => {
    if (
      !available.length ||
      month < available[0] ||
      month > available[available.length - 1]
    ) {
      return null;
    }
    const row = byMonth.get(month);
    if (row) total = row.total;
    return { total, newCount: row?.newCount ?? 0 };
  });
}

const monthLabel = (month: string) =>
  new Date(`${month}-01T00:00:00Z`).toLocaleDateString(undefined, {
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
const compactNumber = new Intl.NumberFormat(undefined, {
  notation: "compact",
  maximumFractionDigits: 1,
});

function GrowthTooltip({ slice }: SliceTooltipProps) {
  return (
    <div
      style={{
        background: "white",
        padding: "9px 12px",
        border: "1px solid #ccc",
        borderRadius: 4,
      }}
    >
      <strong>{monthLabel(String(slice.points[0].data.x))}</strong>
      {slice.points.map((point) => {
        const data = point.data as typeof point.data & {
          total: number;
          newCount: number;
          monthlyLabel: string;
        };
        return (
          <div key={point.serieId} style={{ color: point.serieColor }}>
            {point.serieId}: <strong>{data.total.toLocaleString()}</strong>
            <div>
              {data.monthlyLabel}: {data.newCount.toLocaleString()}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function CountEvolutionChart({
  userCountEvolution,
  listenCountEvolution,
}: {
  userCountEvolution: UserEvolutionData[];
  listenCountEvolution: ListenEvolutionData[];
}) {
  const isMobile = useMediaQuery("(max-width: 767px)");
  const available = [...userCountEvolution, ...listenCountEvolution]
    .map(({ period }) => period.slice(0, 7))
    .sort();
  if (!available.length) return <div>No data available</div>;

  const months: string[] = [];
  const date = new Date(`${available[0]}-01T00:00:00Z`);
  while (date.toISOString().slice(0, 7) <= available[available.length - 1]) {
    months.push(date.toISOString().slice(0, 7));
    date.setUTCMonth(date.getUTCMonth() + 1);
  }
  const series = [
    {
      id: "Users",
      color: COLOR_LB_ORANGE,
      side: "left",
      monthlyLabel: "New users",
      values: alignMonths(
        userCountEvolution.map(({ period, total_users, new_users }) => ({
          period,
          total: total_users,
          newCount: new_users,
        })),
        months
      ),
    },
    {
      id: "Listens",
      color: COLOR_LB_BLUE,
      side: "right",
      monthlyLabel: "Listens submitted",
      values: alignMonths(
        listenCountEvolution.map(({ period, total_listens, new_listens }) => ({
          period,
          total: total_listens,
          newCount: new_listens,
        })),
        months
      ),
    },
  ].map((seriesData) => ({
    ...seriesData,
    scale: scaleLinear()
      .domain([0, Math.max(1, ...seriesData.values.map((v) => v?.total ?? 0))])
      .nice(5),
  }));

  // Nivo has one plotting scale. Map each series into [0, 1], and draw its
  // independent axis using the very same conversion. Tooltips retain raw counts.
  const axes = ({ innerWidth, innerHeight }: CustomLayerProps) => (
    <g>
      {series
        .filter((s) => s.values.some((v) => v !== null))
        .map((s) => {
          const direction = s.side === "left" ? -1 : 1;
          return (
            <g
              key={s.id}
              transform={`translate(${direction < 0 ? 0 : innerWidth},0)`}
              fill={s.color}
              data-testid={`axis-${s.side}`}
            >
              <line
                y2={innerHeight}
                stroke={s.color}
                data-testid={`axis-line-${s.side}`}
              />
              {s.scale.ticks(5).map((value) => (
                <g
                  key={value}
                  transform={`translate(0,${
                    innerHeight * (1 - s.scale(value))
                  })`}
                >
                  <line x2={direction * 5} stroke={s.color} />
                  <text
                    x={direction * 9}
                    dy="0.32em"
                    textAnchor={direction < 0 ? "end" : "start"}
                    fontSize={11}
                  >
                    {compactNumber.format(value)}
                  </text>
                </g>
              ))}
              <text
                transform={`translate(${direction * (isMobile ? 49 : 61)},${
                  innerHeight / 2
                }) rotate(${direction * 90})`}
                textAnchor="middle"
                fontSize={12}
              >
                {s.id}
              </text>
            </g>
          );
        })}
    </g>
  );

  const tickEvery = Math.max(1, Math.ceil(months.length / (isMobile ? 4 : 10)));
  return (
    <>
      <div className="d-flex gap-3 justify-content-center">
        {series.map((s) => (
          <span key={s.id} style={{ color: s.color }}>
            <strong>━ {s.id}</strong> ({s.side} axis)
            {!s.values.some((v) => v !== null) && " — no data available"}
          </span>
        ))}
      </div>
      <div style={{ height: "400px", width: "100%" }}>
        <ResponsiveLine
          data={series.map((s) => ({
            id: s.id,
            data: months.map((month, i) => ({
              x: month,
              y: s.values[i] === null ? null : s.scale(s.values[i]!.total),
              total: s.values[i]?.total,
              newCount: s.values[i]?.newCount,
              monthlyLabel: s.monthlyLabel,
            })),
          }))}
          colors={series.map((s) => s.color)}
          margin={{
            top: 20,
            right: isMobile ? 65 : 80,
            bottom: 65,
            left: isMobile ? 65 : 80,
          }}
          xScale={{ type: "point" }}
          yScale={{ type: "linear", min: 0, max: 1 }}
          axisLeft={null}
          axisRight={null}
          axisBottom={{
            format: monthLabel,
            tickValues: months.filter((_, i) => i % tickEvery === 0),
            tickRotation: -45,
          }}
          enableGridX={false}
          gridYValues={[0, 0.2, 0.4, 0.6, 0.8, 1]}
          layers={[
            "grid",
            "axes",
            axes,
            "lines",
            "points",
            "crosshair",
            "slices",
          ]}
          pointSize={3}
          curve="monotoneX"
          enableSlices="x"
          sliceTooltip={GrowthTooltip}
        />
      </div>
    </>
  );
}
