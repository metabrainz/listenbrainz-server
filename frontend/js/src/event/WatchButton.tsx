import * as React from "react";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faCheck,
  faEye,
  faEyeSlash,
  faExclamationTriangle,
} from "@fortawesome/free-solid-svg-icons";
import GlobalAppContext from "../utils/GlobalAppContext";

type WatchButtonProps = {
  eventMBID: string;
  loggedInUserWatchesEvent: boolean;
  updateWatchedEvents?: (
    eventMBID: string,
    action: "watch" | "unwatch"
  ) => void;
};

type WatchButtonState = {
  loggedInUserWatchesEvent: boolean;
  justWatched: boolean;
  hover: boolean;
  error: boolean;
};

class WatchButton extends React.Component<WatchButtonProps, WatchButtonState> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  constructor(props: WatchButtonProps) {
    super(props);
    this.state = {
      loggedInUserWatchesEvent: props.loggedInUserWatchesEvent,
      hover: false,
      justWatched: false,
      error: false,
    };
  }

  componentDidUpdate(prevProps: WatchButtonProps) {
    const { loggedInUserWatchesEvent } = this.props;
    if (prevProps.loggedInUserWatchesEvent !== loggedInUserWatchesEvent) {
      this.setState({ loggedInUserWatchesEvent });
    }
  }

  setHover = (value: boolean) => {
    this.setState({ hover: value, justWatched: false });
  };

  handleButtonClick = () => {
    const { loggedInUserWatchesEvent } = this.state;
    if (loggedInUserWatchesEvent) {
      this.unwatchEvent();
    } else {
      this.watchEvent();
    }
  };

  watchEvent = () => {
    const { eventMBID, updateWatchedEvents } = this.props;
    const { APIService, currentUser } = this.context;

    APIService.watchEvent(eventMBID, currentUser?.auth_token!).then(
      ({ status }) => {
        if (status === 200) {
          this.setState({ loggedInUserWatchesEvent: true, justWatched: true });
          if (updateWatchedEvents) {
            updateWatchedEvents(eventMBID, "watch");
          }
        } else {
          this.setState({ error: true });
        }
      }
    );
  };

  unwatchEvent = () => {
    const { eventMBID, updateWatchedEvents } = this.props;
    const { APIService, currentUser } = this.context;

    APIService.unwatchEvent(eventMBID, currentUser?.auth_token!).then(
      ({ status }) => {
        if (status === 200) {
          this.setState({
            loggedInUserWatchesEvent: false,
            justWatched: false,
          });
          if (updateWatchedEvents) {
            updateWatchedEvents(eventMBID, "unwatch");
          }
        } else {
          this.setState({ error: true });
        }
      }
    );
  };

  getButtonDetails = (): {
    buttonIcon: IconProp;
    buttonText: string;
  } => {
    const { error, justWatched, loggedInUserWatchesEvent, hover } = this.state;

    if (error) {
      return {
        buttonIcon: faExclamationTriangle as IconProp,
        buttonText: "Error!!",
      };
    }

    if (justWatched) {
      return {
        buttonIcon: faCheck as IconProp,
        buttonText: "Watching",
      };
    }

    if (loggedInUserWatchesEvent) {
      if (!hover) {
        return {
          buttonIcon: faCheck as IconProp,
          buttonText: "Watching",
        };
      }
      return {
        buttonIcon: faEyeSlash as IconProp,
        buttonText: "Unwatch",
      };
    }

    return {
      buttonIcon: faEye as IconProp,
      buttonText: "Watch",
    };
  };

  render() {
    const { buttonText, buttonIcon } = this.getButtonDetails();
    return (
      <button
        onClick={this.handleButtonClick}
        onMouseEnter={() => this.setHover(true)}
        onMouseLeave={() => this.setHover(false)}
        className="lb-watch-button btn btn-info"
        type="button"
      >
        <FontAwesomeIcon icon={buttonIcon} /> {buttonText}
      </button>
    );
  }
}

export default WatchButton;
