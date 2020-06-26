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
  ): UserListeningActivityState | null {
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
      const lastWeek = data.payload.listening_activity
        .slice(0, 7)
        .map((day) => {
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
        return {
          x: date.toLocaleString("en-us", {
            weekday: "short",
            timeZone: "UTC",
          }),
          y: day.listen_count,
          date,
        };
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
    } else if (range === "year") {
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
      const thisYear = data.payload.listening_activity
        .slice(12)
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
    }
  };

  loadData = async (): Promise<void> => {
    const data = await this.getData();
    console.log("test2");
    this.setState({
      data: this.processData(data),
    });
  };

  render() {
    const { data } = this.state;
    const { range } = this.props;

    return (
      <div>
        <div className="col-md-8" style={{ height: "20em" }}>
          <Card>
            <LineDualTone data={data} dateFormat={this.dateFormat[range]} />
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
                    118
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
                    17
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
