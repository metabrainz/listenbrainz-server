import * as React from "react";
import { faExclamationCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";

import APIService from "../APIService";
import Card from "../components/Card";
import Line from "./Line";
import Loader from "../components/Loader";

export type UserDailyActivityProps = {
  range: UserStatsAPIRange;
  user: ListenBrainzUser;
  apiUrl: string;
};

export type UserDailyActivityState = {
  data: UserDailyActivityData;
  loading: boolean;
  errorMessage: string;
  hasError: boolean;
};

export default class UserDailyActivity extends React.Component<
  UserDailyActivityProps,
  UserDailyActivityState
> {
  APIService: APIService;

  constructor(props: UserDailyActivityProps) {
    super(props);

    this.APIService = new APIService(
      props.apiUrl || `${window.location.origin}/1`
    );

    this.state = {
      data: [],
      loading: true,
      errorMessage: "",
      hasError: false,
    };
  }

  componentDidUpdate(prevProps: UserDailyActivityProps) {
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

  getData = async (): Promise<UserDailyActivityResponse> => {
    const { range, user } = this.props;
    try {
      const data = await this.APIService.getUserDailyActivity(user.name, range);
      return data;
    } catch (error) {
      if (error.response && error.response.status === 204) {
        this.setState({
          loading: false,
          hasError: true,
          errorMessage: "Statistics for the user have not been calculated",
        });
      } else {
        this.setState(() => {
          throw error;
        });
      }
    }
    return {} as UserDailyActivityResponse;
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

  processData = (data: UserDailyActivityResponse): UserDailyActivityData => {
    const weekdays = [
      "Monday",
      "Tuesday",
      "Wednesday",
      "Thursday",
      "Friday",
      "Saturday",
      "Sunday",
    ];

    const result: UserDailyActivityData = weekdays.map((day: string) => {
      return {
        id: day,
        data: [],
      };
    });

    data.payload.daily_activity.forEach((elem) => {
      const { day, hour, listen_count: listenCount } = elem;

      const index = weekdays.indexOf(day);
      result[index].data.push({ x: hour, y: listenCount });
    });

    // Fill in gaps in the data
    result.forEach((elem) => {
      const dataWithZeroHours = [];
      for (let i = 0; i < 24; i += 1) {
        const index = elem.data.findIndex((hourData) => hourData.x === i);

        if (index < 0) {
          dataWithZeroHours.push({
            x: i,
            y: 0,
          });
        } else {
          dataWithZeroHours.push(elem.data[index]);
        }
      }

      // eslint-disable-next-line no-param-reassign
      elem.data = dataWithZeroHours;
    });

    return result;
  };

  render() {
    const { data, loading, hasError, errorMessage } = this.state;

    return (
      <Card style={{ minHeight: 400, marginTop: 20 }}>
        <div className="row">
          <div className="col-xs-12">
            <h3 className="capitalize-bold" style={{ marginLeft: 20 }}>
              Daily Activity
            </h3>
          </div>
        </div>
        <Loader
          isLoading={loading}
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            minHeight: "inherit",
          }}
        >
          {hasError && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                minHeight: "inherit",
              }}
            >
              <span style={{ fontSize: 24 }}>
                <FontAwesomeIcon icon={faExclamationCircle as IconProp} />{" "}
                {errorMessage}
              </span>
            </div>
          )}
          {!hasError && (
            <div className="row">
              <div className="col-xs-12" style={{ height: 350 }}>
                <Line data={data} />
              </div>
            </div>
          )}
        </Loader>
      </Card>
    );
  }
}
