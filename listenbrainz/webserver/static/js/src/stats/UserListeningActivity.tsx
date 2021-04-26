import * as React from "react";
import MediaQuery from "react-responsive";
import { faExclamationCircle, faLink } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";

import APIService from "../APIService";
import Card from "../components/Card";
import BarDualTone from "./BarDualTone";
import Loader from "../components/Loader";

export type UserListeningActivityProps = {
  range: UserStatsAPIRange;
  user: ListenBrainzUser;
  apiUrl: string;
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

export default class UserListeningActivity extends React.Component<
  UserListeningActivityProps,
  UserListeningActivityState
> {
  APIService: APIService;

  rangeMap = {
    week: {
      dateFormat: {
        weekday: "short",
        timeZone: "UTC",
      },
      perRange: "day",
    },
    month: {
      dateFormat: {
        day: "2-digit",
        timeZone: "UTC",
      },
      perRange: "day",
    },
    year: {
      dateFormat: {
        month: "short",
        timeZone: "UTC",
      },
      perRange: "month",
    },
    all_time: {
      dateFormat: {
        year: "numeric",
        timeZone: "UTC",
      },
      perRange: "year",
    },
  };

  constructor(props: UserListeningActivityProps) {
    super(props);

    this.APIService = new APIService(
      props.apiUrl || `${window.location.origin}/1`
    );

    this.state = {
      data: [],
      lastRangePeriod: {},
      thisRangePeriod: {},
      totalListens: 0,
      avgListens: 0,
      loading: false,
      hasError: false,
      errorMessage: "",
    };
  }

  componentDidUpdate(prevProps: UserListeningActivityProps) {
    const { range: prevRange } = prevProps;
    const { range: currRange } = this.props;
    if (prevRange !== currRange) {
      if (["week", "month", "year", "all_time"].indexOf(currRange) < 0) {
        this.setState({
          loading: false,
          hasError: true,
          errorMessage: `Invalid range: ${currRange}`,
        });
      } else {
        this.loadData();
      }
    }
  }

  getData = async (): Promise<UserListeningActivityResponse> => {
    const { range, user } = this.props;
    try {
      const data = await this.APIService.getUserListeningActivity(
        user.name,
        range
      );
      return data;
    } catch (error) {
      if (error.response && error.response.status === 204) {
        this.setState({
          loading: false,
          hasError: true,
          errorMessage: "Statistics for the user have not been calculated",
        });
      } else {
        throw error;
      }
    }
    return {} as UserListeningActivityResponse;
  };

  getNumberOfDaysInMonth = (month: Date): number => {
    return new Date(
      month.getUTCFullYear(),
      month.getUTCMonth() + 1,
      0
    ).getDate();
  };

  processData = (
    data: UserListeningActivityResponse
  ): UserListeningActivityData => {
    const { range } = this.props;
    let result = [] as UserListeningActivityData;
    if (!data?.payload) {
      return result;
    }
    if (range === "week") {
      result = this.processWeek(data);
    }
    else if (range === "month") {
      result = this.processMonth(data);
    }
    else if (range === "year") {
      result = this.processYear(data);
    }
    else if (range === "all_time") {
      result = this.processAllTime(data);
    }
    return result;
  };

  processWeek = (
    data: UserListeningActivityResponse
  ): UserListeningActivityData => {
    const { dateFormat } = this.rangeMap.week;
    let totalListens = 0;
    let totalDays = 0;

    const lastWeek = data.payload.listening_activity.slice(0, 7);
    const thisWeek = data.payload.listening_activity.slice(7);

    const result = lastWeek.map((lastWeekDay, index) => {
      const thisWeekDay = thisWeek[index];
      let thisWeekData = {};
      if (thisWeekDay) {
        const thisWeekCount = thisWeekDay.listen_count;
        totalListens += thisWeekCount;
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

    this.setState({
      avgListens: Math.ceil(totalListens / totalDays),
      lastRangePeriod: {
        start: lastWeek[0].from_ts,
        end: lastWeek[6].from_ts,
      },
      thisRangePeriod: {
        start: thisWeek[0].from_ts,
        end: thisWeek[totalDays - 1].from_ts,
      },
      totalListens,
    });

    return result;
  };

  processMonth = (
    data: UserListeningActivityResponse
  ): UserListeningActivityData => {
    const { dateFormat } = this.rangeMap.month;
    let totalListens = 0;
    let totalDays = 0;

    const startOfLastMonth = new Date(
      data.payload.listening_activity[0].from_ts * 1000
    );
    const numOfDaysInLastMonth = this.getNumberOfDaysInMonth(startOfLastMonth);

    const lastMonth = data.payload.listening_activity.slice(
      0,
      numOfDaysInLastMonth
    );
    const thisMonth = data.payload.listening_activity.slice(
      numOfDaysInLastMonth
    );

    const result = lastMonth.map((lastMonthDay, index) => {
      const thisMonthDay = thisMonth[index];
      let thisMonthData = {};
      if (thisMonthDay) {
        const thisMonthCount = thisMonthDay.listen_count;
        totalListens += thisMonthCount;
        totalDays += 1;

        thisMonthData = {
          thisRangeCount: thisMonthCount,
          thisRangeTs: thisMonthDay.from_ts,
        };
      }

      const lastMonthCount = lastMonthDay.listen_count;
      const lastMonthDate = new Date(lastMonthDay.from_ts * 1000);
      return {
        id: lastMonthDate.toLocaleString("en-us", dateFormat),
        lastRangeCount: lastMonthCount,
        lastRangeTs: lastMonthDay.from_ts,
        ...thisMonthData,
      };
    });

    this.setState({
      avgListens: Math.ceil(totalListens / totalDays),
      lastRangePeriod: {
        start: lastMonth[0].from_ts,
      },
      thisRangePeriod: {
        start: thisMonth[0].from_ts,
      },
      totalListens,
    });

    return result;
  };

  processYear = (
    data: UserListeningActivityResponse
  ): UserListeningActivityData => {
    const { dateFormat } = this.rangeMap.year;
    let totalListens = 0;
    let totalMonths = 0;

    const lastYear = data.payload.listening_activity.slice(0, 12);
    const thisYear = data.payload.listening_activity.slice(12);

    const result = lastYear.map((lastYearMonth, index) => {
      const thisYearMonth = thisYear[index];
      let thisYearData = {};
      if (thisYearMonth) {
        const thisYearCount = thisYearMonth.listen_count;
        totalListens += thisYearCount;
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

    this.setState({
      avgListens: Math.ceil(totalListens / totalMonths),
      lastRangePeriod: {
        start: lastYear[0].from_ts,
      },
      thisRangePeriod: {
        start: thisYear[0].from_ts,
      },
      totalListens,
    });

    return result;
  };

  processAllTime = (
    data: UserListeningActivityResponse
  ): UserListeningActivityData => {
    const { dateFormat } = this.rangeMap.all_time;
    let totalListens = 0;
    let totalYears = 0;

    const allTimeData = [];
    const currYear = new Date().getFullYear();
    for (let i = 2002; i <= currYear; i += 1) {
      const yearData = data.payload.listening_activity.filter(
        (year) => year.time_range === String(i)
      )[0];

      totalYears += 1;
      if (yearData) {
        const date = new Date(yearData.from_ts * 1000);
        allTimeData.push({
          id: date.toLocaleString("en-us", dateFormat),
          thisRangeCount: yearData.listen_count,
          thisRangeTs: yearData.from_ts,
        });
        totalListens += yearData.listen_count;
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

    this.setState({
      avgListens: Math.ceil(totalListens / totalYears),
      totalListens,
    });

    return allTimeData;
  };

  loadData = async (): Promise<void> => {
    this.setState({
      hasError: false,
      loading: true,
    });
    const data = await this.getData();
    this.setState({
      data: this.processData(data),
      loading: false,
    });
  };

  render() {
    const {
      data,
      totalListens,
      avgListens,
      lastRangePeriod,
      thisRangePeriod,
      loading,
      hasError,
      errorMessage,
    } = this.state;
    const { range } = this.props;
    const { perRange } = this.rangeMap[range] || {};

    return (
      <Card style={{ marginTop: 20, minHeight: 400 }}>
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
                  color="#000000"
                  style={{ marginRight: 20 }}
                />
              </a>
            </h4>
          </div>
        </div>

        <Loader isLoading={loading}>
          {hasError && (
            <div className="flex-center" style={{ minHeight: "inherit" }}>
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
              <div className="row">
                <div className="col-xs-12" style={{ height: 350 }}>
                  <BarDualTone
                    data={data}
                    range={range}
                    showLegend={range !== "all_time"}
                    lastRangePeriod={lastRangePeriod}
                    thisRangePeriod={thisRangePeriod}
                  />
                </div>
              </div>
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
}
