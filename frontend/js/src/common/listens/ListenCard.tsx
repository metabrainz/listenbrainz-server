import * as React from "react";

import NiceModal from "@ebay/nice-modal-react";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import {
  faSoundcloud,
  faSpotify,
  faYoutube,
} from "@fortawesome/free-brands-svg-icons";
import { faPlayCircle } from "@fortawesome/free-regular-svg-icons";
import {
  faCode,
  faCommentDots,
  faEllipsisVertical,
  faExternalLinkAlt,
  faImage,
  faLink,
  faMusic,
  faPaperPlane,
  faPencilAlt,
  faPlay,
  faPlus,
  faPlusCircle,
  faSquare,
  faThumbtack,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { useQuery } from "@tanstack/react-query";
import { get, isEmpty, isEqual, isNil, isNumber, merge } from "lodash";
import { Link } from "react-router-dom";
import { toast } from "react-toastify";
import {
  fullLocalizedDateFromTimestampOrISODate,
  getAlbumArtFromListenMetadata,
  getAlbumArtFromListenMetadataKey,
  getArtistLink,
  getArtistMBIDs,
  getArtistName,
  getRecordingMBID,
  getRecordingMSID,
  getReleaseGroupMBID,
  getReleaseMBID,
  getReleaseName,
  getTrackDurationInMs,
  getTrackLink,
  getTrackName,
  preciseTimestamp,
} from "../../utils/utils";

import CBReviewModal from "../../cb-review/CBReviewModal";
import Card from "../../components/Card";
import { useMediaQuery } from "../../explore/fresh-releases/utils";
import { ToastMsg } from "../../notifications/Notifications";
import PersonalRecommendationModal from "../../personal-recommendations/PersonalRecommendationsModal";
import PinRecordingModal from "../../pins/PinRecordingModal";
import { millisecondsToStr } from "../../playlists/utils";
import { dataSourcesInfo } from "../../settings/brainzplayer/BrainzPlayerSettings";
import GlobalAppContext from "../../utils/GlobalAppContext";
import {
  BrainzPlayerActionType,
  useBrainzPlayerDispatch,
} from "../brainzplayer/BrainzPlayerContext";
import SoundcloudPlayer from "../brainzplayer/SoundcloudPlayer";
import SpotifyPlayer from "../brainzplayer/SpotifyPlayer";
import YoutubePlayer from "../brainzplayer/YoutubePlayer";
import Username from "../Username";
import AddToPlaylist from "./AddToPlaylist";
import CoverArtWithFallback from "./CoverArtWithFallback";
import ListenControl from "./ListenControl";
import ListenFeedbackComponent from "./ListenFeedbackComponent";
import ListenPayloadModal from "./ListenPayloadModal";
import MBIDMappingModal from "./MBIDMappingModal";

export type ListenCardProps = {
  listen: Listen;
  className?: string;
  showTimestamp: boolean;
  showUsername: boolean;
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

export type ListenCardState = {
  listen: Listen;
  isCurrentlyPlaying: boolean;
};

type ListenCardPropsWithDispatch = ListenCardProps & {
  thumbnailSrc?: string;
  dispatch: (action: BrainzPlayerActionType, callback?: () => void) => void;
  isMobile: boolean;
};

export class ListenCard extends React.Component<
  ListenCardPropsWithDispatch,
  ListenCardState
> {
  static coverartPlaceholder = "/static/img/cover-art-placeholder.jpg";
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;
  constructor(props: ListenCardPropsWithDispatch) {
    super(props);
    this.state = {
      listen: props.listen,
      isCurrentlyPlaying: false,
    };
  }

  async componentDidMount() {
    window.addEventListener("message", this.receiveBrainzPlayerMessage);
  }

  async componentDidUpdate(
    oldProps: ListenCardProps,
    oldState: ListenCardState
  ) {
    const { listen: oldListen } = oldProps;
    const { listen, customThumbnail } = this.props;
    if (Boolean(listen) && !isEqual(listen, oldListen)) {
      this.setState({ listen });
    }
  }

  componentWillUnmount() {
    window.removeEventListener("message", this.receiveBrainzPlayerMessage);
  }

  playListen = () => {
    const { listen, isCurrentlyPlaying } = this.state;
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
    const { listen } = this.state;
    if (isNil(listen)) {
      return false;
    }
    return isEqual(element, listen);
  };

  recommendListenToFollowers = async () => {
    const { listen } = this.state;
    const { APIService, currentUser } = this.context;

    if (currentUser?.auth_token) {
      const metadata: UserTrackRecommendationMetadata = {};

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
          toast.success(
            <ToastMsg
              title="You recommended a track to your followers"
              message={`${getArtistName(listen)} - ${getTrackName(listen)}`}
            />,
            { toastId: "recommended-success" }
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
    if (!error) {
      return;
    }
    toast.error(
      <ToastMsg
        title={title || "Error"}
        message={typeof error === "object" ? error.message : error}
      />,
      { toastId: "recommended-error" }
    );
  };

  addToTopOfQueue = () => {
    const { dispatch } = this.props;
    const { listen } = this.state;
    dispatch({ type: "ADD_LISTEN_TO_TOP_OF_QUEUE", data: listen });
  };

  addToBottomOfQueue = () => {
    const { dispatch } = this.props;
    const { listen } = this.state;
    dispatch({ type: "ADD_LISTEN_TO_BOTTOM_OF_QUEUE", data: listen });
  };

  render() {
    const {
      additionalContent,
      beforeThumbnailContent,
      customThumbnail,
      className,
      showUsername,
      showTimestamp,
      listenDetails,
      customTimestamp,
      compact,
      feedbackComponent,
      additionalMenuItems,
      additionalActions,
      listen: listenFromProps,
      dispatch: dispatchProp,
      thumbnailSrc,
      isMobile,
      ...otherProps
    } = this.props;
    const { listen, isCurrentlyPlaying } = this.state;
    const { currentUser, userPreferences } = this.context;

    const isLoggedIn = !isEmpty(currentUser);

    const recordingMSID = getRecordingMSID(listen);
    const recordingMBID = getRecordingMBID(listen);
    const trackMBID = get(listen, "track_metadata.additional_info.track_mbid");
    const releaseMBID = getReleaseMBID(listen);
    const releaseGroupMBID = getReleaseGroupMBID(listen);
    const artistMBIDs = getArtistMBIDs(listen);
    const spotifyURL = SpotifyPlayer.getURLFromListen(listen);
    const youtubeURL = YoutubePlayer.getURLFromListen(listen);
    const soundcloudURL = SoundcloudPlayer.getURLFromListen(listen);

    const trackName = getTrackName(listen);
    const artistName = getArtistName(listen);
    const trackDurationMs = getTrackDurationInMs(listen);

    const hasRecordingMSID = Boolean(recordingMSID);
    const hasRecordingMBID = Boolean(recordingMBID);
    const hasInfoAndMBID =
      artistName && trackName && (hasRecordingMSID || hasRecordingMBID);
    const isListenReviewable =
      Boolean(recordingMBID) ||
      artistMBIDs?.length ||
      Boolean(trackMBID) ||
      Boolean(releaseGroupMBID);

    // Hide the actions menu if in compact mode or no buttons to be shown
    const hasActionOptions =
      additionalMenuItems?.length ||
      hasInfoAndMBID ||
      recordingMBID ||
      spotifyURL ||
      youtubeURL ||
      soundcloudURL;
    const hideActionsMenu = compact || !hasActionOptions;

    const renderBrainzplayer =
      userPreferences?.brainzplayer?.brainzplayerEnabled ?? true;

    let timeStampForDisplay;
    if (customTimestamp) {
      timeStampForDisplay = customTimestamp;
    } else if (listen.playing_now) {
      timeStampForDisplay = (
        <span className="listen-time">
          <Link to="/listening-now/">
            <FontAwesomeIcon icon={faMusic as IconProp} /> Listening now &#8212;
          </Link>
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
    let thumbnail;
    if (customThumbnail) {
      thumbnail = customThumbnail;
    } else if (thumbnailSrc) {
      let thumbnailLink;
      let thumbnailTitle;
      let optionalAttributes = {};
      if (releaseMBID) {
        thumbnailLink = `/release/${releaseMBID}`;
        thumbnailTitle = getReleaseName(listen);
      } else if (releaseGroupMBID) {
        thumbnailLink = `/album/${releaseGroupMBID}`;
        thumbnailTitle = get(
          listen,
          "track_metadata.mbid_mapping.release_group_name"
        );
      } else {
        thumbnailLink = spotifyURL || youtubeURL || soundcloudURL;
        thumbnailTitle = "Cover art";
        optionalAttributes = {
          target: "_blank",
          rel: "noopener noreferrer",
        };
      }
      thumbnail = thumbnailLink ? (
        <div className="listen-thumbnail">
          <Link
            to={thumbnailLink}
            title={thumbnailTitle}
            {...optionalAttributes}
          >
            <CoverArtWithFallback
              imgSrc={thumbnailSrc}
              altText={thumbnailTitle}
            />
          </Link>
        </div>
      ) : (
        <div className="listen-thumbnail">
          <CoverArtWithFallback
            imgSrc={thumbnailSrc}
            altText={thumbnailTitle}
          />
        </div>
      );
    } else if (releaseMBID) {
      thumbnail = (
        <a
          href={`https://musicbrainz.org/release/${releaseMBID}/cover-art`}
          title="Add cover art in MusicBrainz"
          target="_blank"
          rel="noopener noreferrer"
          className="listen-thumbnail"
        >
          <div className="add-cover-art">
            <span className="fa-layers fa-fw">
              <FontAwesomeIcon icon={faImage} />
              <FontAwesomeIcon
                icon={faSquare}
                transform="shrink-10 left-5 up-2.5"
              />
              <FontAwesomeIcon
                icon={faPlus}
                inverse
                transform="shrink-11 left-2.5 up-2.5"
                style={{ stroke: "white", strokeWidth: "60" }}
              />
            </span>
          </div>
        </a>
      );
    } else if (isLoggedIn && Boolean(recordingMSID)) {
      const openModal = () => {
        NiceModal.show(MBIDMappingModal, {
          listenToMap: listen,
        }).then((linkedTrackMetadata: any) => {
          this.setState((prevState) => {
            return {
              listen: merge({}, prevState.listen, {
                track_metadata: linkedTrackMetadata,
              }),
            };
          });
        });
      };
      thumbnail = (
        <div
          className="listen-thumbnail"
          title="Link with MusicBrainz"
          onClick={openModal}
          onKeyDown={openModal}
          role="button"
          tabIndex={0}
        >
          <div className="not-mapped">
            <FontAwesomeIcon icon={faLink} />
          </div>
        </div>
      );
    } else if (recordingMBID || releaseGroupMBID) {
      if (recordingMBID) {
        thumbnail = (
          <a
            href={`https://musicbrainz.org/recording/${recordingMBID}`}
            title="Could not load cover art"
            target="_blank"
            rel="noopener noreferrer"
            className="listen-thumbnail"
          >
            <div className="cover-art-fallback">
              <span className="fa-layers fa-fw">
                <FontAwesomeIcon icon={faImage} />
                <FontAwesomeIcon
                  icon={faSquare}
                  transform="shrink-10 left-5 up-2.5"
                />
              </span>
            </div>
          </a>
        );
      } else {
        thumbnail = (
          <Link
            to={`/album/${releaseGroupMBID}`}
            title="Could not load cover art"
            className="listen-thumbnail"
          >
            <div className="cover-art-fallback">
              <span className="fa-layers fa-fw">
                <FontAwesomeIcon icon={faImage} />
                <FontAwesomeIcon
                  icon={faSquare}
                  transform="shrink-10 left-5 up-2.5"
                />
              </span>
            </div>
          </Link>
        );
      }
    } else {
      // eslint-disable-next-line react/jsx-no-useless-fragment
      thumbnail = (
        <div className="listen-thumbnail">
          <div className="cover-art-fallback">
            <span className="fa-layers fa-fw">
              <FontAwesomeIcon icon={faImage} />
              <FontAwesomeIcon
                icon={faSquare}
                transform="shrink-10 left-5 up-2.5"
              />
            </span>
          </div>
        </div>
      );
    }

    return (
      <Card
        {...otherProps}
        onDoubleClick={renderBrainzplayer ? this.playListen : undefined}
        className={`listen-card ${isCurrentlyPlaying ? "current-listen" : ""}${
          compact ? " compact" : ""
        }${additionalContent ? " has-additional-content" : " "} ${
          className || ""
        }`}
        data-testid="listen"
      >
        <div className="main-content">
          {beforeThumbnailContent}
          {thumbnail}
          {listenDetails ? (
            <div className="listen-details">{listenDetails}</div>
          ) : (
            <div className="listen-details">
              <div className="title-duration">
                <div
                  title={trackName}
                  className={compact ? "ellipsis" : "ellipsis-2-lines"}
                >
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
                {showUsername && listen.user_name && (
                  <Username username={listen.user_name} />
                )}
                {showTimestamp && timeStampForDisplay}
              </div>
            )}
            <div className="listen-controls">
              {isLoggedIn &&
                !isMobile &&
                (feedbackComponent ?? (
                  <ListenFeedbackComponent listen={listen} type="button" />
                ))}
              {hideActionsMenu ? null : (
                <>
                  <button
                    title="More actions"
                    className="btn btn-transparent dropdown-toggle"
                    id="listenControlsDropdown"
                    data-toggle="dropdown"
                    aria-haspopup="true"
                    aria-expanded="true"
                    type="button"
                  >
                    <FontAwesomeIcon icon={faEllipsisVertical} fixedWidth />
                  </button>
                  <ul
                    className="dropdown-menu dropdown-menu-right"
                    aria-labelledby="listenControlsDropdown"
                  >
                    {isMobile && (
                      <ListenFeedbackComponent
                        listen={listen}
                        type="dropdown"
                      />
                    )}
                    {recordingMBID && (
                      <ListenControl
                        icon={faExternalLinkAlt}
                        title="Open in MusicBrainz"
                        text="Open in MusicBrainz"
                        key="Open in MusicBrainz"
                        link={`https://musicbrainz.org/recording/${recordingMBID}`}
                        anchorTagAttributes={{
                          target: "_blank",
                          rel: "noopener noreferrer",
                        }}
                      />
                    )}
                    {renderBrainzplayer && (
                      <>
                        <ListenControl
                          text="Play Next"
                          icon={faPlay}
                          title="Play Next"
                          action={this.addToTopOfQueue}
                        />
                        <ListenControl
                          text="Add to Queue"
                          icon={faPlusCircle}
                          title="Add to Queue"
                          action={this.addToBottomOfQueue}
                        />
                      </>
                    )}

                    {spotifyURL && (
                      <ListenControl
                        icon={faSpotify}
                        iconColor={dataSourcesInfo.spotify.color}
                        title="Open in Spotify"
                        text="Open in Spotify"
                        key="Open in Spotify"
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
                        iconColor={dataSourcesInfo.youtube.color}
                        title="Open in YouTube"
                        text="Open in YouTube"
                        key="Open in YouTube"
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
                        iconColor={dataSourcesInfo.soundcloud.color}
                        title="Open in Soundcloud"
                        text="Open in Soundcloud"
                        key="Open in Soundcloud"
                        link={soundcloudURL}
                        anchorTagAttributes={{
                          target: "_blank",
                          rel: "noopener noreferrer",
                        }}
                      />
                    )}
                    {isLoggedIn && hasInfoAndMBID && (
                      <ListenControl
                        text="Pin this track"
                        key="Pin this track"
                        icon={faThumbtack}
                        action={() => {
                          NiceModal.show(PinRecordingModal, {
                            recordingToPin: listen,
                          });
                        }}
                        dataToggle="modal"
                        dataTarget="#PinRecordingModal"
                      />
                    )}
                    {isLoggedIn && hasInfoAndMBID && (
                      <ListenControl
                        icon={faCommentDots}
                        title="Recommend to my followers"
                        text="Recommend to my followers"
                        key="Recommend to my followers"
                        action={this.recommendListenToFollowers}
                      />
                    )}
                    {isLoggedIn && hasInfoAndMBID && (
                      <ListenControl
                        text="Personally recommend"
                        key="Personally recommend"
                        icon={faPaperPlane}
                        action={() => {
                          NiceModal.show(PersonalRecommendationModal, {
                            listenToPersonallyRecommend: listen,
                          });
                        }}
                        dataToggle="modal"
                        dataTarget="#PersonalRecommendationModal"
                      />
                    )}
                    {isLoggedIn && Boolean(recordingMSID) && (
                      <ListenControl
                        text="Link with MusicBrainz"
                        key="Link with MusicBrainz"
                        icon={faLink}
                        action={() => {
                          NiceModal.show(MBIDMappingModal, {
                            listenToMap: listen,
                          });
                        }}
                      />
                    )}
                    {isLoggedIn && isListenReviewable && (
                      <ListenControl
                        text="Write a review"
                        key="Write a review"
                        icon={faPencilAlt}
                        action={() => {
                          NiceModal.show(CBReviewModal, {
                            listen,
                          });
                        }}
                        dataToggle="modal"
                        dataTarget="#CBReviewModal"
                      />
                    )}
                    {isLoggedIn && (
                      <ListenControl
                        text="Add to playlist"
                        key="Add to playlist"
                        icon={faPlusCircle}
                        action={() => {
                          NiceModal.show(AddToPlaylist, {
                            listen,
                          });
                        }}
                        dataToggle="modal"
                        dataTarget="#AddToPlaylistModal"
                      />
                    )}
                    {additionalMenuItems}
                    <ListenControl
                      text="Inspect listen"
                      key="Inspect listen"
                      icon={faCode}
                      action={() => {
                        NiceModal.show(ListenPayloadModal, {
                          listen,
                        });
                      }}
                      dataToggle="modal"
                      dataTarget="#ListenPayloadModal"
                    />
                  </ul>
                </>
              )}
              {renderBrainzplayer && (
                <button
                  title="Play"
                  className={`btn btn-transparent play-button${
                    isCurrentlyPlaying ? " playing" : ""
                  }`}
                  onClick={this.playListen}
                  type="button"
                >
                  <FontAwesomeIcon
                    fixedWidth
                    icon={isCurrentlyPlaying ? faPlay : faPlayCircle}
                  />
                </button>
              )}
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

export default function ListenCardWrapper(props: ListenCardProps) {
  const dispatch = useBrainzPlayerDispatch();
  const { spotifyAuth, APIService, userPreferences } = React.useContext(
    GlobalAppContext
  );
  const { listen, customThumbnail } = props;

  const albumArtQueryKey = React.useMemo(
    () => getAlbumArtFromListenMetadataKey(listen, spotifyAuth),
    [listen, spotifyAuth]
  );

  const albumArtDisabled =
    Boolean(customThumbnail) || !listen || userPreferences?.saveData;

  const { data: thumbnailSrc } = useQuery({
    queryKey: ["album-art", albumArtQueryKey, albumArtDisabled],
    queryFn: async () => {
      if (albumArtDisabled) {
        return "";
      }
      try {
        const albumArtURL = await getAlbumArtFromListenMetadata(
          listen,
          spotifyAuth
        );
        return albumArtURL ?? "";
      } catch (error) {
        // eslint-disable-next-line no-console
        console.error("Error fetching album art", error);
        return "";
      }
    },
    staleTime: 1000 * 60 * 60 * 12,
    gcTime: 1000 * 60 * 60 * 12,
  });

  const isMobile = useMediaQuery("(max-width: 480px)");

  return (
    <ListenCard
      {...props}
      dispatch={dispatch}
      thumbnailSrc={thumbnailSrc}
      isMobile={isMobile}
    />
  );
}
