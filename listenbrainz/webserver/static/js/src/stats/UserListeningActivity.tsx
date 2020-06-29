import * as React from "react";

import APIService from "../APIService";
import Card from "../components/Card";
import LineDualTone from "./LineDualTone";

export type UserListeningActivityProps = {
  range: UserStatsAPIRange;
  user: ListenBrainzUser;
  apiUrl: string;
};

export type UserListeningActivityState = {
  data: UserListeningActivityData;
  prevRange: UserStatsAPIRange;
  totalListens: number;
  avgListens: number;
};

export default class UserListeningActivity extends React.Component<
  UserListeningActivityProps,
  UserListeningActivityState
> {
  APIService: APIService;

  dateFormat = {
    week: {
      day: "2-digit",
      month: "long",
      year: "numeric",
    },
    month: {
      day: "2-digit",
      month: "long",
      year: "numeric",
    },
    year: {
      month: "long",
      year: "numeric",
    },
    all_time: {
      year: "numeric",
    },
  };

  constructor(props: UserListeningActivityProps) {
    super(props);

    this.APIService = new APIService(
      props.apiUrl || `${window.location.origin}/1`
    );

    this.state = {
      data: [],
      prevRange: "" as UserStatsAPIRange,
      totalListens: 0,
      avgListens: 0,
    };
  }

  componentDidMount() {
    this.loadData();
  }

  componentDidUpdate() {
    const { data } = this.state;
    if (!data.length) {
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

  static getDerivedStateFromProps(
    props: UserListeningActivityProps,
    state: UserListeningActivityState
  ): Partial<UserListeningActivityState | null> {
    if (props.range !== state.prevRange) {
      return {
        data: [],
        prevRange: props.range,
      };
    }

    return null;
  }

  processData = (
    data: UserListeningActivityResponse
  ): UserListeningActivityData => {
    const { range } = this.props;
    if (range === "week") {
      return this.processWeek(data);
    } else if (range === "month") {
      return this.processMonth(data);
    } else if (range === "year") {
      return this.processYear(data);
    } else {
      return this.processAllTime(data);
    }
  };

  processWeek = (
    data: UserListeningActivityResponse
  ): UserListeningActivityData => {
    let totalListens = 0;
    let totalDays = 0;
    const lastWeek = data.payload.listening_activity.slice(0, 7).map((day) => {
      const date = new Date(day.from_ts * 1000);
      return {
        x: date.toLocaleString("en-us", {
          weekday: "short",
          timeZone: "UTC",
        }),
        y: day.listen_count,
        date,
      };
    });
    const thisWeek = data.payload.listening_activity.slice(7).map((day) => {
      const date = new Date(day.from_ts * 1000);
      totalListens += day.listen_count;
      totalDays += 1;
      return {
        x: date.toLocaleString("en-us", {
          weekday: "short",
          timeZone: "UTC",
        }),
        y: day.listen_count,
        date,
      };
    });

    this.setState({
      avgListens: Math.ceil(totalListens / totalDays),
      totalListens,
    });

    return [
      {
        id: "Last Week",
        data: lastWeek,
      },
      {
        id: "This Week",
        data: thisWeek,
      },
    ];
  };

  processMonth = (
    data: UserListeningActivityResponse
  ): UserListeningActivityData => {
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

    const lastMonth = data.payload.listening_activity
      .slice(0, numOfDaysInLastMonth)
      .map((day) => {
        const date = new Date(day.from_ts * 1000);
        return {
          x: date.toLocaleString("en-us", {
            day: "2-digit",
            timeZone: "UTC",
          }),
          y: day.listen_count,
          date,
        };
      });
    const thisMonth = data.payload.listening_activity
      .slice(numOfDaysInLastMonth)
      .map((day) => {
        const date = new Date(day.from_ts * 1000);
        totalListens += day.listen_count;
        totalDays += 1;
        return {
          x: date.toLocaleString("en-us", {
            day: "2-digit",
            timeZone: "UTC",
          }),
          y: day.listen_count,
          date,
        };
      });

    this.setState({
      avgListens: Math.ceil(totalListens / totalDays),
      totalListens,
    });

    return [
      {
        id: "Last Month",
        data: lastMonth,
      },
      {
        id: "This Month",
        data: thisMonth,
      },
    ];
  };

  processYear = (
    data: UserListeningActivityResponse
  ): UserListeningActivityData => {
    let totalListens = 0;
    let totalMonths = 0;
    const lastYear = data.payload.listening_activity
      .slice(0, 12)
      .map((month) => {
        const date = new Date(month.from_ts * 1000);
        return {
          x: date.toLocaleString("en-us", {
            month: "short",
            timeZone: "UTC",
          }),
          y: month.listen_count,
          date,
        };
      });
    const thisYear = data.payload.listening_activity.slice(12).map((month) => {
      const date = new Date(month.from_ts * 1000);
      totalListens += month.listen_count;
      totalMonths += 1;
      return {
        x: date.toLocaleString("en-us", {
          month: "short",
          timeZone: "UTC",
        }),
        y: month.listen_count,
        date,
      };
    });

    this.setState({
      avgListens: Math.ceil(totalListens / totalMonths),
      totalListens,
    });

    return [
      {
        id: "Last Year",
        data: lastYear,
      },
      {
        id: "This Year",
        data: thisYear,
      },
    ];
  };

  processAllTime = (
    data: UserListeningActivityResponse
  ): UserListeningActivityData => {
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
          x: date.toLocaleString("en-us", {
            year: "2-digit",
            timeZone: "UTC",
          }),
          y: yearData.listen_count,
          date,
        });
        totalListens += yearData.listen_count;
      } else {
        const date = new Date(`${i}-01-01T00:00:00.000+00:00`);
        allTimeData.push({
          x: date.toLocaleString("en-us", {
            year: "2-digit",
            timeZone: "UTC",
          }),
          y: 0,
          date,
        });
      }
    }

    this.setState({
      avgListens: Math.ceil(totalListens / totalYears),
      totalListens,
    });

    return [
      {
        id: "All Time",
        data: allTimeData,
      },
    ];
  };

  loadData = async (): Promise<void> => {
    const data = await this.getData();
    this.setState({
      data: this.processData(data),
    });
  };

  render() {
    const { data, totalListens, avgListens } = this.state;
    const { range } = this.props;

    return (
      <div>
        <div className="col-md-8" style={{ height: "20em" }}>
          <Card>
            <LineDualTone
              data={data}
              dateFormat={this.dateFormat[range]}
              showLegend={range !== "all_time"}
            />
          </Card>
        </div>
        <div className="col-md-4" style={{ height: "20em" }}>
          <Card style={{ display: "flex", alignItems: "center" }}>
            <table
              style={{ height: "50%", width: "100%", tableLayout: "fixed" }}
            >
              <tbody>
                <tr>
                  <td
                    style={{
                      width: "30%",
                      textAlign: "end",
                      fontSize: 30,
                      fontWeight: "bold",
                    }}
                  >
                    {totalListens}
                  </td>
                  <td>
                    <span style={{ fontSize: 24 }}>&nbsp;Listens</span>
                  </td>
                </tr>
                <tr>
                  <td
                    style={{
                      width: "30%",
                      textAlign: "end",
                      fontSize: 30,
                      fontWeight: "bold",
                    }}
                  >
                    {avgListens}
                  </td>
                  <td>
                    <span style={{ fontSize: 24 }}>&nbsp;Listens per day</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </Card>
        </div>
      </div>
    );
  }
}
