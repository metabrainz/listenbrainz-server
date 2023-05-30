/* eslint-disable jsx-a11y/anchor-is-valid */
/* eslint-disable camelcase */

import * as React from "react";
import { createRoot } from "react-dom/client";

import * as Sentry from "@sentry/react";
import { Integrations } from "@sentry/tracing";
import NiceModal from "@ebay/nice-modal-react";
import { toast, ToastContainer } from "react-toastify";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faSave } from "@fortawesome/free-solid-svg-icons";
import {
  withAlertNotifications,
  WithAlertNotificationsInjectedProps,
} from "../notifications/AlertNotificationsHOC";
import GlobalAppContext from "../utils/GlobalAppContext";
import Loader from "../components/Loader";
import ErrorBoundary from "../utils/ErrorBoundary";
import { getPageProps } from "../utils/utils";
import { getPlaylistId, JSPFTrackToListen } from "../playlists/utils";
import ListenCard from "../listens/ListenCard";
import RecommendationPlaylistSettings from "./RecommendationPlaylistSettings";

export type RecommendationsPageProps = {
  playlists?: JSPFObject[];
  user: ListenBrainzUser;
} & WithAlertNotificationsInjectedProps;

export type RecommendationsPageState = {
  playlists: JSPFPlaylist[];
  selectedPlaylist?: JSPFPlaylist;
  loading: boolean;
};

export default class RecommendationsPage extends React.Component<
  RecommendationsPageProps,
  RecommendationsPageState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  constructor(props: RecommendationsPageProps) {
    super(props);

    const concatenatedPlaylists = props.playlists?.map((pl) => pl.playlist);
    this.state = {
      playlists: concatenatedPlaylists ?? [],
      loading: false,
    };
  }

  selectPlaylist = async (playlist: JSPFPlaylist) => {
    // The playlist prop only contains generic info, not the actual tracks
    // We need to fetch the playlist to get it in full.
    // Perhaps this should be revisited and we can send the full palylists directly.
    const { APIService, currentUser } = this.context;
    const playlistId = getPlaylistId(playlist);
    try {
      const response = await APIService.getPlaylist(
        playlistId,
        currentUser?.auth_token
      );
      const JSPFObject: JSPFObject = await response.json();
      this.setState({ selectedPlaylist: JSPFObject.playlist });
    } catch (error) {
      toast.error(error.message);
    }
  };

  render() {
    const { user, newAlert } = this.props;
    const { currentUser } = this.context;
    const { playlists, selectedPlaylist, loading } = this.state;
    const isLoggedIn = Boolean(currentUser?.auth_token);
    const [weeklyJams, ...otherPlaylists] = playlists;
    return (
      <div id="recommendations">
        <h3>Created for {user.name}</h3>

        <Loader isLoading={loading} />
        <div className="playlists-masonry">
          {weeklyJams && (
            <div
              className={`weekly-jams ${
                selectedPlaylist?.identifier === weeklyJams.identifier
                  ? "selected"
                  : ""
              }`}
              onClick={this.selectPlaylist.bind(this, weeklyJams)}
              onKeyDown={this.selectPlaylist.bind(this, weeklyJams)}
              role="button"
              tabIndex={0}
            >
              <div className="title">Weekly Jams</div>
              {isLoggedIn && (
                <div className="btn btn-info btn-rounded">
                  <FontAwesomeIcon icon={faSave} title="Save to my playlists" />{" "}
                  Save
                </div>
              )}
            </div>
          )}
          {otherPlaylists.map((playlist) => {
            return (
              <div
                className={`${
                  selectedPlaylist?.identifier === playlist.identifier
                    ? "selected"
                    : ""
                }`}
                onClick={this.selectPlaylist.bind(this, playlist)}
                onKeyDown={this.selectPlaylist.bind(this, playlist)}
                role="button"
                tabIndex={0}
              >
                <div className="title">{playlist.title}</div>
                {isLoggedIn && (
                  <div className="btn btn-info btn-rounded btn-sm">
                    <FontAwesomeIcon
                      icon={faSave}
                      title="Save to my playlists"
                    />
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {selectedPlaylist && (
          <section id="selected-playlist">
            <div className="playlist-items">
              {selectedPlaylist.track.map((playlistTrack) => {
                const listen = JSPFTrackToListen(playlistTrack);

                return (
                  <ListenCard
                    key={playlistTrack.identifier}
                    className="playlist-item-card"
                    listen={listen}
                    showTimestamp={false}
                    showUsername={false}
                    newAlert={newAlert}
                  />
                );
              })}
            </div>
            <RecommendationPlaylistSettings playlist={selectedPlaylist} />
          </section>
        )}
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
  const { playlists, user } = reactProps;

  const RecommendationsPageWithAlertNotifications = withAlertNotifications(
    RecommendationsPage
  );

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <ErrorBoundary>
      <ToastContainer
        position="bottom-right"
        autoClose={8000}
        hideProgressBar
      />
      <GlobalAppContext.Provider value={globalAppContext}>
        <NiceModal.Provider>
          <RecommendationsPageWithAlertNotifications
            initialAlerts={optionalAlerts}
            playlists={playlists}
            user={user}
          />
        </NiceModal.Provider>
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});
