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
  PinnedRecording: PinnedRecording;
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
    const { PinnedRecording } = this.props;
    const pinnedUntilTime: Date = new Date(PinnedRecording.pinned_until * 1000);

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
    const { PinnedRecording, isCurrentUser, newAlert } = this.props;
    const { APIService, currentUser } = this.context;

    if (isCurrentUser && currentUser?.auth_token) {
      try {
        const status = await APIService.unpinRecording(currentUser.auth_token);
        if (status === 200) {
          this.setState({ currentlyPinned: false });
          newAlert(
            "success",
            `You unpinned a recording.`,
            `${PinnedRecording.track_metadata.artist_name} - ${PinnedRecording.track_metadata.track_name}`
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
    const { PinnedRecording, isCurrentUser, userName } = this.props;
    const { currentlyPinned, isDeleted } = this.state;
    const { track_name } = PinnedRecording.track_metadata;
    const { artist_name } = PinnedRecording.track_metadata;

    return (
      <Card
        className={`pinned-recording-card row${
          currentlyPinned ? " currently-pinned" : ""
        }
        ${isDeleted ? " deleted" : ""}`}
      >
        <div className={`${isCurrentUser ? " col-xs-9" : " col-xs-12"}`}>
          <MediaQuery minWidth={768}>
            <div className="col-xs-8">
              <div className="pin-details">
                <span
                  className={`${
                    currentlyPinned ? " pin-title text-muted" : "hidden"
                  }`}
                >
                  <FontAwesomeIcon icon={faThumbtack as IconProp} />{" "}
                  {isCurrentUser ? "My " : `${userName}'s `} Pinned Recording
                  <br />
                </span>
                <p title={track_name}>{track_name}</p>
                <p>
                  <small title={artist_name}>{artist_name}</small>
                </p>
                {PinnedRecording.blurb_content && (
                  <p>
                    <div
                      className="blurb-content"
                      title={PinnedRecording.blurb_content}
                    >
                      &quot;{PinnedRecording.blurb_content}&quot;
                    </div>
                  </p>
                )}
              </div>
            </div>
            <div className="col-xs-4">
              <span
                className="pinned-recording-time text-center text-muted-less"
                title={new Date(PinnedRecording.created * 1000).toISOString()}
              >
                {preciseTimestamp(PinnedRecording.created * 1000)}
              </span>
            </div>
          </MediaQuery>
          <MediaQuery maxWidth={767}>
            <div className="col-xs-12">
              <div className="pin-details">
                {currentlyPinned && (
                  <small className="pin-title text-muted">
                    <FontAwesomeIcon icon={faThumbtack as IconProp} />{" "}
                    {isCurrentUser ? "My " : `${userName}'s `} Pinned Recording
                    <br />
                  </small>
                )}
                <p title={track_name}>{track_name}</p>
                <p>
                  <small title={artist_name}>
                    <span
                      className="pinned-recording-time text-center text-muted-less"
                      title={new Date(
                        PinnedRecording.created * 1000
                      ).toISOString()}
                    >
                      {preciseTimestamp(PinnedRecording.created * 1000)}
                      &nbsp; &#8212; &nbsp;
                    </span>
                    {artist_name}
                  </small>
                </p>
                {PinnedRecording.blurb_content && (
                  <p>
                    <div
                      className="blurb-content"
                      title={PinnedRecording.blurb_content}
                    >
                      &quot;{PinnedRecording.blurb_content}&quot;
                    </div>
                  </p>
                )}
              </div>
            </div>
          </MediaQuery>
        </div>
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
                action={() => this.deletePin(PinnedRecording.row_id)}
              />
            </ul>
          </div>
        </div>
      </Card>
    );
  }
}
