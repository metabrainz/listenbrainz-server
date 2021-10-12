/* eslint-disable jsx-a11y/anchor-is-valid */

import * as ReactDOM from "react-dom";
import * as React from "react";
import ErrorBoundary from "../ErrorBoundary";
import GlobalAppContext, { GlobalAppContextT } from "../GlobalAppContext";
import {
  WithAlertNotificationsInjectedProps,
  withAlertNotifications,
} from "../AlertNotificationsHOC";

import APIServiceClass from "../APIService";
import BrainzPlayer from "../BrainzPlayer";
import Loader from "../components/Loader";
import { getPageProps } from "../utils";

export type ColorPlayProps = {
  user: ListenBrainzUser;
  tracks: Array<Listen>;
  totalCount: number;
  profileUrl?: string;
} & WithAlertNotificationsInjectedProps;

export type ColorPlayState = {
  direction: BrainzPlayDirection;
  tracks: Array<Listen>;
  page: number;
  maxPage: number;
  loading: boolean;
};

export default class ColorPlay extends React.Component<
  ColorPlayProps,
  ColorPlayState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  private DEFAULT_TRACKS_PER_PAGE = 25;

  constructor(props: ColorPlayProps) {
    super(props);
    const { totalCount } = this.props;
    this.state = {
      maxPage: Math.ceil(totalCount / this.DEFAULT_TRACKS_PER_PAGE),
      tracks: props.tracks || [],
      page: 1,
      loading: false,
      direction: "down",
    };
  }

  async componentDidMount(): Promise<void> {
    // Listen to browser previous/next events and load page accordingly
    window.addEventListener("popstate", this.handleURLChange);
    this.handleURLChange();
  }

  componentWillUnmount() {
    window.removeEventListener("popstate", this.handleURLChange);
  }

  // pagination functions
  handleURLChange = async (): Promise<void> => {
    const { page, maxPage } = this.state;
    const url = new URL(window.location.href);

    if (url.searchParams.get("page")) {
      let newPage = Number(url.searchParams.get("page"));
      if (newPage === page) {
        // page didn't change
        return;
      }
      newPage = Math.max(newPage, 1);
      newPage = Math.min(newPage, maxPage);
    } else if (page !== 1) {
      // occurs on back + forward history
    }
  };

  handleClickOlder = async (event?: React.MouseEvent) => {
    if (event) {
      event.preventDefault();
    }
  };

  handleClickNewer = async (event?: React.MouseEvent) => {
    if (event) {
      event.preventDefault();
    }
  };

  render() {
    const { user, newAlert } = this.props;
    const { tracks, direction, loading } = this.state;
    const { currentUser } = this.context;

    return (
      <div role="main">
        <div className="row">
          <div className="col-md-8">
            <h3>Huesound Color Play</h3>

            {tracks.length === 0 && (
              <>
                <div className="lead text-center">No Tracks found</div>

                {user.name === currentUser.name && <>Click on the wheel</>}
              </>
            )}

            {tracks.length > 0 && <Loader isLoading={loading} />}
          </div>
          <div
            className="col-md-4"
            // @ts-ignore
            // eslint-disable-next-line no-dupe-keys
            style={{ position: "-webkit-sticky", position: "sticky", top: 20 }}
          >
            <BrainzPlayer
              direction={direction}
              newAlert={newAlert}
              listens={tracks}
            />
          </div>
        </div>
      </div>
    );
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const { domContainer, reactProps, globalReactProps } = getPageProps();
  const { api_url, current_user, spotify, youtube } = globalReactProps;
  const { user, tracks, total_count, profile_url } = reactProps;

  const apiService = new APIServiceClass(
    api_url || `${window.location.origin}/1`
  );

  const ColorPlayWithAlertNotifications = withAlertNotifications(ColorPlay);

  const globalProps: GlobalAppContextT = {
    APIService: apiService,
    currentUser: current_user,
    spotifyAuth: spotify,
    youtubeAuth: youtube,
  };

  ReactDOM.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalProps}>
        <ColorPlayWithAlertNotifications
          user={user}
          tracks={tracks}
          totalCount={total_count}
          profileUrl={profile_url}
        />
      </GlobalAppContext.Provider>
    </ErrorBoundary>,
    domContainer
  );
});
