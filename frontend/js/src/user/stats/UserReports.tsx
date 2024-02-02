import * as React from "react";

import {
  faGlobe,
  faInfoCircle,
  faUser,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { useLoaderData } from "react-router-dom";
import ErrorBoundary from "../../utils/ErrorBoundary";
import Pill from "../../components/Pill";
import UserListeningActivity from "./components/UserListeningActivity";
import UserTopEntity from "./components/UserTopEntity";
import UserDailyActivity from "./components/UserDailyActivity";
import UserArtistMap from "./components/UserArtistMap";
import { getAllStatRanges } from "./utils";
import GlobalAppContext from "../../utils/GlobalAppContext";

export type UserReportsProps = {
  user?: ListenBrainzUser;
  apiUrl: string;
};

export type UserReportsState = {
  range: UserStatsAPIRange;
  user?: ListenBrainzUser;
};

type UserReportsLoaderData = UserReportsProps;

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
      user: props.user,
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

  setUser(userName?: string) {
    if (userName) {
      this.setState({ user: { name: userName } });
    } else {
      this.setState({ user: undefined });
    }
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
    const { range, user } = this.state;
    const { apiUrl } = this.props;
    const { currentUser } = this.context;

    const ranges = getAllStatRanges();
    const userOrLoggedInUser: string | undefined =
      user?.name ?? currentUser?.name;

    return (
      <div>
        <div className="tertiary-nav dragscroll">
          <div>
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
          <div>
            {Boolean(userOrLoggedInUser) && (
              <button
                type="button"
                onClick={() => {
                  this.setUser(user?.name ?? currentUser?.name);
                }}
                className={`pill secondary ${user ? "active" : ""}`}
              >
                <FontAwesomeIcon icon={faUser} />{" "}
                {user?.name ?? currentUser?.name}
              </button>
            )}
            <button
              type="button"
              onClick={() => {
                this.setUser();
              }}
              className={`pill secondary ${!user ? "active" : ""}`}
            >
              <FontAwesomeIcon icon={faGlobe} /> Global
            </button>
          </div>
        </div>
        <small>
          <FontAwesomeIcon icon={faInfoCircle} />
          &nbsp;
          <a
            href="https://listenbrainz.readthedocs.io/en/latest/general/data-update-intervals.html"
            target="_blank"
            rel="noopener noreferrer"
          >
            How often are my stats updated?
          </a>
        </small>
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
                />
              </ErrorBoundary>
            </div>
            <div className="col-md-4">
              <ErrorBoundary>
                <UserTopEntity
                  range={range}
                  entity="release-group"
                  apiUrl={apiUrl}
                  user={user}
                  terminology="album"
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

export function UserReportsWrapper() {
  const data = useLoaderData() as UserReportsLoaderData;
  const { APIService } = React.useContext(GlobalAppContext);
  return <UserReports {...data} apiUrl={APIService.APIBaseURI} />;
}

export function StatisticsPage() {
  const { APIService } = React.useContext(GlobalAppContext);
  return <UserReports apiUrl={APIService.APIBaseURI} />;
}

export const UserReportsLoader = async ({ request }: { request: Request }) => {
  const response = await fetch(request.url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  });
  const data = await response.json();
  return { ...data };
};
