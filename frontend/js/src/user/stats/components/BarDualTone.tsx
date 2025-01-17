import * as React from "react";

import { BarTooltipProps, ResponsiveBar } from "@nivo/bar";
import { useMediaQuery } from "react-responsive";
import { BasicTooltip } from "@nivo/tooltip";
import { COLOR_LB_BLUE, COLOR_LB_ORANGE } from "../../../utils/constants";

export type BarDualToneProps = {
  data: UserListeningActivityData;
  range: UserStatsAPIRange;
  lastRangePeriod: {
    start?: number;
    end?: number;
  };
  thisRangePeriod: {
    start?: number;
    end?: number;
  };
  showLegend?: boolean;
};

export default function BarDualTone(props: BarDualToneProps) {
  const isMobile = useMediaQuery({ maxWidth: 767 });

  const rangeMap = {
    week: {
      dateFormat: {
        day: "2-digit",
        month: "long",
        year: "numeric",
      } as Intl.DateTimeFormatOptions,
      legendDateFormat: {
        day: "2-digit",
        month: "short",
      } as Intl.DateTimeFormatOptions,
      keys: ["lastRangeCount", "thisRangeCount"],
      itemWidth: 120,
    },
    this_week: {
      dateFormat: {
        day: "2-digit",
        month: "long",
        year: "numeric",
      } as Intl.DateTimeFormatOptions,
      legendDateFormat: {
        day: "2-digit",
        month: "short",
      } as Intl.DateTimeFormatOptions,
      keys: ["lastRangeCount", "thisRangeCount"],
      itemWidth: 120,
    },
    month: {
      dateFormat: {
        day: "2-digit",
        month: "long",
        year: "numeric",
      } as Intl.DateTimeFormatOptions,
      legendDateFormat: {
        month: "long",
        year: "numeric",
      } as Intl.DateTimeFormatOptions,
      keys: !isMobile
        ? ["lastRangeCount", "thisRangeCount"]
        : ["thisRangeCount"],
      itemWidth: 100,
    },
    this_month: {
      dateFormat: {
        day: "2-digit",
        month: "long",
        year: "numeric",
      } as Intl.DateTimeFormatOptions,
      legendDateFormat: {
        month: "long",
        year: "numeric",
      } as Intl.DateTimeFormatOptions,
      keys: !isMobile
        ? ["lastRangeCount", "thisRangeCount"]
        : ["thisRangeCount"],
      itemWidth: 100,
    },
    year: {
      dateFormat: {
        month: "long",
        year: "numeric",
      } as Intl.DateTimeFormatOptions,
      legendDateFormat: {
        year: "numeric",
      } as Intl.DateTimeFormatOptions,
      keys: ["lastRangeCount", "thisRangeCount"],
      itemWidth: 70,
    },
    this_year: {
      dateFormat: {
        month: "long",
        year: "numeric",
      } as Intl.DateTimeFormatOptions,
      legendDateFormat: {
        year: "numeric",
      } as Intl.DateTimeFormatOptions,
      keys: ["lastRangeCount", "thisRangeCount"],
      itemWidth: 70,
    },
    all_time: {
      dateFormat: {
        year: "numeric",
      } as Intl.DateTimeFormatOptions,
      keys: ["thisRangeCount"],
      itemWidth: 0,
    },
  };

  const generateLegendLabel = (start?: number, end?: number): string => {
    const { range } = props;
    let legendDateFormat = {};
    if (range && range !== "all_time") {
      ({ legendDateFormat } = rangeMap[range] || {});
    }

    const startDate = start ? new Date(start * 1000) : undefined;
    const endDate = end ? new Date(end * 1000) : undefined;

    if (endDate) {
      return `${startDate?.toLocaleString("en-us", {
        ...legendDateFormat,
        timeZone: "UTC",
      })} - ${endDate.toLocaleString("en-us", {
        ...legendDateFormat,
        timeZone: "UTC",
      })}`;
    }
    return (
      startDate?.toLocaleString("en-us", {
        ...legendDateFormat,
        timeZone: "UTC",
      }) || ""
    );
  };

  const { data, range, lastRangePeriod, thisRangePeriod } = props;
  let { showLegend } = props;
  showLegend = showLegend && !(isMobile && range === "month");

  const { dateFormat, keys, itemWidth } = rangeMap[range] || {};

  const customTooltip = (elem: BarTooltipProps<UserListeningActivityDatum>) => {
    const { id, data: datum, color, value } = elem;

    let dateString: string;
    let listenCount: number;
    if (id === "lastRangeCount") {
      const lastRangeDate = new Date((datum.lastRangeTs ?? 0) * 1000);
      dateString = lastRangeDate.toLocaleString("en-us", {
        ...dateFormat,
        timeZone: "UTC",
      });
      listenCount = datum.lastRangeCount!;
    } else {
      const thisRangeDate = new Date((datum?.thisRangeTs ?? 0) * 1000);
      dateString = thisRangeDate.toLocaleString("en-us", {
        ...dateFormat,
        timeZone: "UTC",
      });
      listenCount = datum.thisRangeCount!;
    }
    return (
      <BasicTooltip
        id={dateString}
        value={`${value} ${Number(value) === 1 ? "listen" : "listens"}`}
        color={color}
      />
    );
  };

  const tickFormatter = (tick: any) => {
    return (Number(tick) % 3) - 1 === 0 ? tick : "";
  };
  return (
    <div
      className="stats-full-width-graph user-listening-activity"
      data-testid="listening-activity-bar"
    >
      <ResponsiveBar
        data={data}
        indexBy="id"
        keys={keys}
        groupMode="grouped"
        colors={({ id }) => {
          return id === "thisRangeCount" ? COLOR_LB_ORANGE : COLOR_LB_BLUE;
        }}
        axisBottom={{
          format:
            (range === "all_time" || range === "month") && isMobile
              ? tickFormatter
              : undefined,
        }}
        axisLeft={{
          format: ".2~s",
        }}
        minValue={0}
        padding={0.3}
        innerPadding={2}
        enableLabel={false}
        tooltip={customTooltip}
        margin={{
          left: 45,
          bottom: 40,
          top: showLegend ? 30 : 20,
        }}
        enableGridY={false}
        layers={["grid", "axes", "bars", "markers", "annotations", "legends"]}
        legends={
          showLegend
            ? [
                {
                  dataFrom: "keys",
                  data: [
                    {
                      id: "lastRangeName",
                      label: generateLegendLabel(
                        lastRangePeriod.start,
                        lastRangePeriod.end
                      ),
                      color: COLOR_LB_BLUE,
                    },
                    {
                      id: "thisRangeName",
                      label: generateLegendLabel(
                        thisRangePeriod.start,
                        thisRangePeriod.end
                      ),
                      color: COLOR_LB_ORANGE,
                    },
                  ],
                  anchor: "top-right",
                  direction: "row",
                  itemHeight: 20,
                  translateY: -20,
                  symbolSize: 10,
                  itemWidth,
                },
              ]
            : []
        }
      />
    </div>
  );
}
