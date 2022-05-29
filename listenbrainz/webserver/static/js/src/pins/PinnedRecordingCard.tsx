import * as React from "react";
import { isEqual, isNil } from "lodash";
import MediaQuery from "react-responsive";
import { faEllipsisV, faThumbtack } from "@fortawesome/free-solid-svg-icons";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

import {
  preciseTimestamp,
  getListenablePin,
  pinnedRecordingToListen,
  getArtistName,
  getTrackName,
} from "../utils/utils";
import GlobalAppContext from "../utils/GlobalAppContext";
import Card from "../components/Card";
import ListenControl from "../listens/ListenControl";
import ListenCard from "../listens/ListenCard";

export const DEFAULT_COVER_ART_URL = "/static/img/default_cover_art.png";

export type PinnedRecordingCardProps = {
  userName: string;
  pinnedRecording: PinnedRecording;
  currentFeedback?: ListenFeedBack | null;
  // Only used when not passing a custom feedbackComponent
  updateFeedbackCallback?: (
    recordingMsid: string,
    score: ListenFeedBack | RecommendationFeedBack,
    recordingMbid?: string
  ) => void;
  className?: string;
  isCurrentUser: Boolean;
  removePinFromPinsList: (pin: PinnedRecording) => void;
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
    this.state = {
      currentlyPinned: this.determineIfCurrentlyPinned(),
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
            `${getArtistName(pinnedRecording)} - ${getTrackName(
              pinnedRecording
            )}`
          );
        }
      } catch (error) {
        this.handleError(error, "Error while unpinning recording");
      }
    }
  };

  deletePin = async (pin: PinnedRecording) => {
    const { isCurrentUser, removePinFromPinsList } = this.props;
    const { APIService, currentUser } = this.context;

    if (isCurrentUser && currentUser?.auth_token) {
      try {
        const status = await APIService.deletePin(
          currentUser.auth_token,
          pin.row_id
        );
        if (status === 200) {
          this.setState({ currentlyPinned: false });
          this.setState({ isDeleted: true });

          // wait for the animation to finish
          setTimeout(function removeListen() {
            removePinFromPinsList(pin);
          }, 1000);
        }
      } catch (error) {
        this.handleError(error, "Error while deleting pin");
      }
    }
  };

  render() {
    const {
      pinnedRecording,
      newAlert,
      currentFeedback,
      updateFeedbackCallback,
    } = this.props;
    const { currentlyPinned, isDeleted } = this.state;

    const thumbnail = currentlyPinned ? (
      <div className="pinned-recording-icon">
        <span className="icon">
          <FontAwesomeIcon icon={faThumbtack as IconProp} />
        </span>
        <span className="small">Pinned</span>
      </div>
    ) : undefined;

    const blurb = pinnedRecording.blurb_content ? (
      <div className="blurb-content" title={pinnedRecording.blurb_content}>
        &quot;{pinnedRecording.blurb_content}&quot;
      </div>
    ) : undefined;

    const additionalMenuItems = (
      <>
        {currentlyPinned && (
          <ListenControl
            title="Unpin"
            text="Unpin"
            action={() => this.unpinRecording()}
          />
        )}
        <ListenControl
          title="Delete Pin"
          text="Delete Pin"
          action={() => this.deletePin(pinnedRecording)}
        />
      </>
    );
    const cssClasses = ["pinned-recording-card"];
    if (currentlyPinned) {
      cssClasses.push("currently-pinned");
    }
    if (isDeleted) {
      cssClasses.push("deleted");
    }
    return (
      <ListenCard
        className={cssClasses.join(" ")}
        listen={pinnedRecordingToListen(pinnedRecording)}
        currentFeedback={currentFeedback}
        updateFeedbackCallback={updateFeedbackCallback}
        showTimestamp
        showUsername={false}
        newAlert={newAlert}
        additionalMenuItems={additionalMenuItems}
        additionalContent={blurb}
        thumbnail={thumbnail}
      />
    );
  }
}
