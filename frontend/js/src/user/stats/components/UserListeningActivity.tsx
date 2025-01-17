import * as React from "react";
import MediaQuery from "react-responsive";
import { faExclamationCircle, faLink } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";

import { useQuery } from "@tanstack/react-query";
import Card from "../../../components/Card";
import BarDualTone from "./BarDualTone";
import Loader from "../../../components/Loader";
import { COLOR_BLACK } from "../../../utils/constants";
import GlobalAppContext from "../../../utils/GlobalAppContext";

export type UserListeningActivityProps = {
  range: UserStatsAPIRange;
  user?: ListenBrainzUser;
};

export type UserListeningActivityState = {
  data: UserListeningActivityData;
  lastRangePeriod: {
    start?: number;
    end?: number;
  };
  thisRangePeriod: {
    start?: number;
    end?: number;
  };
  loading: boolean;
  totalListens: number;
  avgListens: number;
  errorMessage: string;
  hasError: boolean;
};

export default function UserListeningActivity(
  props: UserListeningActivityProps
) {
  const { APIService } = React.useContext(GlobalAppContext);

  // Props
  const { range, user } = props;

  // Fetch data
  const { data: loaderData, isLoading: loading } = useQuery({
    queryKey: ["userListeningActivity", user?.name, range],
    queryFn: async () => {
      try {
        const queryData = await APIService.getUserListeningActivity(
          user?.name,
          range
        );
        return {
          data: queryData,
          hasError: false,
          errorMessage: "",
        };
      } catch (error) {
        return {
          data: {} as UserListeningActivityResponse,
          hasError: true,
          errorMessage: error.message,
        };
      }
    },
  });

  const {
    data: rawData = {} as UserListeningActivityResponse,
    hasError = false,
    errorMessage = "",
  } = loaderData || {};

  const rangeMap = {
    week: {
      dateFormat: {
        weekday: "short",
        timeZone: "UTC",
      } as Intl.DateTimeFormatOptions,
      perRange: "day",
    },
    this_week: {
      dateFormat: {
        weekday: "short",
        timeZone: "UTC",
      } as Intl.DateTimeFormatOptions,
      perRange: "day",
    },
    month: {
      dateFormat: {
        day: "2-digit",
        timeZone: "UTC",
      } as Intl.DateTimeFormatOptions,
      perRange: "day",
    },
    this_month: {
      dateFormat: {
        day: "2-digit",
        timeZone: "UTC",
      } as Intl.DateTimeFormatOptions,
      perRange: "day",
    },
    year: {
      dateFormat: {
        month: "short",
        timeZone: "UTC",
      } as Intl.DateTimeFormatOptions,
      perRange: "month",
    },
    this_year: {
      dateFormat: {
        month: "short",
        timeZone: "UTC",
      } as Intl.DateTimeFormatOptions,
      perRange: "month",
    },
    all_time: {
      dateFormat: {
        year: "numeric",
        timeZone: "UTC",
      } as Intl.DateTimeFormatOptions,
      perRange: "year",
    },
  };

  const [data, setData] = React.useState<UserListeningActivityData>([]);
  const [totalListens, setTotalListens] = React.useState<number>(0);
  const [avgListens, setAvgListens] = React.useState<number>(0);
  const [lastRangePeriod, setLastRangePeriod] = React.useState<{
    start?: number;
    end?: number;
  }>({});
  const [thisRangePeriod, setThisRangePeriod] = React.useState<{
    start?: number;
    end?: number;
  }>({});

  const getNumberOfDaysInMonth = (month: Date): number => {
    return new Date(
      month.getUTCFullYear(),
      month.getUTCMonth() + 1,
      0
    ).getDate();
  };

  const processWeek = (
    unprocessedData: UserListeningActivityResponse
  ): UserListeningActivityData => {
    const { dateFormat } = rangeMap.week;
    let totalListensForWeek = 0;
    let totalDays = 0;

    const lastWeek = unprocessedData.payload.listening_activity.slice(0, 7);
    const thisWeek = unprocessedData.payload.listening_activity.slice(7);

    const result = lastWeek.map((lastWeekDay, index) => {
      const thisWeekDay = thisWeek[index];
      let thisWeekData = {};
      if (thisWeekDay) {
        const thisWeekCount = thisWeekDay.listen_count;
        totalListensForWeek += thisWeekCount;
        totalDays += 1;

        thisWeekData = {
          thisRangeCount: thisWeekCount,
          thisRangeTs: thisWeekDay.from_ts,
        };
      }

      const lastWeekDate = new Date(lastWeekDay.from_ts * 1000);
      return {
        id: lastWeekDate.toLocaleString("en-us", dateFormat),
        lastRangeCount: lastWeekDay.listen_count,
        lastRangeTs: lastWeekDay.from_ts,
        ...thisWeekData,
      };
    });

    setAvgListens(
      totalListensForWeek > 0 ? Math.ceil(totalListensForWeek / totalDays) : 0
    );
    setLastRangePeriod({
      start: lastWeek?.[0]?.from_ts,
      end: lastWeek?.[6]?.from_ts,
    });
    setThisRangePeriod({
      start: thisWeek?.[0]?.from_ts,
      end: thisWeek?.[totalDays - 1]?.from_ts,
    });
    setTotalListens(totalListensForWeek);

    return result;
  };

  const processMonth = (
    unprocessedData: UserListeningActivityResponse
  ): UserListeningActivityData => {
    const { dateFormat } = rangeMap.month;
    let totalListensForMonth = 0;
    let totalDays = 0;

    const startOfLastMonth = new Date(
      unprocessedData.payload.listening_activity[0].from_ts * 1000
    );

    const endOfThisMonth = new Date(
      unprocessedData.payload.listening_activity[
        unprocessedData.payload.listening_activity.length - 1
      ].from_ts * 1000
    );

    const numOfDaysInLastMonth = getNumberOfDaysInMonth(startOfLastMonth);
    const numOfDaysInThisMonth = getNumberOfDaysInMonth(endOfThisMonth);

    const lastMonth = unprocessedData.payload.listening_activity.slice(
      0,
      numOfDaysInLastMonth
    );
    const thisMonth = unprocessedData.payload.listening_activity.slice(
      numOfDaysInLastMonth
    );

    const result = [];

    const maxDays = Math.max(numOfDaysInLastMonth, numOfDaysInThisMonth);

    for (let i = 0; i < maxDays; i += 1) {
      const lastMonthDay = lastMonth[i] || null;
      const thisMonthDay = thisMonth[i] || null;

      if (!lastMonthDay && !thisMonthDay) {
        const daysInMilliseconds = 24 * 60 * 60 * 1000;

        // Determine the date based on which month has more days
        const dateTS =
          numOfDaysInLastMonth > numOfDaysInThisMonth
            ? new Date(startOfLastMonth.getTime() + i * daysInMilliseconds)
            : new Date(
                startOfLastMonth.getTime() +
                  numOfDaysInLastMonth * daysInMilliseconds +
                  i * daysInMilliseconds
              );

        result.push({
          id: dateTS.toLocaleString("en-us", dateFormat),
          lastRangeCount: 0,
          thisRangeCount: 0,
        });
        // eslint-disable-next-line no-continue
        continue;
      }

      let thisMonthData = {};
      let lastMonthData = {};
      if (thisMonthDay) {
        const thisMonthCount = thisMonthDay.listen_count;
        totalListensForMonth += thisMonthCount;
        totalDays += 1;

        thisMonthData = {
          thisRangeCount: thisMonthCount,
          thisRangeTs: thisMonthDay.from_ts,
        };
      }

      if (lastMonthDay) {
        lastMonthData = {
          lastRangeCount: lastMonthDay.listen_count,
          lastRangeTs: lastMonthDay.from_ts,
        };
      }

      const dateTS = lastMonthDay
        ? new Date(lastMonthDay.from_ts * 1000)
        : new Date(thisMonthDay.from_ts * 1000);

      result.push({
        id: dateTS.toLocaleString("en-us", dateFormat),
        ...lastMonthData,
        ...thisMonthData,
      });
    }

    setAvgListens(
      totalListensForMonth > 0 ? Math.ceil(totalListensForMonth / totalDays) : 0
    );
    setLastRangePeriod({
      start: lastMonth?.[0]?.from_ts,
    });
    setThisRangePeriod({
      start: thisMonth?.[0]?.from_ts,
    });
    setTotalListens(totalListensForMonth);

    return result;
  };

  const processYear = (
    unprocessedData: UserListeningActivityResponse
  ): UserListeningActivityData => {
    const { dateFormat } = rangeMap.year;
    let totalListensForYear = 0;
    let totalMonths = 0;

    const lastYear = unprocessedData.payload.listening_activity.slice(0, 12);
    const thisYear = unprocessedData.payload.listening_activity.slice(12);

    const result = lastYear.map((lastYearMonth, index) => {
      const thisYearMonth = thisYear[index];
      let thisYearData = {};
      if (thisYearMonth) {
        const thisYearCount = thisYearMonth.listen_count;
        totalListensForYear += thisYearCount;
        totalMonths += 1;

        thisYearData = {
          thisRangeCount: thisYearCount,
          thisRangeTs: thisYearMonth.from_ts,
        };
      }

      const lastYearDate = new Date(lastYearMonth.from_ts * 1000);
      return {
        id: lastYearDate.toLocaleString("en-us", dateFormat),
        lastRangeCount: lastYearMonth.listen_count,
        lastRangeTs: lastYearMonth.from_ts,
        ...thisYearData,
      };
    });

    setAvgListens(
      totalListensForYear > 0 ? Math.ceil(totalListensForYear / totalMonths) : 0
    );
    setLastRangePeriod({
      start: lastYear?.[0]?.from_ts,
    });
    setThisRangePeriod({
      start: thisYear?.[0]?.from_ts,
    });
    setTotalListens(totalListensForYear);

    return result;
  };

  const processAllTime = (
    unprocessedData: UserListeningActivityResponse
  ): UserListeningActivityData => {
    const { dateFormat } = rangeMap.all_time;
    let totalListensForAllTime = 0;
    let totalYears = 0;
    const allTimeData = [];
    const currYear = new Date().getFullYear();
    let encounteredNonEmptyYear: boolean = false;

    for (let i = 2002; i <= currYear; i += 1) {
      const yearData = unprocessedData.payload.listening_activity.filter(
        (year) => year.time_range === String(i)
      )[0];
      totalYears += 1;

      if (yearData) {
        if (encounteredNonEmptyYear === false) {
          if (yearData.listen_count > 0) {
            encounteredNonEmptyYear = true;
          }
        }
        const date = new Date(yearData.from_ts * 1000);
        if (encounteredNonEmptyYear) {
          allTimeData.push({
            id: date.toLocaleString("en-us", dateFormat),
            thisRangeCount: yearData.listen_count,
            thisRangeTs: yearData.from_ts,
          });
        }

        totalListensForAllTime += yearData.listen_count;
      } else {
        const date = new Date(`${i}-01-01T00:00:00.000+00:00`);
        allTimeData.push({
          id: date.toLocaleString("en-us", {
            year: "numeric",
            timeZone: "UTC",
          }),
          thisRangeCount: 0,
          thisRangeTs: date.getTime() / 1000,
        });
      }
    }

    setAvgListens(
      totalListensForAllTime > 0
        ? Math.ceil(totalListensForAllTime / totalYears)
        : 0
    );
    setTotalListens(totalListensForAllTime);

    return allTimeData;
  };

  const processData = (
    unprocessedData: UserListeningActivityResponse
  ): UserListeningActivityData => {
    if (!unprocessedData?.payload) {
      return [] as UserListeningActivityData;
    }
    if (!unprocessedData?.payload) {
      return [] as UserListeningActivityData;
    }
    if (range === "week" || range === "this_week") {
      return processWeek(unprocessedData);
    }
    if (range === "month" || range === "this_month") {
      return processMonth(unprocessedData);
    }
    if (range === "year" || range === "this_year") {
      return processYear(unprocessedData);
    }
    if (range === "all_time") {
      return processAllTime(unprocessedData);
    }
    return [];
  };

  React.useEffect(() => {
    if (rawData && rawData?.payload) {
      setData(processData(rawData));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rawData]);

  const { perRange } = rangeMap[range] || {};

  return (
    <Card
      style={{ marginTop: 20, minHeight: 400 }}
      data-testid="listening-activity"
    >
      <div className="row">
        <div className="col-xs-10">
          <h3 className="capitalize-bold" style={{ marginLeft: 20 }}>
            Listening Activity
          </h3>
        </div>
        <div className="col-xs-2 text-right">
          <h4 style={{ marginTop: 20 }}>
            <a href="#listening-activity">
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
        {hasError && (
          <div
            className="flex-center"
            style={{ minHeight: "inherit" }}
            data-testid="error-message"
          >
            <span style={{ fontSize: 24 }} className="text-center">
              <FontAwesomeIcon
                icon={faExclamationCircle as IconProp}
                size="2x"
              />{" "}
              {errorMessage}
            </span>
          </div>
        )}
        {!hasError && (
          <>
            <BarDualTone
              data={data}
              range={range}
              showLegend={range !== "all_time"}
              lastRangePeriod={lastRangePeriod}
              thisRangePeriod={thisRangePeriod}
            />
            <div className="row mt-5 mb-15">
              <MediaQuery minWidth={768}>
                <div className="col-md-6 text-center">
                  <span
                    style={{
                      fontSize: 30,
                      fontWeight: "bold",
                    }}
                  >
                    {totalListens}
                  </span>
                  <span>
                    <span style={{ fontSize: 24 }}>&nbsp;Listens</span>
                  </span>
                </div>
                <div className="col-md-6 text-center">
                  <span
                    style={{
                      fontSize: 30,
                      fontWeight: "bold",
                    }}
                  >
                    {avgListens}
                  </span>
                  <span style={{ fontSize: 24 }}>
                    &nbsp;Listens per {perRange}
                  </span>
                </div>
              </MediaQuery>
              <MediaQuery maxWidth={767}>
                <div
                  className="col-xs-12"
                  style={{ display: "flex", justifyContent: "center" }}
                >
                  <table style={{ width: "90%" }}>
                    <tbody>
                      <tr>
                        <td
                          style={{
                            textAlign: "end",
                            fontSize: 28,
                            fontWeight: "bold",
                          }}
                        >
                          {totalListens}
                        </td>
                        <td>
                          <span style={{ fontSize: 22, textAlign: "start" }}>
                            &nbsp;Listens
                          </span>
                        </td>
                      </tr>
                      <tr>
                        <td
                          style={{
                            width: "30%",
                            textAlign: "end",
                            fontSize: 28,
                            fontWeight: "bold",
                          }}
                        >
                          {avgListens}
                        </td>
                        <td>
                          <span style={{ fontSize: 22, textAlign: "start" }}>
                            &nbsp;Listens per {perRange}
                          </span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </MediaQuery>
            </div>
          </>
        )}
      </Loader>
    </Card>
  );
}
