/* eslint-disable jsx-a11y/anchor-is-valid */
/* eslint-disable camelcase */

import * as React from "react";
import { createRoot } from "react-dom/client";

import * as Sentry from "@sentry/react";
import { Integrations } from "@sentry/tracing";
import NiceModal from "@ebay/nice-modal-react";
import { toast, ToastContainer } from "react-toastify";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faChevronLeft,
  faChevronRight,
  faSave,
} from "@fortawesome/free-solid-svg-icons";
import { get, isUndefined, throttle } from "lodash";
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
  getRecordingMBIDFromJSPFTrack,
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
  recordingFeedbackMap: RecordingFeedbackMap;
};

export default class RecommendationsPage extends React.Component<
  RecommendationsPageProps,
  RecommendationsPageState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;
  private scrollContainer: React.RefObject<HTMLDivElement>;

  static getPlaylistInfo(
    playlist: JSPFPlaylist,
    isOld = false
  ): { shortTitle: string; cssClasses: string } {
    const extension = getPlaylistExtension(playlist);
    const sourcePatch =
      extension?.additional_metadata?.algorithm_metadata.source_patch;
    let year;
    switch (sourcePatch) {
      case "weekly-jams":
        return {
          shortTitle: !isOld ? "Weekly Jams" : `Last Week's Jams`,
          cssClasses: "weekly-jams green",
        };
      case "weekly-exploration":
        return {
          shortTitle: !isOld ? "Weekly Exploration" : `Last Week's Exploration`,
          cssClasses: "green",
        };
      case "daily-jams":
        return {
          shortTitle: "Daily Jams",
          cssClasses: "blue",
        };
      case "top-discoveries-for-year":
        // get year from title, fallback to using creationg date minus 1
        year =
          playlist.title.match(/\d{2,4}/)?.[0] ??
          new Date(playlist.date).getUTCFullYear() - 1;
        return {
          shortTitle: `${year} Top Discoveries`,
          cssClasses: "red",
        };
      case "top-missed-recordings-for-year":
        // get year from title, fallback to using creationg date minus 1
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

  throttledOnScroll: React.ReactEventHandler<HTMLDivElement>;

  constructor(props: RecommendationsPageProps) {
    super(props);

    const playlists = props.playlists?.map((pl) => pl.playlist);
    this.state = {
      playlists: playlists ?? [],
      recordingFeedbackMap: {},
      loading: false,
    };
    this.scrollContainer = React.createRef();
    this.throttledOnScroll = throttle(this.onScroll, 400, { leading: true });
  }

  async componentDidMount(): Promise<void> {
    const { playlists } = this.state;
    const selectedPlaylist =
      playlists.find((pl) => {
        const extension = getPlaylistExtension(pl);
        const sourcePatch =
          extension?.additional_metadata?.algorithm_metadata.source_patch;
        return sourcePatch === "weekly-jams";
      }) ?? playlists[0];
    if (selectedPlaylist) {
      const playlistId = getPlaylistId(selectedPlaylist);
      await this.fetchPlaylist(playlistId);
      const recordingFeedbackMap = await this.loadFeedback();
      this.setState({ recordingFeedbackMap });
    }
  }

  getFeedback = async (mbids?: string[]): Promise<FeedbackResponse[]> => {
    const { currentUser, APIService } = this.context;
    const { selectedPlaylist } = this.state;
    if (currentUser && selectedPlaylist?.track) {
      const recordings =
        mbids ?? selectedPlaylist.track.map(getRecordingMBIDFromJSPFTrack);
      try {
        const data = await APIService.getFeedbackForUserForRecordings(
          currentUser.name,
          recordings
        );
        return data.feedback;
      } catch (error) {
        toast.error(
          `Could not get love/hat feedback: ${
            error.message ?? error.toString()
          }`
        );
      }
    }
    return [];
  };

  loadFeedback = async (mbids?: string[]): Promise<RecordingFeedbackMap> => {
    const { recordingFeedbackMap } = this.state;
    const feedback = await this.getFeedback(mbids);
    const newRecordingFeedbackMap: RecordingFeedbackMap = {
      ...recordingFeedbackMap,
    };
    feedback.forEach((fb: FeedbackResponse) => {
      if (fb.recording_mbid) {
        newRecordingFeedbackMap[fb.recording_mbid] = fb.score;
      }
    });
    return newRecordingFeedbackMap;
  };

  updateFeedback = (
    recordingMbid: string,
    score: ListenFeedBack | RecommendationFeedBack
  ) => {
    if (recordingMbid) {
      const { recordingFeedbackMap } = this.state;
      recordingFeedbackMap[recordingMbid] = score as ListenFeedBack;
      this.setState({ recordingFeedbackMap });
    }
  };

  getFeedbackForRecordingMbid = (
    recordingMbid?: string | null
  ): ListenFeedBack => {
    const { recordingFeedbackMap } = this.state;
    return recordingMbid ? get(recordingFeedbackMap, recordingMbid, 0) : 0;
  };

  fetchPlaylist = async (playlistId: string) => {
    const { APIService, currentUser } = this.context;
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

  // The playlist prop only contains generic info, not the actual tracks
  // We need to fetch the playlist to get it in full.
  selectPlaylist: React.ReactEventHandler<HTMLElement> = async (event) => {
    if (!(event?.currentTarget instanceof HTMLElement)) {
      return;
    }
    if (
      event.currentTarget.closest(".dragscroll")?.classList.contains("dragging")
    ) {
      // We are dragging with the dragscroll library, ignore the click
      event.preventDefault();
      return;
    }
    const { playlistId } = event.currentTarget.dataset;
    if (!playlistId) {
      toast.error("No playlist to select");
      return;
    }
    await this.fetchPlaylist(playlistId);
  };

  copyPlaylist: React.ReactEventHandler<HTMLElement> = async (event) => {
    if (!(event?.currentTarget instanceof HTMLElement)) {
      return;
    }
    event?.stopPropagation();
    if (
      event.currentTarget.closest(".dragscroll")?.classList.contains("dragging")
    ) {
      // We are dragging with the dragscroll library, ignore the click
      event.preventDefault();
      return;
    }
    const { APIService, currentUser } = this.context;
    const playlistId = event.currentTarget?.parentElement?.dataset?.playlistId;

    if (!currentUser?.auth_token) {
      toast.warning("You must be logged in to save playlists");
      return;
    }
    if (!playlistId) {
      toast.error("No playlist to copy");
      return;
    }
    try {
      const newPlaylistId = await APIService.copyPlaylist(
        currentUser.auth_token,
        playlistId
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
    const { user } = this.props;
    const { selectedPlaylist } = this.state;
    const isLoggedIn = Boolean(currentUser?.auth_token);
    const isCurrentUser = user.name === currentUser?.name;
    const playlistId = getPlaylistId(playlist);
    return (
      <button
        className={`${
          selectedPlaylist?.identifier === playlist.identifier ? "selected" : ""
        } ${cssClasses}`}
        onClick={this.selectPlaylist}
        type="button"
        data-playlist-id={playlistId}
      >
        <div className="title">{shortTitle ?? playlist.title}</div>
        {isLoggedIn && (
          <button
            type="button"
            className="btn btn-info btn-rounded btn-sm"
            onClick={this.copyPlaylist}
          >
            <FontAwesomeIcon icon={faSave} title="Save to my playlists" />{" "}
            {isCurrentUser ? "Save" : "Duplicate"}
          </button>
        )}
      </button>
    );
  };

  onScroll: React.ReactEventHandler<HTMLDivElement> = (event) => {
    const element = event.target as HTMLDivElement;
    const parent = element.parentElement;
    if (!element || !parent) {
      return;
    }
    // calculate horizontal scroll percentage
    const scrollPercentage =
      (100 * element.scrollLeft) / (element.scrollWidth - element.clientWidth);

    if (scrollPercentage > 95) {
      parent.classList.add("scroll-end");
      parent.classList.remove("scroll-start");
    } else if (scrollPercentage < 5) {
      parent.classList.add("scroll-start");
      parent.classList.remove("scroll-end");
    } else {
      parent.classList.remove("scroll-end");
      parent.classList.remove("scroll-start");
    }
  };

  manualScroll: React.ReactEventHandler<HTMLElement> = (event) => {
    if (!this.scrollContainer?.current) {
      return;
    }
    if (event?.currentTarget.classList.contains("forward")) {
      this.scrollContainer.current.scrollBy({
        left: 300,
        top: 0,
        behavior: "smooth",
      });
    } else {
      this.scrollContainer.current.scrollBy({
        left: -300,
        top: 0,
        behavior: "smooth",
      });
    }
  };

  render() {
    const { user, newAlert } = this.props;
    const { currentUser, APIService } = this.context;
    const { playlists, selectedPlaylist, loading } = this.state;

    const listensFromJSPFTracks =
      selectedPlaylist?.track.map(JSPFTrackToListen) ?? [];
    return (
      <div id="recommendations">
        <h3>Created for {user.name}</h3>

        <Loader isLoading={loading} />
        {!playlists.length ? (
          <div className="text-center">
            <img
              src="/static/img/recommendations/no-freshness.png"
              alt="No recommendations to show"
            />
            <p className="hidden">
              Oh no. Either something’s gone wrong, or you need to submit more
              listens before we can prepare delicious fresh produce just for
              you.
            </p>
          </div>
        ) : (
          <div className="playlists-masonry-container scroll-start">
            <button
              className="nav-button backward"
              type="button"
              onClick={this.manualScroll}
            >
              <FontAwesomeIcon icon={faChevronLeft} />
            </button>
            <div
              className="playlists-masonry dragscroll"
              onScroll={this.throttledOnScroll}
              ref={this.scrollContainer}
            >
              {playlists.map((playlist, index) => {
                const extension = getPlaylistExtension(playlist);
                const sourcePatch =
                  extension?.additional_metadata?.algorithm_metadata
                    .source_patch;
                const isFirstOfType =
                  playlists.findIndex((pl) => {
                    const extension2 = getPlaylistExtension(pl);
                    const sourcePatch2 =
                      extension2?.additional_metadata?.algorithm_metadata
                        .source_patch;
                    return sourcePatch === sourcePatch2;
                  }) === index;

                const info = RecommendationsPage.getPlaylistInfo(
                  playlist,
                  !isFirstOfType
                );
                return this.getPlaylistCard(playlist, info);
              })}
            </div>
            <button
              className="nav-button forward"
              type="button"
              onClick={this.manualScroll}
            >
              <FontAwesomeIcon icon={faChevronRight} />
            </button>
          </div>
        )}
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
