import * as React from "react";
import { faExclamationCircle, faLink } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";

import APIService from "../utils/APIService";
import Card from "../components/Card";
import HeatMap from "./HeatMap";
import Loader from "../components/Loader";
import { isInvalidStatRange } from "./utils";
import { COLOR_BLACK } from "../utils/constants";

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
      loading: false,
      errorMessage: "",
      hasError: false,
    };
  }

  componentDidUpdate(prevProps: UserDailyActivityProps) {
    const { range: prevRange, user: prevUser } = prevProps;
    const { range: currRange, user: currUser } = this.props;
    if (prevRange !== currRange || prevUser !== currUser) {
      if (isInvalidStatRange(currRange)) {
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
          errorMessage:
            "There are no statistics available for this user for this period",
        });
      } else {
        throw error;
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

    const result: UserDailyActivityData = [];
    if (!data?.payload) {
      return result;
    }

    const tzOffset = -Math.floor(new Date().getTimezoneOffset() / 60);

    weekdays.forEach((day) => {
      const dayData = data.payload.daily_activity[day];
      let hourData: any = [];

      hourData = dayData.map((elem) => {
        const hour = (elem.hour + tzOffset + 24) % 24;
        return {
          x: hour,
          y: elem.listen_count,
        };
      });

      result.push({
        id: day,
        data: hourData,
      });
    });

    const average = Array(24).fill(0);
    Object.values(data.payload.daily_activity).forEach((dayData) => {
      dayData.forEach((hourData) => {
        average[hourData.hour] += hourData.listen_count;
      });
    });

    let averageData: any = [];
    averageData = average.map((elem, index) => {
      const hour = (index + tzOffset + 24) % 24;
      return {
        x: hour,
        y: Math.ceil(elem / 7),
      };
    });

    result.unshift({
      id: "Average",
      data: averageData,
    });

    return result;
  };

  render() {
    const { data, loading, hasError, errorMessage } = this.state;

    return (
      <Card className="user-stats-card">
        <div className="row">
          <div className="col-xs-10">
            <h3 className="capitalize-bold" style={{ marginLeft: 20 }}>
              Daily Activity
            </h3>
          </div>
          <div className="col-xs-2 text-right">
            <h4 style={{ marginTop: 20 }}>
              <a href="#daily-activity">
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
          {hasError ? (
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
          ) : (
            <div className="row">
              <div className="col-xs-12">
                <HeatMap data={data} />
              </div>
            </div>
          )}
        </Loader>
      </Card>
    );
  }
}
