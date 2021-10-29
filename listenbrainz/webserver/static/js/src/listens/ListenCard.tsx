import * as React from "react";
import { get as _get, has as _has, isEqual, isNil } from "lodash";
import {
  faMusic,
  faEllipsisV,
  faPlay,
  faCommentDots,
} from "@fortawesome/free-solid-svg-icons";
import { faPlayCircle } from "@fortawesome/free-regular-svg-icons";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

import {
  getArtistLink,
  getTrackLink,
  preciseTimestamp,
  fullLocalizedDateFromTimestampOrISODate,
  getRecordingMBID,
} from "../utils";
import GlobalAppContext from "../GlobalAppContext";
import Card from "../components/Card";
import ListenControl from "./ListenControl";
import ListenFeedbackComponent from "./ListenFeedbackComponent";

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
    score: ListenFeedBack | RecommendationFeedBack
  ) => void;
  newAlert: (
    alertType: AlertType,
    title: string,
    message: string | JSX.Element
  ) => void;
  // This show under the first line of listen details. It's meant for reviews, etc.
  additionalDetails?: string | JSX.Element;
  thumbnail?: JSX.Element;
  // The default details (recording name, artist name) can be replaced
  listenDetails?: JSX.Element;
  compact?: boolean;
  // The default Listen fedback (love/hate) can be replaced
  feedbackComponent?: JSX.Element;
  // These go in the dropdown menu
  additionalMenuItems?: JSX.Element;
};

type ListenCardState = {
  isCurrentlyPlaying: boolean;
};

export default class ListenCard extends React.Component<
  ListenCardProps,
  ListenCardState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  constructor(props: ListenCardProps) {
    super(props);

    this.state = {
      isCurrentlyPlaying: false,
    };
  }

  componentDidMount() {
    window.addEventListener("message", this.receiveBrainzPlayerMessage);
  }

  componentWillUnmount() {
    window.removeEventListener("message", this.receiveBrainzPlayerMessage);
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
        artist_name: _get(listen, "track_metadata.artist_name"),
        track_name: _get(listen, "track_metadata.track_name"),
        release_name: _get(listen, "track_metadata.release_name"),
        recording_mbid: getRecordingMBID(listen),
        recording_msid: _get(
          listen,
          "track_metadata.additional_info.recording_msid"
        ),
        artist_msid: _get(listen, "track_metadata.additional_info.artist_msid"),
      };
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
      additionalDetails,
      listen,
      className,
      showUsername,
      showTimestamp,
      thumbnail,
      listenDetails,
      compact,
      feedbackComponent,
      additionalMenuItems,
      currentFeedback,
      newAlert,
      updateFeedbackCallback,
      ...otherProps
    } = this.props;
    const { isCurrentlyPlaying } = this.state;

    const recordingMSID = _get(
      listen,
      "track_metadata.additional_info.recording_msid"
    );

    const hasRecordingMSID = Boolean(recordingMSID);
    const enableRecommendButton =
      _has(listen, "track_metadata.artist_name") &&
      _has(listen, "track_metadata.track_name") &&
      hasRecordingMSID;

    // Hide the actions menu if in compact mode or no buttons to be shown
    const hideActionsMenu =
      compact || (!additionalMenuItems && !enableRecommendButton);

    const timeStampForDisplay = (
      <>
        {listen.playing_now ? (
          <span className="listen-time">
            <FontAwesomeIcon icon={faMusic as IconProp} /> Playing now &#8212;
          </span>
        ) : (
          <span
            className="listen-time"
            title={
              listen.listened_at
                ? fullLocalizedDateFromTimestampOrISODate(
                    listen.listened_at * 1000
                  )
                : fullLocalizedDateFromTimestampOrISODate(
                    listen.listened_at_iso
                  )
            }
          >
            {preciseTimestamp(
              listen.listened_at_iso || listen.listened_at * 1000
            )}
          </span>
        )}
      </>
    );

    return (
      <Card
        {...otherProps}
        onDoubleClick={this.playListen}
        className={`listen-card row ${
          isCurrentlyPlaying ? "current-listen" : ""
        }${compact ? " compact" : " "} ${className || ""}`}
      >
        {thumbnail && <div className="listen-thumbnail">{thumbnail}</div>}
        {listenDetails ? (
          <div className="listen-details">{listenDetails}</div>
        ) : (
          <div className="listen-details">
            <div
              title={listen.track_metadata?.track_name}
              className="ellipsis-2-lines"
            >
              {getTrackLink(listen)}
            </div>
            <span
              className="small text-muted ellipsis"
              title={listen.track_metadata?.artist_name}
            >
              {getArtistLink(listen)}
            </span>
          </div>
        )}
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
                {enableRecommendButton && (
                  <ListenControl
                    icon={faCommentDots}
                    title="Recommend to my followers"
                    action={this.recommendListenToFollowers}
                  />
                )}
                {additionalMenuItems}
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
        </div>
        {additionalDetails && (
          <span
            className="additional-details"
            title={listen.track_metadata?.track_name}
          >
            {additionalDetails}
          </span>
        )}
      </Card>
    );
  }
}
