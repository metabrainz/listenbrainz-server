import * as React from "react";
import { get as _get, has as _has } from "lodash";
import {
  faMusic,
  faHeart,
  faHeartBroken,
  faEllipsisV,
} from "@fortawesome/free-solid-svg-icons";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

import {
  getArtistLink,
  getPlayButton,
  getTrackLink,
  preciseTimestamp,
  fullLocalizedDateFromTimestampOrISODate,
} from "../utils";
import GlobalAppContext from "../GlobalAppContext";
import Card from "../components/Card";
import ListenControl from "./ListenControl";

export const DEFAULT_COVER_ART_URL = "/static/img/default_cover_art.png";

export type ListenCardProps = {
  listen: Listen;
  className?: string;
  currentFeedback: ListenFeedBack;
  isCurrentListen: boolean;
  showTimestamp: boolean;
  showUsername: boolean;
  playListen: (listen: Listen) => void;
  removeListenCallback?: (listen: Listen) => void;
  updateFeedbackCallback?: (
    recordingMsid: string,
    score: ListenFeedBack
  ) => void;
  updateRecordingToPin?: (recordingToPin: Listen) => void;
  newAlert: (
    alertType: AlertType,
    title: string,
    message: string | JSX.Element
  ) => void;
  additionalDetails?: string | JSX.Element;
  thumbnail?: JSX.Element;
  // The default details (recording name, artist name) can be superseeded
  listenDetails?: JSX.Element;
  compact?: boolean;
};

type ListenCardState = {
  isDeleted: boolean;
  feedback: ListenFeedBack;
};

export default class ListenCard extends React.Component<
  ListenCardProps,
  ListenCardState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  playListen: (listen: Listen) => void;

  constructor(props: ListenCardProps) {
    super(props);

    this.state = {
      isDeleted: false,
      feedback: props.currentFeedback || 0,
    };
    this.playListen = props.playListen.bind(this, props.listen);
  }

  componentDidUpdate(prevProps: ListenCardProps) {
    const { currentFeedback } = this.props;
    if (currentFeedback !== prevProps.currentFeedback) {
      this.setState({ feedback: currentFeedback });
    }
  }

  submitFeedback = async (score: ListenFeedBack) => {
    const { listen, updateFeedbackCallback } = this.props;
    const { APIService, currentUser } = this.context;
    if (currentUser?.auth_token) {
      const recordingMSID = _get(
        listen,
        "track_metadata.additional_info.recording_msid"
      );

      try {
        const status = await APIService.submitFeedback(
          currentUser.auth_token,
          recordingMSID,
          score
        );
        if (status === 200) {
          this.setState({ feedback: score });
          if (updateFeedbackCallback) {
            updateFeedbackCallback(recordingMSID, score);
          }
        }
      } catch (error) {
        this.handleError(error, "Error while submitting feedback");
      }
    }
  };

  deleteListen = async () => {
    const { listen, removeListenCallback } = this.props;
    const { APIService, currentUser } = this.context;
    const isCurrentUser =
      Boolean(listen.user_name) && listen.user_name === currentUser?.name;
    if (removeListenCallback && isCurrentUser && currentUser?.auth_token) {
      const listenedAt = _get(listen, "listened_at");
      const recordingMSID = _get(
        listen,
        "track_metadata.additional_info.recording_msid"
      );

      try {
        const status = await APIService.deleteListen(
          currentUser.auth_token,
          recordingMSID,
          listenedAt
        );
        if (status === 200) {
          this.setState({ isDeleted: true });
          if (removeListenCallback) {
            // wait for the animation to finish
            setTimeout(function removeListen() {
              removeListenCallback(listen);
            }, 1000);
          }
        }
      } catch (error) {
        this.handleError(error, "Error while deleting listen");
      }
    }
  };

  recommendListenToFollowers = async () => {
    const { listen, newAlert } = this.props;
    const { APIService, currentUser } = this.context;

    if (currentUser?.auth_token) {
      const metadata: UserTrackRecommendationMetadata = {
        artist_name: _get(listen, "track_metadata.artist_name"),
        track_name: _get(listen, "track_metadata.track_name"),
        release_name: _get(listen, "track_metadata.release_name"),
        recording_mbid: _get(
          listen,
          "track_metadata.additional_info.recording_mbid"
        ),
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
      isCurrentListen,
      showUsername,
      showTimestamp,
      updateRecordingToPin,
      thumbnail,
      listenDetails,
      compact,
    } = this.props;
    const { currentUser } = this.context;
    const { feedback, isDeleted } = this.state;

    const isCurrentUser =
      Boolean(listen.user_name) && listen.user_name === currentUser?.name;

    const enableFeedbackButtons = _has(
      listen,
      "track_metadata.additional_info.recording_msid"
    );
    const enableRecommendButton =
      _has(listen, "track_metadata.artist_name") &&
      _has(listen, "track_metadata.track_name") &&
      _has(listen, "track_metadata.additional_info.recording_msid");

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

    const listenedAt = _get(listen, "listened_at");
    const recordingMSID = _get(
      listen,
      "track_metadata.additional_info.recording_msid"
    );
    const canDelete =
      isCurrentUser && Boolean(listenedAt) && Boolean(recordingMSID);

    return (
      <Card
        onDoubleClick={isCurrentListen ? undefined : this.playListen}
        className={`listen-card row ${
          isCurrentListen ? "current-listen" : ""
        } ${isDeleted ? "deleted" : ""} ${compact ? " compact" : " "} ${
          className || ""
        }`}
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
          {!currentUser?.auth_token || compact ? null : (
            <>
              <ListenControl
                icon={faHeart}
                title="Love"
                action={() => this.submitFeedback(feedback === 1 ? 0 : 1)}
                className={`${feedback === 1 ? " loved" : ""}`}
                disabled={!enableFeedbackButtons}
              />
              <ListenControl
                icon={faHeartBroken}
                title="Hate"
                action={() => this.submitFeedback(feedback === -1 ? 0 : -1)}
                className={`${feedback === -1 ? " hated" : ""}`}
                disabled={!enableFeedbackButtons}
              />

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
                <ListenControl
                  title="Recommend to my followers"
                  action={this.recommendListenToFollowers}
                  disabled={!enableRecommendButton}
                />
                <ListenControl
                  title="Pin this Recording"
                  action={
                    updateRecordingToPin
                      ? () => updateRecordingToPin(listen)
                      : undefined
                  }
                  dataToggle="modal"
                  dataTarget="#PinRecordingModal"
                />
                <ListenControl
                  disabled={!canDelete}
                  title="Delete Listen"
                  action={canDelete ? this.deleteListen : undefined}
                />
              </ul>
            </>
          )}
          {getPlayButton(listen, isCurrentListen, this.playListen)}
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
