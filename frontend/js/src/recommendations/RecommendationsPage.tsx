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
import { get, isUndefined, set, throttle } from "lodash";
import { ReactSortable } from "react-sortablejs";
import withAlertNotifications from "../notifications/AlertNotificationsHOC";
import GlobalAppContext from "../utils/GlobalAppContext";
import Loader from "../components/Loader";
import ErrorBoundary from "../utils/ErrorBoundary";
import { getPageProps, preciseTimestamp } from "../utils/utils";
import {
  getPlaylistExtension,
  getPlaylistId,
  getRecordingMBIDFromJSPFTrack,
  JSPFTrackToListen,
} from "../playlists/utils";
import RecommendationPlaylistSettings from "./RecommendationPlaylistSettings";
import BrainzPlayer from "../brainzplayer/BrainzPlayer";
import PlaylistItemCard from "../playlists/PlaylistItemCard";
import { ToastMsg } from "../notifications/Notifications";

export type RecommendationsPageProps = {
  playlists?: JSPFObject[];
  user: ListenBrainzUser;
};

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
        // get year from title, fallback to using creation date minus 1
        year =
          playlist.title.match(/\d{2,4}/)?.[0] ??
          new Date(playlist.date).getUTCFullYear() - 1;
        return {
          shortTitle: `${year} Top Discoveries`,
          cssClasses: "red",
        };
      case "top-missed-recordings-for-year":
        // get year from title, fallback to using creation date minus 1
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
    }
  }

  getFeedback = async (mbids?: string[]): Promise<FeedbackResponse[]> => {
    const { currentUser, APIService } = this.context;
    const { selectedPlaylist } = this.state;
    const recordings =
      mbids ?? selectedPlaylist?.track.map(getRecordingMBIDFromJSPFTrack);
    if (currentUser && recordings?.length) {
      try {
        const data = await APIService.getFeedbackForUserForRecordings(
          currentUser.name,
          recordings
        );
        return data.feedback;
      } catch (error) {
        toast.error(
          `Could not get love/hate feedback: ${
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

      // React-SortableJS expects an 'id' attribute (non-negociable), so add it to each object
      JSPFObject.playlist?.track?.forEach((jspfTrack: JSPFTrack) => {
        set(jspfTrack, "id", getRecordingMBIDFromJSPFTrack(jspfTrack));
      });
      // Fetch feedback for loaded tracks
      const newTracksMBIDS = JSPFObject.playlist.track.map(
        getRecordingMBIDFromJSPFTrack
      );
      const recordingFeedbackMap = await this.loadFeedback(newTracksMBIDS);
      this.setState({
        selectedPlaylist: JSPFObject.playlist,
        recordingFeedbackMap,
      });
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

  hasRightToEdit = (): boolean => {
    const { currentUser } = this.context;
    const { user } = this.props;
    return currentUser?.name === user.name;
  };

  movePlaylistItem = async (evt: any) => {
    const { currentUser, APIService } = this.context;
    const { selectedPlaylist } = this.state;
    if (!currentUser?.auth_token) {
      toast.error("You must be logged in to modify this playlist");
      return;
    }
    if (!this.hasRightToEdit()) {
      toast.error("You are not authorized to modify this playlist");
      return;
    }
    try {
      await APIService.movePlaylistItem(
        currentUser.auth_token,
        getPlaylistId(selectedPlaylist),
        evt.item.getAttribute("data-recording-mbid"),
        evt.oldIndex,
        evt.newIndex,
        1
      );
    } catch (error) {
      toast.error(error.toString());
      // Revert the move in state.playlist order
      const newTracks = isUndefined(selectedPlaylist)
        ? []
        : [...selectedPlaylist.track];
      // The ol' switcheroo !
      const toMoveBack = newTracks[evt.newIndex];
      newTracks[evt.newIndex] = newTracks[evt.oldIndex];
      newTracks[evt.oldIndex] = toMoveBack;

      this.setState((prevState) => ({
        selectedPlaylist: { ...prevState.selectedPlaylist!, track: newTracks },
      }));
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
    const extension = getPlaylistExtension(playlist);
    const expiryDate = extension?.additional_metadata?.expires_at;
    let percentTimeLeft;
    if (expiryDate) {
      const start = new Date(playlist.date).getTime();
      const end = new Date(expiryDate).getTime();
      const today = new Date().getTime();

      const elapsed = Math.abs(today - start);
      const total = Math.abs(end - start);
      percentTimeLeft = Math.round((elapsed / total) * 100);
    }
    return (
      <div
        key={playlist.identifier}
        className={`${
          selectedPlaylist?.identifier === playlist.identifier ? "selected" : ""
        } ${cssClasses}`}
        onClick={this.selectPlaylist}
        onKeyDown={(event) => {
          if (["Enter", " "].includes(event.key)) this.selectPlaylist(event);
        }}
        data-playlist-id={playlistId}
        role="button"
        tabIndex={0}
      >
        {!isUndefined(percentTimeLeft) && (
          <div
            className={`playlist-timer ${
              percentTimeLeft > 75 ? "pressing" : ""
            }`}
            title={`Deleted in ${preciseTimestamp(expiryDate!, "timeAgo")}`}
            style={{
              ["--degrees-progress" as any]: `${
                (percentTimeLeft / 100) * 360
              }deg`,
            }}
          />
        )}
        <div className="title">{shortTitle ?? playlist.title}</div>
        {isLoggedIn && (
          <button
            type="button"
            className="btn btn-info btn-rounded btn-sm"
            onClick={this.copyPlaylist}
          >
            <FontAwesomeIcon icon={faSave} title="Save to my playlists" />
            <span className="button-text">
              {" "}
              {isCurrentUser ? "Save" : "Duplicate"}
            </span>
          </button>
        )}
      </div>
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
    const { currentUser, APIService } = this.context;
    const { playlists, selectedPlaylist, loading } = this.state;
    const { user } = this.props;

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
              {selectedPlaylist.track.length > 0 ? (
                <ReactSortable
                  handle=".drag-handle"
                  list={
                    selectedPlaylist.track as (JSPFTrack & { id: string })[]
                  }
                  onEnd={this.movePlaylistItem}
                  setList={(newState) =>
                    this.setState((prevState) => ({
                      selectedPlaylist: {
                        ...prevState.selectedPlaylist!,
                        track: newState,
                      },
                    }))
                  }
                >
                  {selectedPlaylist.track.map((track: JSPFTrack, index) => {
                    return (
                      <PlaylistItemCard
                        key={`${track.id}-${index.toString()}`}
                        canEdit={this.hasRightToEdit()}
                        track={track}
                        currentFeedback={this.getFeedbackForRecordingMbid(
                          track.id
                        )}
                        showTimestamp={false}
                        showUsername={false}
                        // removeTrackFromPlaylist={this.deletePlaylistItem}
                        updateFeedbackCallback={this.updateFeedback}
                      />
                    );
                  })}
                </ReactSortable>
              ) : (
                <div className="lead text-center">
                  <p>Nothing in this playlist yet</p>
                </div>
              )}
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
            playlists={playlists}
            user={user}
          />
        </NiceModal.Provider>
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});
