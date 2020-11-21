import * as timeago from "time-ago";

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

import { getArtistLink, getTrackLink } from "../utils";
import Card from "../components/Card";
import APIService from "../APIService";
import ListenControl from "../listens/ListenControl";

export const DEFAULT_COVER_ART_URL = "/static/img/default_cover_art.png";

export type ListenCardProps = {
  apiUrl: string;
  listen: Listen;
  currentFeedback: ListenFeedBack;
  isCurrentUser: Boolean;
  currentUser?: ListenBrainzUser;
  playListen: (listen: Listen) => void;
  removeTrackFromPlaylist: (listen: Listen) => void;
  updateFeedback: (recordingMsid: string, score: ListenFeedBack) => void;
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
  APIService: APIService;
  playListen: (listen: Listen) => void;

  constructor(props: ListenCardProps) {
    super(props);

    this.state = {
      isDeleted: false,
      feedback: props.currentFeedback || 0,
    };

    this.APIService = new APIService(
      props.apiUrl || `${window.location.origin}/1`
    );

    this.playListen = props.playListen.bind(this, props.listen);
  }

  componentDidUpdate(prevProps: ListenCardProps) {
    const { currentFeedback } = this.props;
    if (currentFeedback !== prevProps.currentFeedback) {
      this.setState({ feedback: currentFeedback });
    }
  }

  submitFeedback = async (score: ListenFeedBack) => {
    const { listen, currentUser, isCurrentUser, updateFeedback } = this.props;
    if (isCurrentUser && currentUser?.auth_token) {
      const recordingMSID = _get(
        listen,
        "track_metadata.additional_info.recording_msid"
      );

      try {
        const status = await this.APIService.submitFeedback(
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

  removeTrack = async () => {
    const {
      listen,
      currentUser,
      isCurrentUser,
      removeTrackFromPlaylist,
    } = this.props;

    if (isCurrentUser && currentUser?.auth_token) {
      const listenedAt = _get(listen, "listened_at");
      const recordingMSID = _get(
        listen,
        "track_metadata.additional_info.recording_msid"
      );

      try {
        const status = await this.APIService.deleteListen(
          currentUser.auth_token,
          recordingMSID,
          listenedAt
        );
        if (status === 200) {
          this.setState({ isDeleted: true });

          // wait for the animation to finish
          setTimeout(function () {
            removeTrackFromPlaylist(listen);
          }, 1000);
        }
      } catch (error) {
        this.handleError(error, "Error while deleting listen");
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

  handleListenedAt = () => {
    const { listen } = this.props;
    return (
      <span
        className="listen-time text-center text-muted"
        title={
          listen.listened_at_iso?.toString() ||
          new Date(listen.listened_at * 1000).toISOString()
        }
      >
        {listen.listened_at_iso
          ? timeago.ago(listen.listened_at_iso)
          : timeago.ago(listen.listened_at * 1000)}
      </span>
    );
  };

  handleListenedAtMobileView = () => {
    const { listen } = this.props;
    return (
      <span
        className="listen-time text-muted"
        title={
          listen.listened_at_iso?.toString() ||
          new Date(listen.listened_at * 1000).toISOString()
        }
      >
        {`
      ${
        listen.listened_at_iso
          ? timeago.ago(listen.listened_at_iso, true)
          : timeago.ago(listen.listened_at * 1000, true)
      }
      `}
        ago &#8212; &nbsp;
      </span>
    );
  };

  render() {
    const { listen, isCurrentUser } = this.props;
    const { feedback, isDeleted } = this.state;

    return (
      <Card
        onDoubleClick={this.playListen}
        className={`listen-card row ${isDeleted ? " deleted" : ""}`}
      >
        <div className="col-xs-9">
          <MediaQuery minWidth={768}>
            <div className="col-xs-9">
              <div className="track-details">
                <p title={listen.track_metadata.track_name}>
                  {getTrackLink(listen)}
                </p>
                <p>
                  <small
                    className="text-muted"
                    title={listen.track_metadata.artist_name}
                  >
                    {getArtistLink(listen)}
                  </small>
                </p>
              </div>
            </div>
            <div className="col-xs-3">{this.handleListenedAt()}</div>
          </MediaQuery>
          <MediaQuery maxWidth={767}>
            <div className="col-xs-12">
              <div className="track-details">
                <p title={listen.track_metadata.track_name}>
                  {getTrackLink(listen)}
                </p>
                <p>
                  <small
                    className="text-muted"
                    title={listen.track_metadata.artist_name}
                  >
                    {this.handleListenedAtMobileView()}
                    {getArtistLink(listen)}
                  </small>
                </p>
              </div>
            </div>
          </MediaQuery>
        </div>
        <div className="col-xs-3 text-center">
          <div className="listen-controls">
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
                title="Remove from playlist"
                action={this.removeTrack}
              />
            </ul>
          </div>
        </div>
      </Card>
    );
  }
}
