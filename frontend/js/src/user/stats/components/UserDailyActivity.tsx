import * as React from "react";
import { faExclamationCircle, faLink } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";

import { useQuery } from "@tanstack/react-query";
import Card from "../../../components/Card";
import HeatMap from "./HeatMap";
import Loader from "../../../components/Loader";
import { COLOR_BLACK } from "../../../utils/constants";
import GlobalAppContext from "../../../utils/GlobalAppContext";

export type UserDailyActivityProps = {
  range: UserStatsAPIRange;
  user: ListenBrainzUser;
};

export type UserDailyActivityState = {
  data: UserDailyActivityData;
  loading: boolean;
  errorMessage: string;
  hasError: boolean;
};

export default function UserDailyActivity(props: UserDailyActivityProps) {
  const { APIService } = React.useContext(GlobalAppContext);

  // Props
  const { range, user } = props;

  // Load the Data
  const { data: loaderData, isLoading: loading } = useQuery({
    queryKey: ["userDailyActivity", user.name, range],
    queryFn: async () => {
      try {
        const queryData = await APIService.getUserDailyActivity(
          user.name,
          range
        );
        return {
          data: queryData,
          hasError: false,
          errorMessage: "",
        };
      } catch (error) {
        return {
          data: {} as UserDailyActivityResponse,
          hasError: true,
          errorMessage: error.message,
        };
      }
    },
  });

  const {
    data: rawData = {} as UserDailyActivityResponse,
    hasError = false,
    errorMessage = "",
  } = loaderData || {};

  const processData = (
    unProcessedData: UserDailyActivityResponse
  ): UserDailyActivityData => {
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
    if (!unProcessedData?.payload) {
      return result;
    }

    const tzOffset = -Math.floor(new Date().getTimezoneOffset() / 60);

    weekdays.forEach((day) => {
      const dayData = unProcessedData.payload.daily_activity[day];
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
    Object.values(unProcessedData.payload.daily_activity).forEach((dayData) => {
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

  const [data, setData] = React.useState<UserDailyActivityData>([]);
  React.useEffect(() => {
    if (rawData && rawData?.payload) {
      setData(processData(rawData));
    }
  }, [rawData]);

  return (
    <Card className="user-stats-card" data-testid="user-daily-activity">
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
