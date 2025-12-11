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
import { Link } from "react-router";
import { toast } from "react-toastify";
import { useSetAtom } from "jotai";
import {
  fullLocalizedDateFromTimestampOrISODate,
  getAlbumArtFromListenMetadata,
  getAlbumArtFromListenMetadataKey,
  getAlbumLink,
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
import {
  addListenToBottomOfQueueAtom,
  addListenToTopOfQueueAtom,
} from "../brainzplayer/BrainzPlayerAtoms";

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

export default function ListenCard(props: ListenCardProps) {
  const {
    listen: listenProp,
    className,
    showTimestamp,
    showUsername,
    additionalContent,
    beforeThumbnailContent,
    customThumbnail,
    listenDetails,
    customTimestamp,
    compact,
    feedbackComponent,
    additionalMenuItems,
    additionalActions,
    ...otherProps
  } = props;

  const [displayListen, setDisplayListen] = React.useState<Listen>(listenProp);
  const [isCurrentlyPlaying, setIsCurrentlyPlaying] = React.useState(false);

  const {
    APIService,
    currentUser,
    userPreferences,
    spotifyAuth,
  } = React.useContext(GlobalAppContext);
  const isMobile = useMediaQuery("(max-width: 480px)");

  const albumArtQueryKey = React.useMemo(
    () => getAlbumArtFromListenMetadataKey(displayListen, spotifyAuth),
    [displayListen, spotifyAuth],
  );

  const albumArtDisabled =
    Boolean(customThumbnail) || !displayListen || userPreferences?.saveData;

  const { data: thumbnailSrc } = useQuery({
    queryKey: ["album-art", albumArtQueryKey, albumArtDisabled],
    queryFn: async () => {
      if (albumArtDisabled) return "";
      try {
        const albumArtURL = await getAlbumArtFromListenMetadata(
          displayListen,
          spotifyAuth,
        );
        return albumArtURL ?? "";
      } catch (error) {
        console.error("Error fetching album art", error);
        return "";
      }
    },
    staleTime: 1000 * 60 * 60 * 12,
    gcTime: 1000 * 60 * 60 * 12,
  });

  const receiveBrainzPlayerMessage = React.useCallback(
    (event: MessageEvent) => {
      if (event.origin !== window.location.origin) {
        // Received postMessage from different origin, ignoring it
        return;
      }
      const { brainzplayer_event, payload: incomingListen } = event.data;
      switch (brainzplayer_event) {
        case "current-listen-change":
          setIsCurrentlyPlaying(
            isEqual(incomingListen, displayListen) ||
              isEqual(incomingListen, listenProp),
          );
          break;
        default:
        // do nothing
      }
    },
    [displayListen, listenProp],
  );
  React.useEffect(() => {
    // Set up and clean up BrainzPlayer event listener
    window.addEventListener("message", receiveBrainzPlayerMessage);
    return () => {
      window.removeEventListener("message", receiveBrainzPlayerMessage);
    };
  }, [receiveBrainzPlayerMessage]);

  const playListen = React.useCallback(() => {
    if (isCurrentlyPlaying) return;
    window.postMessage(
      { brainzplayer_event: "play-listen", payload: displayListen },
      window.location.origin,
    );
  }, [isCurrentlyPlaying, displayListen]);

  const recommendListenToFollowers = React.useCallback(async () => {
    if (!currentUser?.auth_token) return;

    const metadata: UserTrackRecommendationMetadata = {};
    const recording_mbid = getRecordingMBID(displayListen);
    if (recording_mbid) metadata.recording_mbid = recording_mbid;

    const recording_msid = getRecordingMSID(displayListen);
    if (recording_msid) metadata.recording_msid = recording_msid;

    try {
      const status = await APIService.recommendTrackToFollowers(
        currentUser.name,
        currentUser.auth_token,
        metadata,
      );
      if (status === 200) {
        toast.success(
          <ToastMsg
            title="You recommended a track to your followers"
            message={`${getTrackName(displayListen)} by ${getArtistName(
              displayListen,
            )}`}
          />,
          { toastId: "recommended-success" },
        );
      }
    } catch (error) {
      toast.error(
        <ToastMsg
          title="We encountered an error when trying to recommend the track to your followers"
          message={typeof error === "object" ? error.message : error}
        />,
        { toastId: "recommended-error" },
      );
    }
  }, [currentUser, APIService, displayListen]);

  const openMBIDMappingModal = React.useCallback(async () => {
    try {
      const linkedTrackMetadata: TrackMetadata = await NiceModal.show(
        MBIDMappingModal,
        {
          listenToMap: displayListen,
        },
      );
      setDisplayListen((prevState) => {
        const newVal = merge({}, prevState, {
          track_metadata: linkedTrackMetadata,
        });
        return newVal;
      });
    } catch (error) {
      console.error("Error mapping a listen:", error);
    }
  }, [displayListen, setDisplayListen]);

  const isLoggedIn = !isEmpty(currentUser);
  const recordingMSID = getRecordingMSID(displayListen);
  const recordingMBID = getRecordingMBID(displayListen);
  const trackMBID = get(
    displayListen,
    "track_metadata.additional_info.track_mbid",
  );
  const releaseGroupMBID = getReleaseGroupMBID(displayListen);
  const releaseName = getReleaseName(displayListen);
  const artistMBIDs = getArtistMBIDs(displayListen);
  const spotifyURL = SpotifyPlayer.getURLFromListen(displayListen);
  const youtubeURL = YoutubePlayer.getURLFromListen(displayListen);
  const soundcloudURL = SoundcloudPlayer.getURLFromListen(displayListen);
  const trackName = getTrackName(displayListen);
  const artistName = getArtistName(displayListen);
  const trackDurationMs = getTrackDurationInMs(displayListen);

  const hasRecordingMSID = Boolean(recordingMSID);
  const hasRecordingMBID = Boolean(recordingMBID);
  const hasInfoAndMBID =
    artistName && trackName && (hasRecordingMSID || hasRecordingMBID);
  const isListenReviewable =
    Boolean(recordingMBID) ||
    artistMBIDs?.length ||
    Boolean(trackMBID) ||
    Boolean(releaseGroupMBID);

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
  } else if (displayListen.playing_now) {
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
          displayListen.listened_at
            ? fullLocalizedDateFromTimestampOrISODate(
                displayListen.listened_at * 1000
              )
            : fullLocalizedDateFromTimestampOrISODate(
                displayListen.listened_at_iso
              )
        }
      >
        {preciseTimestamp(
          displayListen.listened_at_iso || displayListen.listened_at * 1000
        )}
      </span>
    );
  }

  const thumbnail =
    customThumbnail ??
    getThumbnailElement(
      thumbnailSrc,
      displayListen,
      currentUser,
      openMBIDMappingModal,
    );

  const addListenToBottomOfQueue = useSetAtom(addListenToBottomOfQueueAtom);
  const addListenToTopOfQueue = useSetAtom(addListenToTopOfQueueAtom);

  return (
    <Card
      {...otherProps}
      onDoubleClick={renderBrainzplayer ? playListen : undefined}
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
        <div className="listen-details">
          {listenDetails || (
            <>
              <div className="title-duration">
                <div
                  title={trackName ?? releaseName}
                  className={compact ? "ellipsis" : "ellipsis-2-lines"}
                >
                  {trackName
                    ? getTrackLink(displayListen)
                    : getAlbumLink(displayListen)}
                </div>
                {trackDurationMs && (
                  <div className="small text-muted" title="Duration">
                    {isNumber(trackDurationMs) &&
                      millisecondsToStr(trackDurationMs)}
                  </div>
                )}
              </div>
              <div className="small text-muted ellipsis" title={artistName}>
                {getArtistLink(displayListen)}
              </div>
            </>
          )}
        </div>
        <div className="right-section">
          {(showUsername || showTimestamp) && (
            <div className="username-and-timestamp">
              {showUsername && displayListen.user_name && (
                <Username username={displayListen.user_name} />
              )}
              {showTimestamp && timeStampForDisplay}
            </div>
          )}
          <div className="listen-controls">
            {isLoggedIn &&
              !isMobile &&
              (feedbackComponent ?? (
                <ListenFeedbackComponent listen={displayListen} type="button" />
              ))}
            {!hideActionsMenu && (
              <>
                <button
                  title="More actions"
                  className="btn btn-transparent dropdown-toggle"
                  id="listenControlsDropdown"
                  data-bs-toggle="dropdown"
                  aria-haspopup="true"
                  aria-expanded="false"
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
                      listen={displayListen}
                      type="dropdown"
                    />
                  )}
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
                  {renderBrainzplayer && (
                    <>
                      <ListenControl
                        text="Play Next"
                        icon={faPlay}
                        title="Play Next"
                        action={addListenToTopOfQueue}
                      />
                      <ListenControl
                        text="Add to Queue"
                        icon={faPlusCircle}
                        title="Add to Queue"
                        action={addListenToBottomOfQueue}
                      />
                    </>
                  )}
                  {spotifyURL && (
                    <ListenControl
                      icon={faSpotify}
                      iconColor={dataSourcesInfo.spotify.color}
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
                      iconColor={dataSourcesInfo.youtube.color}
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
                      iconColor={dataSourcesInfo.soundcloud.color}
                      title="Open in Soundcloud"
                      text="Open in Soundcloud"
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
                      icon={faThumbtack}
                      action={() =>
                        NiceModal.show(PinRecordingModal, {
                          recordingToPin: displayListen,
                        })
                      }
                    />
                  )}
                  {isLoggedIn && hasInfoAndMBID && (
                    <ListenControl
                      icon={faCommentDots}
                      title="Recommend to my followers"
                      text="Recommend to my followers"
                      action={recommendListenToFollowers}
                    />
                  )}
                  {isLoggedIn && hasInfoAndMBID && (
                    <ListenControl
                      text="Personally recommend"
                      icon={faPaperPlane}
                      action={() =>
                        NiceModal.show(PersonalRecommendationModal, {
                          listenToPersonallyRecommend: displayListen,
                        })
                      }
                    />
                  )}
                  {isLoggedIn && Boolean(recordingMSID) && (
                    <ListenControl
                      text="Link with MusicBrainz"
                      icon={faLink}
                      action={openMBIDMappingModal}
                    />
                  )}
                  {isLoggedIn && isListenReviewable && (
                    <ListenControl
                      text="Write a review"
                      icon={faPencilAlt}
                      action={() =>
                        NiceModal.show(CBReviewModal, {
                          listen: displayListen,
                        })
                      }
                    />
                  )}
                  {isLoggedIn && (
                    <ListenControl
                      text="Add to playlist"
                      icon={faPlusCircle}
                      action={() =>
                        NiceModal.show(AddToPlaylist, {
                          listen: displayListen,
                        })
                      }
                    />
                  )}
                  {additionalMenuItems}
                  <ListenControl
                    text="Inspect listen"
                    icon={faCode}
                    action={() =>
                      NiceModal.show(ListenPayloadModal, {
                        listen: displayListen,
                      })
                    }
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
                onClick={playListen}
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

function getThumbnailElement(
  thumbnailSrc: string | undefined,
  displayListen: Listen,
  currentUser: ListenBrainzUser,
  openMBIDMappingModal: () => Promise<void>,
): JSX.Element {
  const isLoggedIn = !isEmpty(currentUser);
  const recordingMSID = getRecordingMSID(displayListen);
  const recordingMBID = getRecordingMBID(displayListen);
  const releaseMBID = getReleaseMBID(displayListen);
  const releaseGroupMBID = getReleaseGroupMBID(displayListen);
  const releaseName = getReleaseName(displayListen);
  const spotifyURL = SpotifyPlayer.getURLFromListen(displayListen);
  const youtubeURL = YoutubePlayer.getURLFromListen(displayListen);
  const soundcloudURL = SoundcloudPlayer.getURLFromListen(displayListen);

  let thumbnail;
  if (thumbnailSrc) {
    let thumbnailLink;
    let thumbnailTitle;
    let optionalAttributes = {};
    if (releaseMBID) {
      thumbnailLink = `/release/${releaseMBID}`;
      thumbnailTitle = releaseName;
    } else if (releaseGroupMBID) {
      thumbnailLink = `/album/${releaseGroupMBID}`;
      thumbnailTitle = get(
        displayListen,
        "track_metadata.mbid_mapping.release_group_name",
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
        <Link to={thumbnailLink} title={thumbnailTitle} {...optionalAttributes}>
          <CoverArtWithFallback
            imgSrc={thumbnailSrc}
            altText={thumbnailTitle}
          />
        </Link>
      </div>
    ) : (
      <div className="listen-thumbnail">
        <CoverArtWithFallback imgSrc={thumbnailSrc} altText={thumbnailTitle} />
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
              transform="shrink-10 start-5 up-2.5"
            />
            <FontAwesomeIcon
              icon={faPlus}
              inverse
              transform="shrink-11 start-2.5 up-2.5"
              style={{ stroke: "white", strokeWidth: "60" }}
            />
          </span>
        </div>
      </a>
    );
  } else if (isLoggedIn && Boolean(recordingMSID)) {
    thumbnail = (
      <div
        className="listen-thumbnail"
        title="Link with MusicBrainz"
        onClick={openMBIDMappingModal}
        onKeyDown={openMBIDMappingModal}
        role="button"
        tabIndex={0}
      >
        <div className="not-mapped">
          <FontAwesomeIcon icon={faLink} />
        </div>
      </div>
    );
  } else if (recordingMBID || releaseGroupMBID) {
    const link = recordingMBID
      ? `/track/${recordingMBID}`
      : `/album/${releaseGroupMBID}`;
    thumbnail = (
      <Link
        to={link}
        title="Could not load cover art"
        className="listen-thumbnail"
      >
        <div className="cover-art-fallback">
          <span className="fa-layers fa-fw">
            <FontAwesomeIcon icon={faImage} />
            <FontAwesomeIcon
              icon={faSquare}
              transform="shrink-10 start-5 up-2.5"
            />
          </span>
        </div>
      </Link>
    );
  } else {
    thumbnail = (
      <div className="listen-thumbnail">
        <div className="cover-art-fallback">
          <span className="fa-layers fa-fw">
            <FontAwesomeIcon icon={faImage} />
            <FontAwesomeIcon
              icon={faSquare}
              transform="shrink-10 start-5 up-2.5"
            />
          </span>
        </div>
      </div>
    );
  }
  return thumbnail;
}
