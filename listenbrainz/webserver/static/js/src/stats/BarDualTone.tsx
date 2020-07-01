/* eslint-disable react/prefer-stateless-function */
import * as React from "react";

import { ResponsiveBar, Layer } from "@nivo/bar";
import { BoxLegendSvg, LegendProps } from "@nivo/legends";
import { useMediaQuery } from "react-responsive";

export type LineDualToneProps = {
  data: UserListeningActivityData;
  range: UserStatsAPIRange;
  lastRangePeriod: {
    start?: Date;
    end?: Date;
  };
  thisRangePeriod: {
    start?: Date;
    end?: Date;
  };
  showLegend?: boolean;
};

const BarLegend = ({
  height,
  legends,
  width,
}: {
  height: number;
  legends: Array<LegendProps>;
  width: any;
}) => (
  <>
    {legends.map((legend) => (
      <BoxLegendSvg
        key={JSON.stringify(legend.data?.map(({ id }) => id))}
        {...legend}
        containerHeight={height}
        containerWidth={width}
      />
    ))}
  </>
);

export default function LineDualTone(
  props: React.PropsWithChildren<LineDualToneProps>
) {
  const isMobile = useMediaQuery({ maxWidth: 767 });

  const rangeMap = {
    week: {
      dateFormat: {
        day: "2-digit",
        month: "long",
        year: "numeric",
      },
      legendDateFormat: {
        day: "2-digit",
        month: "short",
      },
      keys: ["lastRangeCount", "thisRangeCount"],
      itemWidth: 120,
    },
    month: {
      dateFormat: {
        day: "2-digit",
        month: "long",
        year: "numeric",
      },
      legendDateFormat: {
        month: "long",
        year: "numeric",
      },
      keys: !isMobile
        ? ["lastRangeCount", "thisRangeCount"]
        : ["thisRangeCount"],
      itemWidth: 100,
    },
    year: {
      dateFormat: {
        month: "long",
        year: "numeric",
      },
      legendDateFormat: {
        year: "numeric",
      },
      keys: ["lastRangeCount", "thisRangeCount"],
      itemWidth: 70,
    },
    all_time: {
      dateFormat: {
        year: "numeric",
      },
      keys: ["thisRangeCount"],
      itemWidth: 0,
    },
  };

  const generateLegendLabel = (start?: Date, end?: Date): string => {
    const { range } = props;
    let legendDateFormat = {};
    if (range && range !== "all_time") {
      ({ legendDateFormat } = rangeMap[range]);
    }

    if (end) {
      return `${start?.toLocaleString("en-us", {
        ...legendDateFormat,
        timeZone: "UTC",
      })} - ${end.toLocaleString("en-us", {
        ...legendDateFormat,
        timeZone: "UTC",
      })}`;
    }
    return (
      start?.toLocaleString("en-us", {
        ...legendDateFormat,
        timeZone: "UTC",
      }) || ""
    );
  };

  const { data, range, lastRangePeriod, thisRangePeriod } = props;
  let { showLegend } = props;
  showLegend = showLegend && !(isMobile && range === "month");

  const { dateFormat, keys, itemWidth } = rangeMap[range || "week"];

  const customTooltip = (elem: any) => {
    const { id, data: datum } = elem;

    let dateString: string;
    let listenCount: number;
    if (id === "lastRangeCount") {
      dateString = datum.lastRangeDate!.toLocaleString("en-us", {
        ...dateFormat,
        timeZone: "UTC",
      });
      listenCount = datum.lastRangeCount!;
    } else {
      dateString = datum.thisRangeDate!.toLocaleString("en-us", {
        ...dateFormat,
        timeZone: "UTC",
      });
      listenCount = datum.thisRangeCount!;
    }
    return (
      <div>
        {dateString}: <strong>{String(listenCount)} Listens</strong>
      </div>
    );
  };

  const tickFormatter = (tick: any) => {
    return (Number(tick) % 3) - 1 === 0 ? tick : "";
  };

  return (
    <ResponsiveBar
      data={data}
      indexBy="id"
      keys={keys}
      groupMode="grouped"
      colors={({ id }) => {
        return id === "thisRangeCount" ? "#EB743B" : "#353070";
      }}
      axisBottom={{
        format:
          (range === "all_time" || range === "month") && isMobile
            ? tickFormatter
            : undefined,
      }}
      axisLeft={{
        format: ".2s",
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
      layers={
        ["grid", "axes", "bars", "markers", "annotations", BarLegend] as Array<
          Layer
        >
      }
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
                    color: "#353070",
                  },
                  {
                    id: "thisRangeName",
                    label: generateLegendLabel(
                      thisRangePeriod.start,
                      thisRangePeriod.end
                    ),
                    color: "#EB743B",
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
  );
}
