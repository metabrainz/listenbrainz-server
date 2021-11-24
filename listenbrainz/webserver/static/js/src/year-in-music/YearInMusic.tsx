/* eslint-disable jsx-a11y/anchor-is-valid */

import * as ReactDOM from "react-dom";
import * as React from "react";
import { get, has } from "lodash";
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
import ListenCard from "../listens/ListenCard";
import Card from "../components/Card";

export type YearInMusicProps = {
  user: ListenBrainzUser;
} & WithAlertNotificationsInjectedProps;

export type YearInMusicState = {
  colorReleases: Array<ColorReleaseItem>;
  loading: boolean;
  selectedRelease?: ColorReleaseItem;
  selectedColorString?: string;
  gridBackground: string;
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
      colorReleases: [],
      loading: false,
      gridBackground: "#FFFFFF",
    };
  }

  render() {
    const { user, newAlert } = this.props;
    const {
      loading,
      colorReleases,
      selectedRelease,
      gridBackground,
    } = this.state;
    const { APIService, currentUser } = this.context;
    const selectedReleaseTracks = selectedRelease?.recordings ?? [];
    return (
      <div role="main">
        <div>
          <h1 className="text-center">
            Huesound<span className="beta">beta</span>
          </h1>
          <div className="row huesound-container">
            <div className="colour-picker-container">
              {colorReleases.length === 0 && (
                <h2 className="text-center">cover art music discovery</h2>
              )}

              {colorReleases.length === 0 && (
                <h2 className="text-center">
                  Choose a color
                  <br />
                  on the wheel!
                </h2>
              )}
              {colorReleases.length > 0 && !selectedRelease && (
                <h2 className="text-center">
                  Click an album cover to start playing!
                </h2>
              )}
            </div>
            <div
              className={`cover-art-grid ${
                !colorReleases?.length ? "invisible" : ""
              }`}
              style={{ backgroundColor: gridBackground }}
            >
              {colorReleases?.map((release, index) => {
                return (
                  <button
                    key={`${release.release_mbid}-${index}`}
                    type="button"
                    className="cover-art-container"
                  >
                    <img
                      src={`https://archive.org/download/mbid-${release.release_mbid}/mbid-${release.release_mbid}-${release.caa_id}_thumb250.jpg`}
                      alt={`Cover art for Release ${release.release_name}`}
                      height={150}
                    />
                  </button>
                );
              })}
            </div>
          </div>

          {colorReleases.length > 0 && <Loader isLoading={loading} />}
          {selectedRelease && (
            <div className="row align-items-center">
              <div className="col-md-8" style={{ marginTop: "3em" }}>
                <Card style={{ display: "flex" }}>
                  <img
                    className="img-rounded"
                    style={{ flex: 1 }}
                    src={`https://archive.org/download/mbid-${selectedRelease.release_mbid}/mbid-${selectedRelease.release_mbid}-${selectedRelease.caa_id}_thumb250.jpg`}
                    alt={`Cover art for Release ${selectedRelease.release_name}`}
                    width={200}
                    height={200}
                  />
                  <div style={{ flex: 3, padding: "0.5em 2em" }}>
                    <div className="h3">
                      <a
                        href={`https://musicbrainz.org/release/${selectedRelease.release_mbid}`}
                      >
                        {selectedRelease.release_name}
                      </a>
                    </div>
                    <div className="h4">
                      {has(
                        selectedRelease,
                        "recordings[0].track_metadata.additional_info.artist_mbids[0]"
                      ) ? (
                        <a
                          href={`https://musicbrainz.org/artist/${get(
                            selectedRelease,
                            "recordings[0].track_metadata.additional_info.artist_mbids[0]"
                          )}`}
                        >
                          {selectedRelease.artist_name}
                        </a>
                      ) : (
                        selectedRelease.artist_name
                      )}
                    </div>
                  </div>
                </Card>
                <div style={{ padding: "2em" }}>
                  {selectedRelease.recordings?.map(
                    (recording: BaseListenFormat) => {
                      return (
                        <ListenCard
                          listen={recording}
                          currentFeedback={0}
                          showTimestamp={false}
                          showUsername={false}
                          newAlert={newAlert}
                        />
                      );
                    }
                  )}
                </div>
              </div>
              <div className="col-md-4 sticky-top">
                <BrainzPlayer
                  newAlert={newAlert}
                  listens={selectedReleaseTracks}
                  listenBrainzAPIBaseURI={APIService.APIBaseURI}
                  refreshSpotifyToken={APIService.refreshSpotifyToken}
                  refreshYoutubeToken={APIService.refreshYoutubeToken}
                />
              </div>
            </div>
          )}
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
