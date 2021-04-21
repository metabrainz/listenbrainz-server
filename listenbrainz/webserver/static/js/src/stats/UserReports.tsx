import * as ReactDOM from "react-dom";
import * as React from "react";

import * as Sentry from "@sentry/react";
import ErrorBoundary from "../ErrorBoundary";
import Pill from "../components/Pill";
import UserListeningActivity from "./UserListeningActivity";
import UserTopEntity from "./UserTopEntity";
import UserDailyActivity from "./UserDailyActivity";
import UserArtistMap from "./UserArtistMap";

export type UserReportsProps = {
  user: ListenBrainzUser;
  apiUrl: string;
};

export type UserReportsState = {
  range: UserStatsAPIRange;
};

export default class UserReports extends React.Component<
  UserReportsProps,
  UserReportsState
> {
  constructor(props: UserReportsProps) {
    super(props);

    this.state = {
      range: "" as UserStatsAPIRange,
    };
  }

  componentDidMount() {
    window.addEventListener("popstate", this.syncStateWithURL);

    const range = this.getURLParams();
    window.history.replaceState(
      null,
      "",
      `?range=${range}${window.location.hash}`
    );
    this.syncStateWithURL();
  }

  componentWillUnmount() {
    window.removeEventListener("popstate", this.syncStateWithURL);
  }

  changeRange = (newRange: UserStatsAPIRange): void => {
    this.setURLParams(newRange);
    this.syncStateWithURL();
  };

  syncStateWithURL = async (): Promise<void> => {
    const range = this.getURLParams();
    this.setState({ range });
  };

  getURLParams = (): UserStatsAPIRange => {
    const url = new URL(window.location.href);

    let range: UserStatsAPIRange = "week";
    if (url.searchParams.get("range")) {
      range = url.searchParams.get("range") as UserStatsAPIRange;
    }

    return range;
  };

  setURLParams = (range: UserStatsAPIRange): void => {
    window.history.pushState(null, "", `?range=${range}`);
  };

  render() {
    const { range } = this.state;
    const { apiUrl, user } = this.props;

    return (
      <div>
        <div className="row mt-15">
          <div className="col-xs-12">
            <Pill
              active={range === "week"}
              type="secondary"
              onClick={() => this.changeRange("week")}
            >
              Week
            </Pill>
            <Pill
              active={range === "month"}
              type="secondary"
              onClick={() => this.changeRange("month")}
            >
              Month
            </Pill>
            <Pill
              active={range === "year"}
              type="secondary"
              onClick={() => this.changeRange("year")}
            >
              Year
            </Pill>
            <Pill
              active={range === "all_time"}
              type="secondary"
              onClick={() => this.changeRange("all_time")}
            >
              All Time
            </Pill>
          </div>
        </div>
        <section id="listening-activity">
          <ErrorBoundary>
            <UserListeningActivity range={range} apiUrl={apiUrl} user={user} />
          </ErrorBoundary>
        </section>
        <section id="top-entity">
          <div className="row">
            <div className="col-md-4">
              <ErrorBoundary>
                <UserTopEntity
                  range={range}
                  entity="artist"
                  apiUrl={apiUrl}
                  user={user}
                />
              </ErrorBoundary>
            </div>
            <div className="col-md-4">
              <ErrorBoundary>
                <UserTopEntity
                  range={range}
                  entity="release"
                  apiUrl={apiUrl}
                  user={user}
                />
              </ErrorBoundary>
            </div>
            <div className="col-md-4">
              <ErrorBoundary>
                <UserTopEntity
                  range={range}
                  entity="recording"
                  apiUrl={apiUrl}
                  user={user}
                />
              </ErrorBoundary>
            </div>
          </div>
        </section>
        <section id="daily-activity">
          <ErrorBoundary>
            <UserDailyActivity range={range} apiUrl={apiUrl} user={user} />
          </ErrorBoundary>
        </section>
        <section id="artist-origin">
          <ErrorBoundary>
            <UserArtistMap range={range} apiUrl={apiUrl} user={user} />
          </ErrorBoundary>
        </section>
      </div>
    );
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const domContainer = document.querySelector("#react-container");
  const propsElement = document.getElementById("react-props");
  let reactProps;
  try {
    reactProps = JSON.parse(propsElement!.innerHTML);
  } catch (err) {
    // Show error to the user and ask to reload page
  }
  const { user, api_url: apiUrl, sentry_dsn } = reactProps;

  if (sentry_dsn) {
    Sentry.init({ dsn: sentry_dsn });
  }

  ReactDOM.render(
    <ErrorBoundary>
      <UserReports apiUrl={apiUrl} user={user} />
    </ErrorBoundary>,
    domContainer
  );
});
