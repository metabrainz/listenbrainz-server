import * as React from "react";
import MediaQuery from "react-responsive";

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
    start?: Date;
    end?: Date;
  };
  thisRangePeriod: {
    start?: Date;
    end?: Date;
  };
  loading: boolean;
  totalListens: number;
  avgListens: number;
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
    };
  }

  componentDidUpdate(prevProps: UserListeningActivityProps) {
    const { range: prevRange } = prevProps;
    const { range: currRange } = this.props;
    if (prevRange !== currRange) {
      this.loadData();
    }
  }

  getData = async (): Promise<UserListeningActivityResponse> => {
    const { range, user } = this.props;
    const data = await this.APIService.getUserListeningActivity(
      user.name,
      range
    );

    return data;
  };

  processData = (
    data: UserListeningActivityResponse
  ): UserListeningActivityData => {
    const { range } = this.props;
    if (range === "week") {
      return this.processWeek(data);
    }
    if (range === "month") {
      return this.processMonth(data);
    }
    if (range === "year") {
      return this.processYear(data);
    }
    return this.processAllTime(data);
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
        const thisWeekDate = new Date(thisWeekDay.from_ts * 1000);
        const thisWeekCount = thisWeekDay.listen_count;
        totalListens += thisWeekCount;
        totalDays += 1;

        thisWeekData = {
          thisRangeCount: thisWeekCount,
          thisRangeDate: thisWeekDate,
        };
      }

      const lastWeekDate = new Date(lastWeekDay.from_ts * 1000);
      return {
        id: lastWeekDate.toLocaleString("en-us", dateFormat),
        lastRangeCount: lastWeekDay.listen_count,
        lastRangeDate: lastWeekDate,
        ...thisWeekData,
      };
    });

    this.setState({
      avgListens: Math.ceil(totalListens / totalDays),
      lastRangePeriod: {
        start: new Date(lastWeek[0].from_ts * 1000),
        end: new Date(lastWeek[6].from_ts * 1000),
      },
      thisRangePeriod: {
        start: new Date(thisWeek[0].from_ts * 1000),
        end: new Date(thisWeek[totalDays - 1].from_ts * 1000),
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
    const numOfDaysInLastMonth =
      new Date(
        startOfLastMonth.getUTCFullYear(),
        startOfLastMonth.getUTCMonth(),
        0
      ).getDate() + 1;

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
        const thisMonthDate = new Date(thisMonthDay.from_ts * 1000);
        totalListens += thisMonthCount;
        totalDays += 1;

        thisMonthData = {
          thisRangeCount: thisMonthCount,
          thisRangeDate: thisMonthDate,
        };
      }

      const lastMonthCount = lastMonthDay.listen_count;
      const lastMonthDate = new Date(lastMonthDay.from_ts * 1000);
      return {
        id: lastMonthDate.toLocaleString("en-us", dateFormat),
        lastRangeCount: lastMonthCount,
        lastRangeDate: lastMonthDate,
        ...thisMonthData,
      };
    });

    this.setState({
      avgListens: Math.ceil(totalListens / totalDays),
      lastRangePeriod: {
        start: new Date(lastMonth[0].from_ts * 1000),
      },
      thisRangePeriod: {
        start: new Date(thisMonth[0].from_ts * 1000),
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
        const thisYearDate = new Date(thisYearMonth.from_ts * 1000);
        const thisYearCount = thisYearMonth.listen_count;
        totalListens += thisYearCount;
        totalMonths += 1;

        thisYearData = {
          thisRangeCount: thisYearCount,
          thisRangeDate: thisYearDate,
        };
      }

      const lastYearDate = new Date(lastYearMonth.from_ts * 1000);
      return {
        id: lastYearDate.toLocaleString("en-us", dateFormat),
        lastRangeCount: lastYearMonth.listen_count,
        lastRangeDate: lastYearDate,
        ...thisYearData,
      };
    });

    this.setState({
      avgListens: Math.ceil(totalListens / totalMonths),
      lastRangePeriod: {
        start: new Date(lastYear[0].from_ts * 1000),
      },
      thisRangePeriod: {
        start: new Date(thisYear[0].from_ts * 1000),
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
          thisRangeDate: date,
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
          thisRangeDate: date,
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
    this.setState({ loading: true });
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
    } = this.state;
    const { range } = this.props;
    const { perRange } = this.rangeMap[range || "week"];

    return (
      <div>
        <Card>
          <Loader isLoading={loading}>
            <div className="row">
              <div className="col-xs-12" style={{ height: "25em" }}>
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
                            &nbsp;Listens per day
                          </span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </MediaQuery>
            </div>
          </Loader>
        </Card>
      </div>
    );
  }
}
