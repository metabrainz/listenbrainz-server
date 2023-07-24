/* eslint-disable jsx-a11y/anchor-is-valid,camelcase */

import * as React from "react";
import { createRoot } from "react-dom/client";
import { get } from "lodash";

import { faCog, faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";
import { toast } from "react-toastify";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { sanitize } from "dompurify";
import * as Sentry from "@sentry/react";
import { Integrations } from "@sentry/tracing";
import NiceModal from "@ebay/nice-modal-react";
import withAlertNotifications from "../notifications/AlertNotificationsHOC";
import APIServiceClass from "../utils/APIService";
import GlobalAppContext from "../utils/GlobalAppContext";
import BrainzPlayer from "../brainzplayer/BrainzPlayer";

import {
  MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION,
  PLAYLIST_TRACK_URI_PREFIX,
  getRecordingMBIDFromJSPFTrack,
  JSPFTrackToListen,
} from "../playlists/utils";
import { getPageProps } from "../utils/utils";
import ListenControl from "../listens/ListenControl";
import ListenCard from "../listens/ListenCard";
import ErrorBoundary from "../utils/ErrorBoundary";
import { ToastMsg } from "../notifications/Notifications";

export type PlayerPageProps = {
  playlist: JSPFObject;
};

export interface PlayerPageState {
  playlist: JSPFPlaylist;
  recordingFeedbackMap: RecordingFeedbackMap;
}

export default class PlayerPage extends React.Component<
  PlayerPageProps,
  PlayerPageState
> {
  static contextType = GlobalAppContext;

  static makeJSPFTrack(track: ACRMSearchResult): JSPFTrack {
    return {
      identifier: `${PLAYLIST_TRACK_URI_PREFIX}${track.recording_mbid}`,
      title: track.recording_name,
      creator: track.artist_credit_name,
    };
  }

  declare context: React.ContextType<typeof GlobalAppContext>;
  private APIService!: APIServiceClass;

  constructor(props: PlayerPageProps) {
    super(props);

    // React-SortableJS expects an 'id' attribute and we can't change it, so add it to each object
    // eslint-disable-next-line no-unused-expressions
    props.playlist?.playlist?.track?.forEach(
      (jspfTrack: JSPFTrack, index: number) => {
        // eslint-disable-next-line no-param-reassign
        jspfTrack.id = getRecordingMBIDFromJSPFTrack(jspfTrack);
      }
    );
    this.state = {
      playlist: props.playlist?.playlist || {},
      recordingFeedbackMap: {},
    };
  }

  async componentDidMount(): Promise<void> {
    const { APIService } = this.context;
    this.APIService = APIService;
    const recordingFeedbackMap = await this.loadFeedback();
    this.setState({ recordingFeedbackMap });
  }

  getFeedback = async (mbids?: string[]): Promise<FeedbackResponse[]> => {
    const { currentUser } = this.context;
    const { playlist } = this.state;
    const { track: tracks } = playlist;
    if (currentUser?.name && tracks) {
      const recordings = mbids ?? tracks.map(getRecordingMBIDFromJSPFTrack);
      try {
        const data = await this.APIService.getFeedbackForUserForRecordings(
          currentUser.name,
          recordings,
          []
        );
        return data.feedback;
      } catch (error) {
        toast.error(
          <ToastMsg
            title="Playback error"
            message={typeof error === "object" ? error?.message : error}
          />,
          { toastId: "playback-error" }
        );
      }
    }
    return [];
  };

  getAlbumDetails(): JSX.Element {
    const { playlist } = this.state;
    return (
      <>
        <div>Release date: </div>
        <div>Label:</div>
        <div>Tags:</div>
        <div>Links:</div>
      </>
    );
  }

  savePlaylist = async () => {
    const { currentUser } = this.context;
    if (!currentUser?.auth_token) {
      return;
    }
    const { playlist } = this.props;
    try {
      const newPlaylistId = await this.APIService.createPlaylist(
        currentUser.auth_token,
        playlist
      );
      toast.success(
        <ToastMsg
          title="Created playlist"
          message={
            <div>
              {" "}
              Created a new public
              <a href={`/playlist/${newPlaylistId}`}>instant playlist</a>
            </div>
          }
        />,
        { toastId: "create-playlist-success" }
      );
    } catch (error) {
      toast.error(
        <ToastMsg title="Could not save playlist" message={error.message} />,
        { toastId: "create-playlist-error" }
      );
    }
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
    if (!recordingMbid) {
      return;
    }
    const { recordingFeedbackMap } = this.state;
    recordingFeedbackMap[recordingMbid] = score as ListenFeedBack;
    this.setState({ recordingFeedbackMap });
  };

  getFeedbackForRecordingMbid = (
    recordingMbid?: string | null
  ): ListenFeedBack => {
    const { recordingFeedbackMap } = this.state;
    return recordingMbid ? get(recordingFeedbackMap, recordingMbid, 0) : 0;
  };

  handleError = (error: any) => {
    toast.error(<ToastMsg title="Error" message={error.message} />, {
      toastId: "error",
    });
  };

  getHeader = (): JSX.Element => {
    const { currentUser } = this.context;
    const { playlist } = this.state;
    const { track: tracks } = playlist;
    const releaseLink =
      tracks?.[0]?.extension?.[MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION]
        ?.release_identifier;
    const isPlayerPage = false;
    const showOptionsMenu =
      Boolean(releaseLink) || Boolean(currentUser?.auth_token);
    return (
      <div className="playlist-details row">
        <h1 className="title">
          <div>
            {playlist.title ?? "BrainzPlayer"}
            {showOptionsMenu && (
              <span className="dropdown pull-right">
                <button
                  className="btn btn-info dropdown-toggle"
                  type="button"
                  id="playlistOptionsDropdown"
                  data-toggle="dropdown"
                  aria-haspopup="true"
                  aria-expanded="true"
                >
                  <FontAwesomeIcon icon={faCog as IconProp} title="Options" />
                  &nbsp;Options
                </button>
                <ul
                  className="dropdown-menu dropdown-menu-right"
                  aria-labelledby="playlistOptionsDropdown"
                >
                  {releaseLink && (
                    <li>
                      See on MusicBrainz
                      <ListenControl
                        icon={faExternalLinkAlt}
                        title="Open in MusicBrainz"
                        text="Open in MusicBrainz"
                        link={releaseLink}
                        anchorTagAttributes={{
                          target: "_blank",
                          rel: "noopener noreferrer",
                        }}
                      />
                    </li>
                  )}
                  {currentUser?.auth_token && (
                    <li>
                      <a
                        id="exportPlaylistToSpotify"
                        role="button"
                        href="#"
                        onClick={this.savePlaylist}
                      >
                        Save Playlist
                      </a>
                    </li>
                  )}
                </ul>
              </span>
            )}
          </div>
        </h1>
        <div className="info">
          {tracks?.length && (
            <div>
              {tracks.length} tracks
              {isPlayerPage && (
                <>
                  {" "}
                  — Total duration:{" "}
                  {tracks
                    .filter((track) => Boolean(track?.duration))
                    .reduce(
                      (sum, { duration }) => sum + (duration as number),
                      0
                    )}
                </>
              )}
            </div>
          )}
          {isPlayerPage && this.getAlbumDetails()}
        </div>
        {playlist.annotation && (
          <div
            // Sanitize the HTML string before passing it to dangerouslySetInnerHTML
            // eslint-disable-next-line react/no-danger
            dangerouslySetInnerHTML={{
              __html: sanitize(playlist.annotation),
            }}
          />
        )}
        <hr />
      </div>
    );
  };

  render() {
    const { playlist } = this.state;
    const { APIService } = this.context;

    const { track: tracks } = playlist;
    if (!playlist || !playlist.track) {
      return <div>Nothing to see here.</div>;
    }
    return (
      <div role="main">
        <div className="row">
          <div id="playlist" className="col-md-8">
            {this.getHeader()}
            <div id="listens row">
              {tracks?.map((track: JSPFTrack, index) => {
                const listen = JSPFTrackToListen(track);
                return (
                  <ListenCard
                    key={`${track.id}-${index.toString()}`}
                    listen={listen}
                    currentFeedback={this.getFeedbackForRecordingMbid(track.id)}
                    showTimestamp={false}
                    showUsername={false}
                  />
                );
              })}
            </div>
          </div>
          <BrainzPlayer
            listens={tracks?.map(JSPFTrackToListen)}
            listenBrainzAPIBaseURI={APIService.APIBaseURI}
            refreshSpotifyToken={APIService.refreshSpotifyToken}
            refreshYoutubeToken={APIService.refreshYoutubeToken}
          />
        </div>
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
  const { playlist } = reactProps;

  const PlayerPageWithAlertNotifications = withAlertNotifications(PlayerPage);

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalAppContext}>
        <NiceModal.Provider>
          <PlayerPageWithAlertNotifications playlist={playlist} />
        </NiceModal.Provider>
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});
