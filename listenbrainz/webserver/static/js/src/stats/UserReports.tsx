import * as ReactDOM from "react-dom";
import * as React from "react";

import * as Sentry from "@sentry/react";
import { Integrations } from "@sentry/tracing";
import ErrorBoundary from "../utils/ErrorBoundary";
import Pill from "../components/Pill";
import UserListeningActivity from "./UserListeningActivity";
import UserTopEntity from "./UserTopEntity";
import UserDailyActivity from "./UserDailyActivity";
import UserArtistMap from "./UserArtistMap";
import { getPageProps } from "../utils/utils";
import { getAllStatRanges } from "./utils";

export type UserReportsProps = {
  user?: ListenBrainzUser;
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

    const ranges = getAllStatRanges();
    return (
      <div>
        <div className="row mt-15">
          <div className="col-xs-12">
            {Array.from(ranges, ([stat_type, stat_name]) => {
              return (
                <Pill
                  active={range === stat_type}
                  type="secondary"
                  onClick={() => this.changeRange(stat_type)}
                >
                  {stat_name}
                </Pill>
              );
            })}
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
                  newTerminology="artist"
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
                  newTerminology="album"
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
                  newTerminology="track"
                />
              </ErrorBoundary>
            </div>
          </div>
        </section>
        {user && (
          <section id="daily-activity">
            <ErrorBoundary>
              <UserDailyActivity range={range} apiUrl={apiUrl} user={user} />
            </ErrorBoundary>
          </section>
        )}
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
  const { domContainer, reactProps, globalReactProps } = getPageProps();
  const { api_url, sentry_dsn, sentry_traces_sample_rate } = globalReactProps;
  const { user } = reactProps;

  if (sentry_dsn) {
    Sentry.init({
      dsn: sentry_dsn,
      integrations: [new Integrations.BrowserTracing()],
      tracesSampleRate: sentry_traces_sample_rate,
    });
  }

  ReactDOM.render(
    <ErrorBoundary>
      <UserReports apiUrl={api_url} user={user} />
    </ErrorBoundary>,
    domContainer
  );
});
