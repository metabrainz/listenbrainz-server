import * as React from "react";
import { get as _get } from "lodash";
import MediaQuery from "react-responsive";
import { faEllipsisV, faThumbtack } from "@fortawesome/free-solid-svg-icons";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

import { preciseTimestamp } from "./utils";
import GlobalAppContext from "./GlobalAppContext";
import Card from "./components/Card";
import ListenControl from "./listens/ListenControl";

export const DEFAULT_COVER_ART_URL = "/static/img/default_cover_art.png";

export type PinnedRecordingCardProps = {
  userName: string;
  pinnedRecording: PinnedRecording;
  isCurrentUser: Boolean;
  newAlert: (
    alertType: AlertType,
    title: string,
    message: string | JSX.Element
  ) => void;
};

type PinnedRecordingCardState = {
  currentlyPinned?: Boolean;
  isDeleted: Boolean;
};

export default class PinnedRecordingCard extends React.Component<
  PinnedRecordingCardProps,
  PinnedRecordingCardState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  constructor(props: PinnedRecordingCardProps) {
    super(props);
    const currentlyPinned = this.determineIfCurrentlyPinned();
    this.state = {
      currentlyPinned,
      isDeleted: false,
    };
  }

  determineIfCurrentlyPinned = (): Boolean => {
    const { pinnedRecording } = this.props;
    const pinnedUntilTime: Date = new Date(pinnedRecording.pinned_until * 1000);

    // invalid date
    if (Number.isNaN(pinnedUntilTime.getTime())) {
      return false;
    }
    const currentTime: Date = new Date();

    if (currentTime < pinnedUntilTime) {
      return true;
    }

    return false;
  };

  renderPinTitle = (): JSX.Element => {
    const { currentlyPinned } = this.state;
    const { isCurrentUser, pinnedRecording, userName } = this.props;

    const userText = isCurrentUser ? `${userName}'s` : "My";
    const { track_name } = pinnedRecording.track_metadata;

    return (
      <div>
        {currentlyPinned && (
          <p className="pin-title text-muted">
            <FontAwesomeIcon icon={faThumbtack as IconProp} /> {userText} Pinned
            Recording
          </p>
        )}
        <p title={track_name}>{track_name}</p>
      </div>
    );
  };

  renderPinDate = (): JSX.Element => {
    const { pinnedRecording } = this.props;
    return (
      <div
        className="pinned-recording-time text-center text-muted-less"
        title={new Date(pinnedRecording.created * 1000).toISOString()}
      >
        {preciseTimestamp(pinnedRecording.created * 1000)}
      </div>
    );
  };

  renderBlurbContent = (): JSX.Element | null => {
    const { pinnedRecording } = this.props;
    if (!pinnedRecording.blurb_content) {
      return null;
    }
    return (
      <div className="blurb-content" title={pinnedRecording.blurb_content}>
        &quot;{pinnedRecording.blurb_content}&quot;
      </div>
    );
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

  unpinRecording = async () => {
    const { pinnedRecording, isCurrentUser, newAlert } = this.props;
    const { APIService, currentUser } = this.context;

    if (isCurrentUser && currentUser?.auth_token) {
      try {
        const status = await APIService.unpinRecording(currentUser.auth_token);
        if (status === 200) {
          this.setState({ currentlyPinned: false });
          newAlert(
            "success",
            `You unpinned a recording.`,
            `${pinnedRecording.track_metadata.artist_name} - ${pinnedRecording.track_metadata.track_name}`
          );
        }
      } catch (error) {
        this.handleError(error, "Error while unpinning recording");
      }
    }
  };

  deletePin = async (pinID: number) => {
    const { isCurrentUser } = this.props;
    const { APIService, currentUser } = this.context;

    if (isCurrentUser && currentUser?.auth_token) {
      try {
        const status = await APIService.deletePin(
          currentUser.auth_token,
          pinID
        );
        if (status === 200) {
          this.setState({ currentlyPinned: false });
          this.setState({ isDeleted: true });
        }
      } catch (error) {
        this.handleError(error, "Error while deleting pin");
      }
    }
  };

  render() {
    const { pinnedRecording, isCurrentUser } = this.props;
    const { currentlyPinned, isDeleted } = this.state;
    const { artist_name } = pinnedRecording.track_metadata;

    return (
      <Card
        className={`pinned-recording-card row ${
          currentlyPinned ? "currently-pinned " : ""
        } ${isDeleted ? "deleted " : ""}`}
      >
        <div className={`${isCurrentUser ? " col-xs-9" : " col-xs-12"}`}>
          {/* Desktop browser layout */}
          <MediaQuery minWidth={768}>
            <div className="col-xs-8">
              <div className="pin-details">
                {this.renderPinTitle()}
                <small title={artist_name}>{artist_name}</small>
                {this.renderBlurbContent()}
              </div>
            </div>
            <div className="col-xs-4">{this.renderPinDate()}</div>
          </MediaQuery>

          {/* Mobile device layout */}
          <MediaQuery maxWidth={767}>
            <div className="col-xs-12">
              <div className="pin-details">
                {this.renderPinTitle()}
                <small title={artist_name}>
                  {this.renderPinDate()}
                  &nbsp; &#8212; &nbsp; {artist_name}
                </small>
                {this.renderBlurbContent()}
              </div>
            </div>
          </MediaQuery>
        </div>

        {/* Card controls (only shown if current user is viewing component) */}
        <div
          className={`${isCurrentUser ? " col-xs-3 text-center" : "hidden"}`}
        >
          <div className="pinned-recording-controls">
            <FontAwesomeIcon
              icon={faEllipsisV as IconProp}
              title="Delete"
              className="dropdown-toggle"
              id="pinnedRecordingControlsDropdown"
              data-toggle="dropdown"
              aria-haspopup="true"
              aria-expanded="true"
            />
            <ul
              className="dropdown-menu dropdown-menu-right"
              aria-labelledby="pinnedRecordingControlsDropdown"
            >
              {currentlyPinned && (
                <ListenControl
                  title="Unpin"
                  action={() => this.unpinRecording()}
                />
              )}
              <ListenControl
                title="Delete Pin"
                action={() => this.deletePin(pinnedRecording.row_id)}
              />
            </ul>
          </div>
        </div>
      </Card>
    );
  }
}
