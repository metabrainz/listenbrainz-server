import * as React from "react";
import { faExclamationCircle, faLink } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";

import APIService from "../APIService";
import Card from "../components/Card";
import HeatMap from "./HeatMap";
import Loader from "../components/Loader";

export type UserDailyActivityProps = {
  range: UserStatsAPIRange;
  user: ListenBrainzUser;
  apiUrl: string;
};

export type UserDailyActivityState = {
  data: UserDailyActivityData;
  loading: boolean;
  graphContainerWidth?: number;
  errorMessage: string;
  hasError: boolean;
};

export default class UserDailyActivity extends React.Component<
  UserDailyActivityProps,
  UserDailyActivityState
> {
  APIService: APIService;

  graphContainer: React.RefObject<HTMLDivElement>;

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

    this.graphContainer = React.createRef();
  }

  componentDidMount() {
    window.addEventListener("resize", this.handleResize);

    this.handleResize();
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

  componentWillUnmount() {
    window.removeEventListener("resize", this.handleResize);
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
      const hourData: any = {};

      dayData.forEach((elem) => {
        const hour = (elem.hour + tzOffset + 24) % 24;
        hourData[hour] = elem.listen_count;
      });

      result.push({
        day,
        ...hourData,
      });
    });

    const average = Array(24).fill(0);
    Object.values(data.payload.daily_activity).forEach((dayData) => {
      dayData.forEach((hourData) => {
        average[hourData.hour] += hourData.listen_count;
      });
    });

    const averageData: any = {};
    average.forEach((elem, index) => {
      const hour = (index + tzOffset + 24) % 24;
      averageData[hour] = Math.ceil(elem / 7);
    });

    result.unshift({
      day: "Average",
      ...averageData,
    });

    return result;
  };

  handleResize = () => {
    this.setState({
      graphContainerWidth: this.graphContainer.current?.offsetWidth,
    });
  };

  render() {
    const {
      data,
      loading,
      graphContainerWidth,
      hasError,
      errorMessage,
    } = this.state;

    return (
      <Card
        style={{
          marginTop: 20,
          minHeight: (graphContainerWidth || 1200) * 0.4,
        }}
        ref={this.graphContainer}
      >
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
                  color="#000000"
                  style={{ marginRight: 20 }}
                />
              </a>
            </h4>
          </div>
        </div>
        <Loader isLoading={loading}>
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
              <div className="col-xs-12">
                {graphContainerWidth && (
                  <HeatMap data={data} width={graphContainerWidth} />
                )}
              </div>
            </div>
          )}
        </Loader>
      </Card>
    );
  }
}
