import { createRoot } from "react-dom/client";
import * as React from "react";

import * as Sentry from "@sentry/react";
import { Integrations } from "@sentry/tracing";
import NiceModal from "@ebay/nice-modal-react";
import { faGlobe, faUser } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import ErrorBoundary from "../utils/ErrorBoundary";
import Pill from "../components/Pill";
import UserListeningActivity from "./UserListeningActivity";
import UserTopEntity from "./UserTopEntity";
import UserDailyActivity from "./UserDailyActivity";
import UserArtistMap from "./UserArtistMap";
import { getPageProps } from "../utils/utils";
import { getAllStatRanges } from "./utils";
import {
  WithAlertNotificationsInjectedProps,
  withAlertNotifications,
} from "../notifications/AlertNotificationsHOC";
import GlobalAppContext from "../utils/GlobalAppContext";

export type UserReportsProps = {
  user?: ListenBrainzUser;
  apiUrl: string;
} & WithAlertNotificationsInjectedProps;

export type UserReportsState = {
  range: UserStatsAPIRange;
};

export default class UserReports extends React.Component<
  UserReportsProps,
  UserReportsState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

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
    const { apiUrl, user, newAlert } = this.props;
    const { currentUser } = this.context;

    const ranges = getAllStatRanges();
    let userStatsUrl: string | undefined;
    if (user?.name) {
      userStatsUrl = `${window.location.origin}/user/${user.name}/stats/?range=${range}`;
    } else if (currentUser?.name) {
      userStatsUrl = `${window.location.origin}/user/${currentUser.name}/stats/?range=${range}`;
    }

    const globalStatsUrl = `${window.location.origin}/statistics/?range=${range}`;

    return (
      <div>
        <div className="row mt-15 flex flex-wrap">
          <div style={{ flex: "initial" }}>
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
          <div style={{ flex: "initial", marginLeft: "auto" }}>
            {Boolean(userStatsUrl) && (
              <a
                href={userStatsUrl}
                className={`pill secondary ${user ? "active" : ""}`}
              >
                <FontAwesomeIcon icon={faUser} />{" "}
                {user?.name ?? currentUser?.name}
              </a>
            )}
            <a
              href={globalStatsUrl}
              className={`pill secondary ${!user ? "active" : ""}`}
            >
              <FontAwesomeIcon icon={faGlobe} /> Global
            </a>
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
                  terminology="artist"
                  newAlert={newAlert}
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
                  terminology="album"
                  newAlert={newAlert}
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
                  terminology="track"
                  newAlert={newAlert}
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
  const {
    domContainer,
    reactProps,
    globalAppContext,
    sentryProps,
    optionalAlerts,
  } = getPageProps();
  const { sentry_dsn, sentry_traces_sample_rate } = sentryProps;

  if (sentry_dsn) {
    Sentry.init({
      dsn: sentry_dsn,
      integrations: [new Integrations.BrowserTracing()],
      tracesSampleRate: sentry_traces_sample_rate,
    });
  }
  const { user } = reactProps;
  const UserReportsPageWithAlertNotifications = withAlertNotifications(
    UserReports
  );

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalAppContext}>
        <NiceModal.Provider>
          <UserReportsPageWithAlertNotifications
            apiUrl={globalAppContext.APIService.APIBaseURI}
            user={user}
            initialAlerts={optionalAlerts}
          />
        </NiceModal.Provider>
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});
