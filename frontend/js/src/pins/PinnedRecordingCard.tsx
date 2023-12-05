import * as React from "react";
import { faThumbtack } from "@fortawesome/free-solid-svg-icons";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { toast } from "react-toastify";
import ListenCard from "../listens/ListenCard";
import ListenControl from "../listens/ListenControl";
import { ToastMsg } from "../notifications/Notifications";
import GlobalAppContext from "../utils/GlobalAppContext";
import {
  getArtistName,
  getTrackName,
  pinnedRecordingToListen,
} from "../utils/utils";

export type PinnedRecordingCardProps = {
  pinnedRecording: PinnedRecording;
  isCurrentUser: Boolean;
  removePinFromPinsList: (pin: PinnedRecording) => void;
};

export type PinnedRecordingCardState = {
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
    if (!error) {
      return;
    }
    toast.error(
      <ToastMsg
        title={title || "Error"}
        message={typeof error === "object" ? error.message : error}
      />,
      { toastId: "pin-error" }
    );
  };

  unpinRecording = async () => {
    const { pinnedRecording, isCurrentUser } = this.props;
    const { APIService, currentUser } = this.context;

    if (isCurrentUser && currentUser?.auth_token) {
      try {
        const status = await APIService.unpinRecording(currentUser.auth_token);
        if (status === 200) {
          this.setState({ currentlyPinned: false });
          toast.success(
            <ToastMsg
              title="You unpinned a track."
              message={`${getArtistName(pinnedRecording)} - ${getTrackName(
                pinnedRecording
              )}`}
            />,
            { toastId: "unpin-success" }
          );
        }
      } catch (error) {
        this.handleError(error, "Error while unpinning track");
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
    const { pinnedRecording } = this.props;
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

    const additionalMenuItems = [];
    if (currentlyPinned) {
      additionalMenuItems.push(
        <ListenControl
          key="Unpin"
          title="Unpin"
          text="Unpin"
          action={() => this.unpinRecording()}
        />
      );
    }
    additionalMenuItems.push(
      <ListenControl
        key="Delete Pin"
        title="Delete Pin"
        text="Delete Pin"
        action={() => this.deletePin(pinnedRecording)}
      />
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
        showTimestamp
        showUsername={false}
        additionalMenuItems={additionalMenuItems}
        additionalContent={blurb}
        customThumbnail={thumbnail}
      />
    );
  }
}
