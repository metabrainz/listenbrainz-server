/* eslint-disable jsx-a11y/anchor-is-valid */

import * as ReactDOM from "react-dom";
import * as React from "react";
import ErrorBoundary from "../ErrorBoundary";
import GlobalAppContext, { GlobalAppContextT } from "../GlobalAppContext";
import BrainzPlayer from "../BrainzPlayer";
import {
  WithAlertNotificationsInjectedProps,
  withAlertNotifications,
} from "../AlertNotificationsHOC";

import APIServiceClass from "../APIService";
import { getPageProps } from "../utils";
import ComponentToImage from "./ComponentToImage";

export type YearInMusicProps = {
  user: ListenBrainzUser;
} & WithAlertNotificationsInjectedProps;

export type YearInMusicState = {
  loading: boolean;
  selectedRelease?: ColorReleaseItem;
};

export default class YearInMusic extends React.Component<
  YearInMusicProps,
  YearInMusicState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  constructor(props: YearInMusicProps) {
    super(props);
    this.state = {
      loading: false,
    };
  }

  render() {
    const { user, newAlert } = this.props;
    const { loading, selectedRelease } = this.state;
    const { APIService, currentUser } = this.context;
    const selectedReleaseTracks = selectedRelease?.recordings ?? [];
    return (
      <div role="main" id="year-in-music">
        <div className="row">
          <div className="col-sm-4">
            <div className="card">
              Username here
              {user?.name}
            </div>
          </div>
          <div className="col-sm-8">
            <img
              className="header-image"
              src="/static/img/year-in-music-2021.svg"
              alt="Your year in music 2021"
            />
          </div>
          <div className="col-sm-4">
            <div className="card flex-center">
              <h3 className="text-center">Your most active listening day</h3>
              <div>Friday</div>
            </div>
          </div>
          <div className="col-sm-4">
            <div className="card flex-center">
              <h3 className="text-center">Color highlights</h3>
            </div>
          </div>
          <div className="col-sm-4">
            <div className="card flex-center">
              <h3 className="text-center">12345 listens this year</h3>
            </div>
          </div>
          <div className="col-sm-4">
            <div className="card flex-center">
              <h3 className="text-center">Top artists of the year</h3>
            </div>
          </div>
          <div className="col-sm-4">
            <div className="card flex-center">
              <h3 className="text-center">Top albums of the year</h3>
            </div>
          </div>
          <div className="col-sm-4">
            <div className="card flex-center">
              <h3 className="text-center">
                Your top discoveries published this year
              </h3>
            </div>
          </div>
          <div className="col-sm-4">
            <div className="card flex-center">
              <h3 className="text-center">
                New releases from 2021 from my top 50 Artists
              </h3>
            </div>
          </div>
          <div className="col-sm-4">
            <div className="card flex-center">
              <h3 className="text-center">Most similar users this year</h3>
            </div>
          </div>
          <BrainzPlayer
            listens={[]}
            newAlert={newAlert}
            listenBrainzAPIBaseURI={APIService.APIBaseURI}
            refreshSpotifyToken={APIService.refreshSpotifyToken}
            refreshYoutubeToken={APIService.refreshYoutubeToken}
          />
          <ComponentToImage />
        </div>
      </div>
    );
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const { domContainer, reactProps, globalReactProps } = getPageProps();
  const { api_url, current_user, spotify, youtube } = globalReactProps;
  const { user } = reactProps;

  const apiService = new APIServiceClass(
    api_url || `${window.location.origin}/1`
  );

  const YearInMusicWithAlertNotifications = withAlertNotifications(YearInMusic);

  const globalProps: GlobalAppContextT = {
    APIService: apiService,
    currentUser: current_user,
    spotifyAuth: spotify,
    youtubeAuth: youtube,
  };

  ReactDOM.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalProps}>
        <YearInMusicWithAlertNotifications user={user} />
      </GlobalAppContext.Provider>
    </ErrorBoundary>,
    domContainer
  );
});
