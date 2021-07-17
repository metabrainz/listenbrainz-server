import * as React from "react";
import { get as _get } from "lodash";
import MediaQuery from "react-responsive";
import {
  faMusic,
  faHeart,
  faHeartBroken,
  faEllipsisV,
} from "@fortawesome/free-solid-svg-icons";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

import { getArtistLink, getTrackLink, preciseTimestamp } from "../utils";
import GlobalAppContext from "../GlobalAppContext";
import Card from "../components/Card";
import ListenControl from "./ListenControl";

export const DEFAULT_COVER_ART_URL = "/static/img/default_cover_art.png";

export type ListenCardProps = {
  listen: Listen;
  mode: ListensListMode;
  className?: string;
  currentFeedback: ListenFeedBack;
  isCurrentUser: Boolean;
  playListen: (listen: Listen) => void;
  removeListenFromListenList: (listen: Listen) => void;
  updateFeedback: (recordingMsid: string, score: ListenFeedBack) => void;
  updateRecordingToPin: (recordingToPin: Listen) => void;
  newAlert: (
    alertType: AlertType,
    title: string,
    message: string | JSX.Element
  ) => void;
};

type ListenCardState = {
  isDeleted: Boolean;
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
    const { listen, isCurrentUser, updateFeedback } = this.props;
    const { APIService, currentUser } = this.context;
    // const { submitFeedback } = APIService;
    if (isCurrentUser && currentUser?.auth_token) {
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
          updateFeedback(recordingMSID, score);
        }
      } catch (error) {
        this.handleError(error, "Error while submitting feedback");
      }
    }
  };

  deleteListen = async () => {
    const { listen, isCurrentUser, removeListenFromListenList } = this.props;
    const { APIService, currentUser } = this.context;

    if (isCurrentUser && currentUser?.auth_token) {
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

          // wait for the animation to finish
          setTimeout(function removeListen() {
            removeListenFromListenList(listen);
          }, 1000);
        }
      } catch (error) {
        this.handleError(error, "Error while deleting listen");
      }
    }
  };

  recommendListenToFollowers = async () => {
    const { listen, isCurrentUser, newAlert } = this.props;
    const { APIService, currentUser } = this.context;

    if (isCurrentUser && currentUser?.auth_token) {
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
      listen,
      mode,
      className,
      isCurrentUser,
      updateRecordingToPin,
    } = this.props;
    const { feedback, isDeleted } = this.state;

    return (
      <Card
        onDoubleClick={this.playListen}
        className={`listen-card row ${className} ${
          isDeleted ? " deleted" : ""
        }`}
      >
        <div
          className={`${
            isCurrentUser || mode === "recent" ? " col-xs-9" : " col-xs-12"
          }`}
        >
          <MediaQuery minWidth={768}>
            <div className="col-xs-8">
              <div className="track-details">
                <p title={listen.track_metadata?.track_name}>
                  {getTrackLink(listen)}
                </p>
                <p>
                  <small
                    className="text-muted"
                    title={listen.track_metadata?.artist_name}
                  >
                    {getArtistLink(listen)}
                  </small>
                </p>
              </div>
            </div>
            <div className="col-xs-4">
              {listen.playing_now ? (
                <span className="listen-time text-center text-muted">
                  <FontAwesomeIcon icon={faMusic as IconProp} /> Playing now
                </span>
              ) : (
                <span
                  className="listen-time text-center text-muted"
                  title={
                    listen.listened_at_iso?.toString() ||
                    new Date(listen.listened_at * 1000).toISOString()
                  }
                >
                  {preciseTimestamp(
                    listen.listened_at_iso || listen.listened_at * 1000
                  )}
                </span>
              )}
            </div>
          </MediaQuery>
          <MediaQuery maxWidth={767}>
            <div className="col-xs-12">
              <div className="track-details">
                <p title={listen.track_metadata?.track_name}>
                  {getTrackLink(listen)}
                </p>
                <p>
                  <small
                    className="text-muted"
                    title={listen.track_metadata?.artist_name}
                  >
                    {listen.playing_now ? (
                      <span className="listen-time text-muted">
                        <FontAwesomeIcon icon={faMusic as IconProp} /> Playing
                        now &#8212;
                      </span>
                    ) : (
                      <span
                        className="listen-time text-muted"
                        title={
                          listen.listened_at_iso?.toString() ||
                          new Date(listen.listened_at * 1000).toISOString()
                        }
                      >
                        {preciseTimestamp(
                          listen.listened_at_iso || listen.listened_at * 1000
                        )}
                        &nbsp; &#8212; &nbsp;
                      </span>
                    )}
                    {getArtistLink(listen)}
                  </small>
                </p>
              </div>
            </div>
          </MediaQuery>
        </div>
        <div
          className={`${
            isCurrentUser || mode === "recent"
              ? " col-xs-3 text-center"
              : "hidden"
          }`}
        >
          {mode === "recent" ? (
            <a
              href={`/user/${listen.user_name}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              {listen.user_name}
            </a>
          ) : (
            <div className="listen-controls">
              {!listen?.playing_now && (
                <>
                  <ListenControl
                    icon={faHeart}
                    title="Love"
                    action={() => this.submitFeedback(feedback === 1 ? 0 : 1)}
                    className={`${feedback === 1 ? " loved" : ""}`}
                  />
                  <ListenControl
                    icon={faHeartBroken}
                    title="Hate"
                    action={() => this.submitFeedback(feedback === -1 ? 0 : -1)}
                    className={`${feedback === -1 ? " hated" : ""}`}
                  />
                  <FontAwesomeIcon
                    icon={faEllipsisV as IconProp}
                    title="Delete"
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
                    />
                    <ListenControl
                      title="Delete Listen"
                      action={this.deleteListen}
                    />
                    <ListenControl
                      title="Pin this Recording"
                      action={() => updateRecordingToPin(listen)}
                      dataToggle="modal"
                      dataTarget="#PinRecordingModal"
                    />
                  </ul>
                </>
              )}
            </div>
          )}
        </div>
      </Card>
    );
  }
}
