import * as timeago from "time-ago";

import * as React from "react";
import { get as _get } from "lodash";
import {
  faEllipsisV,
  faGripLines,
  faTrashAlt,
} from "@fortawesome/free-solid-svg-icons";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

import { getArtistLink, getTrackLink } from "../utils";
import Card from "../components/Card";
import APIService from "../APIService";
import ListenControl from "../listens/ListenControl";

export const DEFAULT_COVER_ART_URL = "/static/img/default_cover_art.png";

export type PlaylistItemCardProps = {
  apiUrl: string;
  listen: Listen;
  currentFeedback: ListenFeedBack;
  canEdit: Boolean;
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

type PlaylistItemCardState = {
  isDeleted: Boolean;
  feedback: ListenFeedBack;
};

export default class PlaylistItemCard extends React.Component<
  PlaylistItemCardProps,
  PlaylistItemCardState
> {
  APIService: APIService;
  playListen: (listen: Listen) => void;

  constructor(props: PlaylistItemCardProps) {
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

  componentDidUpdate(prevProps: PlaylistItemCardProps) {
    const { currentFeedback } = this.props;
    if (currentFeedback !== prevProps.currentFeedback) {
      this.setState({ feedback: currentFeedback });
    }
  }

  submitFeedback = async (score: ListenFeedBack) => {
    // const { listen, currentUser, canEdit, updateFeedback } = this.props;
    // if (canEdit && currentUser?.auth_token) {
    //   const recordingMSID = _get(
    //     listen,
    //     "track_metadata.additional_info.recording_msid"
    //   );
    //   try {
    //     const status = await this.APIService.submitFeedback(
    //       currentUser.auth_token,
    //       recordingMSID,
    //       score
    //     );
    //     if (status === 200) {
    //       this.setState({ feedback: score });
    //       updateFeedback(recordingMSID, score);
    //     }
    //   } catch (error) {
    //     this.handleError(error, "Error while submitting feedback");
    //   }
    // }
    // We'll want most of this code (at least the API call) on the parent (Playlist) component
    // because we will need the playlist id for bad_recommendation feedback
  };

  removeTrack = async () => {
    const { listen, removeTrackFromPlaylist } = this.props;
    removeTrackFromPlaylist(listen);
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
        className="listen-time"
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

  render() {
    const { listen, canEdit } = this.props;
    const { feedback, isDeleted } = this.state;

    const trackDuration = listen.track_metadata?.additional_info?.duration_ms
      ? (listen.track_metadata.additional_info.duration_ms / 100000).toFixed(2)
      : "?";
    const recordingMbid =
      listen.track_metadata?.additional_info?.recording_msid;
    return (
      <Card
        onDoubleClick={this.playListen}
        className={`playlist-item-card row ${isDeleted ? " deleted" : ""}`}
        data-recording-mbid={recordingMbid}
      >
        <FontAwesomeIcon
          icon={faGripLines as IconProp}
          title="Drag to reorder"
          className="drag-handle text-muted"
        />
        <div className="track-details">
          <div title={listen.track_metadata.track_name}>
            {getTrackLink(listen)}
          </div>
          <small
            className="text-muted"
            title={listen.track_metadata.artist_name}
          >
            {getArtistLink(listen)}
          </small>
        </div>
        <div className="track-duration">{trackDuration}</div>
        {/* <div className="feedback">Feedback component</div> */}
        <div className="addition-details">
          <div>added by monkey{listen.user_name}</div>
          {this.handleListenedAt()}
        </div>

        <div className="dropdown">
          <button
            className="btn btn-link dropdown-toggle"
            type="button"
            id="listenControlsDropdown"
            data-toggle="dropdown"
            aria-haspopup="true"
            aria-expanded="true"
          >
            <FontAwesomeIcon
              icon={faEllipsisV as IconProp}
              title="More options"
            />
          </button>
          <ul
            className="dropdown-menu dropdown-menu-right"
            aria-labelledby="listenControlsDropdown"
          >
            <li>
              <a
                href={`//musicbrainz.org/recording/${recordingMbid}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                Open in MusicBrainz
              </a>
            </li>
            {canEdit && (
              <li onClick={this.removeTrack}>
                <a>
                  <FontAwesomeIcon icon={faTrashAlt as IconProp} /> Remove from
                  playlist
                </a>
              </li>
            )}
          </ul>
        </div>
      </Card>
    );
  }
}
