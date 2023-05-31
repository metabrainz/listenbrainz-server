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
import {
  getPlaylistExtension,
  getPlaylistId,
  JSPFTrackToListen,
} from "../playlists/utils";
import ListenCard from "../listens/ListenCard";
import RecommendationPlaylistSettings from "./RecommendationPlaylistSettings";
import BrainzPlayer from "../brainzplayer/BrainzPlayer";

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

  static getPlaylistInfo(
    playlist: JSPFPlaylist,
    isOld = false
  ): { shortTitle: string; cssClasses: string } {
    const extension = getPlaylistExtension(playlist);
    const sourcePatch =
      extension?.additional_metadata?.algorithm_metadata.source_patch;
    // get year from title, fallback to using creationg date minus 1
    // Used for "top discoveries 2022" type of playlists
    let year;
    switch (sourcePatch) {
      case "weekly-jams":
        return {
          shortTitle: !isOld ? "Weekly Jams" : `Last Week's Jams`,
          cssClasses: "weekly-jams green",
        };
      case "weekly-new-jams":
        return {
          shortTitle: !isOld ? "Weekly New Jams" : `Last Week's New Jams`,
          cssClasses: "green",
        };
      case "daily-jams":
        return {
          shortTitle: "Daily Jams",
          cssClasses: "green",
        };
      case "top-discoveries-for-year":
        year =
          playlist.title.match(/\d{2,4}/)?.[0] ??
          new Date(playlist.date).getUTCFullYear() - 1;
        return {
          shortTitle: `${year} Top Discoveries`,
          cssClasses: "red",
        };
      case "top-missed-recordings-for-year":
        year =
          playlist.title.match(/\d{2,4}/)?.[0] ??
          new Date(playlist.date).getUTCFullYear() - 1;
        return {
          shortTitle: `${year} Missed Tracks`,
          cssClasses: "red",
        };
      default:
        return {
          shortTitle: playlist.title,
          cssClasses: "blue",
        };
    }
  }

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

  copyPlaylist = async (playlist: JSPFPlaylist): Promise<void> => {
    const { APIService, currentUser } = this.context;

    if (!currentUser?.auth_token) {
      toast.warning("You must be logged in to save playlists");
      return;
    }
    if (!playlist) {
      toast.error("No playlist to copy");
      return;
    }
    try {
      const newPlaylistId = await APIService.copyPlaylist(
        currentUser.auth_token,
        getPlaylistId(playlist)
      );

      toast.success(
        <>
          Duplicated to playlist&ensp;
          <a href={`/playlist/${newPlaylistId}`}>{newPlaylistId}</a>
        </>
      );
    } catch (error) {
      toast.error(error.message ?? error);
    }
  };

  getPlaylistCard = (
    playlist: JSPFPlaylist,
    info: {
      shortTitle: string;
      cssClasses: string;
    }
  ) => {
    const { shortTitle, cssClasses } = info;
    const { currentUser } = this.context;
    const { selectedPlaylist } = this.state;
    const isLoggedIn = Boolean(currentUser?.auth_token);
    return (
      <div
        className={`${
          selectedPlaylist?.identifier === playlist.identifier ? "selected" : ""
        } ${cssClasses}`}
        onClick={this.selectPlaylist.bind(this, playlist)}
        onKeyDown={this.selectPlaylist.bind(this, playlist)}
        role="button"
        tabIndex={0}
      >
        <div className="title">{shortTitle ?? playlist.title}</div>
        {isLoggedIn && (
          <button
            type="button"
            className="btn btn-info btn-rounded btn-sm"
            onClick={this.copyPlaylist.bind(this, playlist)}
          >
            <FontAwesomeIcon icon={faSave} title="Save to my playlists" /> Save
          </button>
        )}
      </div>
    );
  };

  render() {
    const { user, newAlert } = this.props;
    const { currentUser, APIService } = this.context;
    const { playlists, selectedPlaylist, loading } = this.state;

    const weeklyJamsIds = playlists
      .filter((pl) => {
        const extension = getPlaylistExtension(pl);
        return (
          extension?.additional_metadata?.algorithm_metadata.source_patch ===
          "weekly-jams"
        );
      })
      .map((pl) => pl.identifier);

    const listensFromJSPFTracks =
      selectedPlaylist?.track.map(JSPFTrackToListen) ?? [];
    return (
      <div id="recommendations">
        <h3>Created for {user.name}</h3>

        <Loader isLoading={loading} />
        <div className="playlists-masonry">
          {playlists.map((playlist, index) => {
            let isOld = false;
            const extension = getPlaylistExtension(playlist);
            const sourcePatch =
              extension?.additional_metadata?.algorithm_metadata.source_patch;
            // if(sourcePatch === "")
            const firstOfType = playlists.findIndex((pl) => {
              const extension2 = getPlaylistExtension(playlist);
              const sourcePatch2 =
                extension2?.additional_metadata?.algorithm_metadata
                  .source_patch;
              return sourcePatch === sourcePatch2;
            });
            if (firstOfType !== index) {
              isOld = true;
            }
            const info = RecommendationsPage.getPlaylistInfo(playlist, isOld);
            return this.getPlaylistCard(playlist, info);
          })}
        </div>

        {selectedPlaylist && (
          <section id="selected-playlist">
            <div className="playlist-items">
              {selectedPlaylist.track.map((playlistTrack, index) => {
                const listen = listensFromJSPFTracks?.[index];

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
        <BrainzPlayer
          listens={listensFromJSPFTracks}
          listenBrainzAPIBaseURI={APIService.APIBaseURI}
          refreshSpotifyToken={APIService.refreshSpotifyToken}
          refreshYoutubeToken={APIService.refreshYoutubeToken}
        />
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
