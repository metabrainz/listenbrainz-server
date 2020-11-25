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
  track: ListenBrainzTrack;
  currentFeedback: ListenFeedBack;
  canEdit: Boolean;
  className?: string;
  currentUser?: ListenBrainzUser;
  playTrack: (track: ListenBrainzTrack) => void;
  removeTrackFromPlaylist: (track: ListenBrainzTrack) => void;
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
  playTrack: (track: ListenBrainzTrack) => void;

  constructor(props: PlaylistItemCardProps) {
    super(props);

    this.state = {
      isDeleted: false,
      feedback: props.currentFeedback || 0,
    };

    this.APIService = new APIService(
      props.apiUrl || `${window.location.origin}/1`
    );

    this.playTrack = props.playTrack.bind(this, props.track);
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
    const { track, removeTrackFromPlaylist } = this.props;
    removeTrackFromPlaylist(track);
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
    const { track } = this.props;
    return (
      <span className="listen-time" title={track.added_at}>
        {timeago.ago(track.added_at)}
      </span>
    );
  };

  render() {
    const { track, canEdit, className } = this.props;
    const { feedback, isDeleted } = this.state;

    const trackDuration = track.duration
      ? (track.duration / 100000).toFixed(2)
      : "?";
    const recordingMbid = track.id;
    return (
      <Card
        onDoubleClick={this.playTrack}
        className={`playlist-item-card row ${className} ${
          isDeleted ? " deleted" : ""
        }`}
        data-recording-mbid={recordingMbid}
      >
        <FontAwesomeIcon
          icon={faGripLines as IconProp}
          title="Drag to reorder"
          className="drag-handle text-muted"
        />
        <div className="track-details">
          <div title={track.title}>
            {/* {getTrackLink(track)} */}
            {track.title}
          </div>
          <small className="text-muted" title={track.creator}>
            {/* {getArtistLink(track)} */}
            {track.creator}
          </small>
        </div>
        <div className="track-duration">{trackDuration}</div>
        {/* <div className="feedback">Feedback component</div> */}
        <div className="addition-details">
          <div>added by {track.added_by}</div>
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
              <li>
                <button onClick={this.removeTrack} type="button">
                  <FontAwesomeIcon icon={faTrashAlt as IconProp} /> Remove from
                  playlist
                </button>
              </li>
            )}
          </ul>
        </div>
      </Card>
    );
  }
}
