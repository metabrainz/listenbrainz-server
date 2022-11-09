import * as React from "react";
import { get as _get, isEqual, isNil, isNumber } from "lodash";
import {
  faMusic,
  faEllipsisV,
  faPlay,
  faCommentDots,
  faExternalLinkAlt,
  faCode,
  faCopy,
} from "@fortawesome/free-solid-svg-icons";
import {
  faSoundcloud,
  faSpotify,
  faYoutube,
} from "@fortawesome/free-brands-svg-icons";
import { faPlayCircle } from "@fortawesome/free-regular-svg-icons";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import hljs from "highlight.js/lib/core";
import json from "highlight.js/lib/languages/json";
import { sanitize } from "dompurify";
import {
  getArtistLink,
  getTrackLink,
  preciseTimestamp,
  fullLocalizedDateFromTimestampOrISODate,
  getRecordingMBID,
  getAlbumArtFromListenMetadata,
  getReleaseMBID,
  getArtistName,
  getTrackName,
  getTrackDurationInMs,
  getRecordingMSID,
} from "../utils/utils";
import GlobalAppContext from "../utils/GlobalAppContext";
import Card from "../components/Card";
import ListenControl from "./ListenControl";
import ListenFeedbackComponent from "./ListenFeedbackComponent";
import YoutubePlayer from "../brainzplayer/YoutubePlayer";
import SpotifyPlayer from "../brainzplayer/SpotifyPlayer";
import SoundcloudPlayer from "../brainzplayer/SoundcloudPlayer";
import { millisecondsToStr } from "../playlists/utils";

hljs.registerLanguage("json", json);

export const DEFAULT_COVER_ART_URL = "/static/img/default_cover_art.png";

export type ListenCardProps = {
  listen: Listen;
  className?: string;
  currentFeedback?: ListenFeedBack | RecommendationFeedBack | null;
  showTimestamp: boolean;
  showUsername: boolean;
  // Only used when not passing a custom feedbackComponent
  updateFeedbackCallback?: (
    recordingMsid: string,
    score: ListenFeedBack | RecommendationFeedBack,
    recordingMbid?: string
  ) => void;
  newAlert: (
    alertType: AlertType,
    title: string,
    message: string | JSX.Element
  ) => void;
  // This show under the first line of listen details. It's meant for reviews, etc.
  additionalContent?: string | JSX.Element;
  // Displays left of the cover art thumbnail. For special items like reorder/grab icon
  beforeThumbnailContent?: JSX.Element;
  // Replaces automatic cover art thumbnail. Also disables loading cover art
  customThumbnail?: JSX.Element;
  // The default details (recording name, artist name) can be replaced
  listenDetails?: JSX.Element;
  // The default timestamp can be replaced
  customTimestamp?: JSX.Element;
  compact?: boolean;
  // The default Listen fedback (love/hate) can be replaced
  feedbackComponent?: JSX.Element;
  // These go in the dropdown menu
  additionalMenuItems?: JSX.Element[];
  // This optional JSX element is for a custom icon
  additionalActions?: JSX.Element;
};

type ListenCardState = {
  isCurrentlyPlaying: boolean;
  thumbnailSrc?: string; // Full URL to the CoverArtArchive thumbnail
};

export default class ListenCard extends React.Component<
  ListenCardProps,
  ListenCardState
> {
  static defaultThumbnailSrc: string = "/static/img/cover-art-placeholder.jpg";
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  constructor(props: ListenCardProps) {
    super(props);

    this.state = {
      isCurrentlyPlaying: false,
    };
  }

  async componentDidMount() {
    window.addEventListener("message", this.receiveBrainzPlayerMessage);
    await this.getCoverArt();
  }

  async componentDidUpdate(oldProps: ListenCardProps) {
    const { listen, customThumbnail } = this.props;
    if (
      !customThumbnail &&
      Boolean(listen) &&
      !isEqual(listen, oldProps.listen)
    ) {
      await this.getCoverArt();
    }
  }

  componentWillUnmount() {
    window.removeEventListener("message", this.receiveBrainzPlayerMessage);
  }

  async getCoverArt() {
    const { spotifyAuth } = this.context;
    const { listen } = this.props;
    const albumArtSrc = await getAlbumArtFromListenMetadata(
      listen,
      spotifyAuth
    );
    if (albumArtSrc) {
      this.setState({ thumbnailSrc: albumArtSrc });
    }
  }

  playListen = () => {
    const { listen } = this.props;
    const { isCurrentlyPlaying } = this.state;
    if (isCurrentlyPlaying) {
      return;
    }
    window.postMessage(
      { brainzplayer_event: "play-listen", payload: listen },
      window.location.origin
    );
  };

  /** React to events sent by BrainzPlayer */
  receiveBrainzPlayerMessage = (event: MessageEvent) => {
    if (event.origin !== window.location.origin) {
      // Received postMessage from different origin, ignoring it
      return;
    }
    const { brainzplayer_event, payload } = event.data;
    switch (brainzplayer_event) {
      case "current-listen-change":
        this.onCurrentListenChange(payload);
        break;
      default:
      // do nothing
    }
  };

  onCurrentListenChange = (newListen: BaseListenFormat) => {
    this.setState({ isCurrentlyPlaying: this.isCurrentlyPlaying(newListen) });
  };

  isCurrentlyPlaying = (element: BaseListenFormat): boolean => {
    const { listen } = this.props;
    if (isNil(listen)) {
      return false;
    }
    return isEqual(element, listen);
  };

  recommendListenToFollowers = async () => {
    const { listen, newAlert } = this.props;
    const { APIService, currentUser } = this.context;

    if (currentUser?.auth_token) {
      const metadata: UserTrackRecommendationMetadata = {
        artist_name: getArtistName(listen),
        track_name: getTrackName(listen),
        release_name: _get(listen, "track_metadata.release_name"),
      };

      const recording_mbid = getRecordingMBID(listen);
      if (recording_mbid) {
        metadata.recording_mbid = recording_mbid;
      }

      const recording_msid = getRecordingMSID(listen);
      if (recording_msid) {
        metadata.recording_msid = recording_msid;
      }

      try {
        const status = await APIService.recommendTrackToFollowers(
          currentUser.name,
          currentUser.auth_token,
          metadata
        );
        if (status === 200) {
          newAlert(
            "success",
            `You recommended a track to your followers!`,
            `${metadata.artist_name} - ${metadata.track_name}`
          );
        }
      } catch (error) {
        this.handleError(
          error,
          "We encountered an error when trying to recommend the track to your followers"
        );
      }
    }
  };

  handleError = (error: string | Error, title?: string): void => {
    const { newAlert } = this.props;
    if (!error) {
      return;
    }
    newAlert(
      "danger",
      title || "Error",
      typeof error === "object" ? error.message : error
    );
  };

  render() {
    const {
      additionalContent,
      beforeThumbnailContent,
      customThumbnail,
      listen,
      className,
      showUsername,
      showTimestamp,
      listenDetails,
      customTimestamp,
      compact,
      feedbackComponent,
      additionalMenuItems,
      currentFeedback,
      newAlert,
      updateFeedbackCallback,
      ...otherProps
    } = this.props;
    const { isCurrentlyPlaying, thumbnailSrc } = this.state;
    const { additionalActions } = this.props;
    const { modal } = this.context;

    const recordingMSID = getRecordingMSID(listen);
    const recordingMBID = getRecordingMBID(listen);
    const releaseMBID = getReleaseMBID(listen);
    const spotifyURL = SpotifyPlayer.getSpotifyURLFromListen(listen);
    const youtubeURL = YoutubePlayer.getYoutubeURLFromListen(listen);
    const soundcloudURL = SoundcloudPlayer.getSoundcloudURLFromListen(listen);

    const trackName = getTrackName(listen);
    const artistName = getArtistName(listen);
    const trackDurationMs = getTrackDurationInMs(listen);

    const hasRecordingMSID = Boolean(recordingMSID);
    const hasRecordingMBID = Boolean(recordingMBID);
    const enableRecommendButton =
      artistName && trackName && (hasRecordingMSID || hasRecordingMBID);

    // Hide the actions menu if in compact mode or no buttons to be shown
    const hasActionOptions =
      additionalMenuItems?.length ||
      enableRecommendButton ||
      recordingMBID ||
      spotifyURL ||
      youtubeURL ||
      soundcloudURL;
    const hideActionsMenu = compact || !hasActionOptions;

    let timeStampForDisplay;
    if (customTimestamp) {
      timeStampForDisplay = customTimestamp;
    } else if (listen.playing_now) {
      timeStampForDisplay = (
        <span className="listen-time">
          <a href="/listening-now/" target="_blank" rel="noopener noreferrer">
            <FontAwesomeIcon icon={faMusic as IconProp} /> Listening now &#8212;
          </a>
        </span>
      );
    } else {
      timeStampForDisplay = (
        <span
          className="listen-time"
          title={
            listen.listened_at
              ? fullLocalizedDateFromTimestampOrISODate(
                  listen.listened_at * 1000
                )
              : fullLocalizedDateFromTimestampOrISODate(listen.listened_at_iso)
          }
        >
          {preciseTimestamp(
            listen.listened_at_iso || listen.listened_at * 1000
          )}
        </span>
      );
    }

    return (
      <Card
        {...otherProps}
        onDoubleClick={this.playListen}
        className={`listen-card ${isCurrentlyPlaying ? "current-listen" : ""}${
          compact ? " compact" : ""
        }${additionalContent ? " has-additional-content" : " "} ${
          className || ""
        }`}
      >
        <div className="main-content">
          {beforeThumbnailContent}
          {customThumbnail || (
            <div className="listen-thumbnail">
              {thumbnailSrc ? (
                <a
                  href={
                    releaseMBID
                      ? `https://musicbrainz.org/release/${releaseMBID}`
                      : (spotifyURL || youtubeURL || soundcloudURL) ?? ""
                  }
                  title={listen.track_metadata?.release_name ?? "Cover art"}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <img
                    src={thumbnailSrc}
                    alt={listen.track_metadata?.release_name ?? "Cover art"}
                  />
                </a>
              ) : (
                <a
                  href={
                    releaseMBID
                      ? `https://musicbrainz.org/release/${releaseMBID}/cover-art`
                      : "https://musicbrainz.org/doc/How_to_Add_Cover_Art"
                  }
                  title={
                    releaseMBID
                      ? "Add cover art in MusicBrainz"
                      : "How can I add missing cover art?"
                  }
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <img
                    src={ListenCard.defaultThumbnailSrc}
                    alt={
                      releaseMBID
                        ? "Add cover art in MusicBrainz"
                        : "How can I add missing cover art?"
                    }
                  />
                </a>
              )}
            </div>
          )}
          {listenDetails ? (
            <div className="listen-details">{listenDetails}</div>
          ) : (
            <div className="listen-details">
              <div className="title-duration">
                <div title={trackName} className="ellipsis-2-lines">
                  {getTrackLink(listen)}
                </div>
                {trackDurationMs && (
                  <div className="small text-muted" title="Duration">
                    {isNumber(trackDurationMs) &&
                      millisecondsToStr(trackDurationMs)}
                  </div>
                )}
              </div>
              <div className="small text-muted ellipsis" title={artistName}>
                {getArtistLink(listen)}
              </div>
            </div>
          )}
          <div className="right-section">
            {(showUsername || showTimestamp) && (
              <div className="username-and-timestamp">
                {showUsername && (
                  <a
                    href={`/user/${listen.user_name}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    title={listen.user_name ?? undefined}
                  >
                    {listen.user_name}
                  </a>
                )}
                {showTimestamp && timeStampForDisplay}
              </div>
            )}
            <div className="listen-controls">
              {feedbackComponent ?? (
                <ListenFeedbackComponent
                  newAlert={newAlert}
                  listen={listen}
                  currentFeedback={currentFeedback as ListenFeedBack}
                  updateFeedbackCallback={updateFeedbackCallback}
                />
              )}
              {hideActionsMenu ? null : (
                <>
                  <FontAwesomeIcon
                    icon={faEllipsisV as IconProp}
                    title="More actions"
                    className="dropdown-toggle"
                    id="listenControlsDropdown"
                    data-toggle="dropdown"
                    aria-haspopup="true"
                    aria-expanded="true"
                  />
                  <ul
                    className="dropdown-menu dropdown-menu-right"
                    aria-labelledby="listenControlsDropdown"
                  >
                    {recordingMBID && (
                      <ListenControl
                        icon={faExternalLinkAlt}
                        title="Open in MusicBrainz"
                        text="Open in MusicBrainz"
                        link={`https://musicbrainz.org/recording/${recordingMBID}`}
                        anchorTagAttributes={{
                          target: "_blank",
                          rel: "noopener noreferrer",
                        }}
                      />
                    )}
                    {spotifyURL && (
                      <ListenControl
                        icon={faSpotify}
                        title="Open in Spotify"
                        text="Open in Spotify"
                        link={spotifyURL}
                        anchorTagAttributes={{
                          target: "_blank",
                          rel: "noopener noreferrer",
                        }}
                      />
                    )}
                    {youtubeURL && (
                      <ListenControl
                        icon={faYoutube}
                        title="Open in YouTube"
                        text="Open in YouTube"
                        link={youtubeURL}
                        anchorTagAttributes={{
                          target: "_blank",
                          rel: "noopener noreferrer",
                        }}
                      />
                    )}
                    {soundcloudURL && (
                      <ListenControl
                        icon={faSoundcloud}
                        title="Open in Soundcloud"
                        text="Open in Soundcloud"
                        link={soundcloudURL}
                        anchorTagAttributes={{
                          target: "_blank",
                          rel: "noopener noreferrer",
                        }}
                      />
                    )}
                    {enableRecommendButton && (
                      <ListenControl
                        icon={faCommentDots}
                        title="Recommend to my followers"
                        text="Recommend to my followers"
                        action={this.recommendListenToFollowers}
                      />
                    )}
                    {additionalMenuItems}
                    <ListenControl
                      text="Inspect listen"
                      icon={faCode}
                      action={() => {
                        const stringifiedJSON = JSON.stringify(listen, null, 4);
                        const highlightedJSON = hljs.highlight(
                          stringifiedJSON,
                          { language: "json" }
                        ).value;
                        modal?.current?.updateModal(
                          <pre>
                            <code
                              className="hljs"
                              // eslint-disable-next-line react/no-danger
                              dangerouslySetInnerHTML={{
                                __html: sanitize(highlightedJSON),
                              }}
                            />
                          </pre>,
                          undefined,
                          <>
                            <button
                              type="button"
                              className="btn btn-info"
                              onClick={async () => {
                                await navigator.clipboard.writeText(
                                  stringifiedJSON
                                );
                              }}
                            >
                              <FontAwesomeIcon icon={faCopy} /> Copy
                            </button>
                            <button
                              type="button"
                              className="btn btn-default"
                              data-dismiss="modal"
                            >
                              Close
                            </button>
                          </>
                        );
                      }}
                      dataToggle="modal"
                      dataTarget="#SimpleModal"
                    />
                  </ul>
                </>
              )}
              <button
                title="Play"
                className="btn-transparent play-button"
                onClick={this.playListen}
                type="button"
              >
                {isCurrentlyPlaying ? (
                  <FontAwesomeIcon size="1x" icon={faPlay as IconProp} />
                ) : (
                  <FontAwesomeIcon size="2x" icon={faPlayCircle as IconProp} />
                )}
              </button>
              {additionalActions}
            </div>
          </div>
        </div>
        {additionalContent && (
          <div className="additional-content" title={trackName}>
            {additionalContent}
          </div>
        )}
      </Card>
    );
  }
}
