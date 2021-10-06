import * as React from "react";
import {
  faAngry,
  faFrown,
  faMeh,
  faSmileBeam,
  faGrinStars,
} from "@fortawesome/free-solid-svg-icons";

import {
  faThumbsUp as faThumbsUpRegular,
  faAngry as faAngryRegular,
  faFrown as faFrownRegular,
  faSmileBeam as faSmileBeamRegular,
  faGrinStars as faGrinStarsRegular,
} from "@fortawesome/free-regular-svg-icons";

import { get as _get, isEqual, isNil } from "lodash";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { IconDefinition } from "@fortawesome/fontawesome-common-types"; // eslint-disable-line import/no-unresolved
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import RecommendationControl from "./RecommendationControl";

import { getArtistLink, getTrackLink } from "../utils";
import Card from "../components/Card";
import GlobalAppContext from "../GlobalAppContext";

export type RecommendationCardProps = {
  recommendation: Recommendation;
  currentFeedback: RecommendationFeedBack | null;
  updateFeedback: (
    recordingMbid: string,
    rating: RecommendationFeedBack | null
  ) => void;
  className?: string;
  isCurrentUser: Boolean;
  newAlert: (
    alertType: AlertType,
    title: string,
    message: string | JSX.Element
  ) => void;
};

type RecommendationCardState = {
  isCurrentListen: Boolean;
};

export default class RecommendationCard extends React.Component<
  RecommendationCardProps,
  RecommendationCardState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  constructor(props: RecommendationCardProps) {
    super(props);
    this.state = { isCurrentListen: false };
  }

  componentDidMount() {
    window.addEventListener("message", this.receiveBrainzPlayerMessage);
  }

  componentWillUnmount() {
    window.removeEventListener("message", this.receiveBrainzPlayerMessage);
  }

  /** React to events sent by BrainzPlayer */
  receiveBrainzPlayerMessage = (event: MessageEvent) => {
    if (event.origin !== window.location.origin) {
      // Reveived postMessage from different origin, ignoring it
      return;
    }
    const { type, payload } = event.data;
    switch (type) {
      case "current-listen-change":
        this.onCurrentListenChange(payload);
        break;
      default:
      // do nothing
    }
  };

  onCurrentListenChange = (newListen: BaseListenFormat) => {
    this.setState({ isCurrentListen: this.isCurrentListen(newListen) });
  };

  isCurrentListen = (element: BaseListenFormat): boolean => {
    const { recommendation } = this.props;
    if (isNil(recommendation)) {
      return false;
    }
    return isEqual(element, recommendation);
  };

  playRecommendation = () => {
    const { recommendation } = this.props;
    const { isCurrentListen } = this.state;
    if (isCurrentListen) {
      return;
    }
    window.postMessage(
      { brainzplayer_event: "play-listen", payload: recommendation },
      window.location.origin
    );
  };

  submitFeedback = async (rating: RecommendationFeedBack) => {
    const { APIService, currentUser } = this.context;
    const { recommendation, isCurrentUser, updateFeedback } = this.props;
    if (isCurrentUser && currentUser?.auth_token) {
      const recordingMBID = _get(
        recommendation,
        "track_metadata.additional_info.recording_mbid"
      );
      try {
        const status = await APIService.submitRecommendationFeedback(
          currentUser.auth_token,
          recordingMBID,
          rating
        );
        if (status === 200) {
          updateFeedback(recordingMBID, rating);
        }
      } catch (error) {
        this.handleError(
          `Error while submitting recommendation feedback - ${error.message}`
        );
      }
    }
  };

  deleteFeedback = async () => {
    const { APIService, currentUser } = this.context;
    const { recommendation, isCurrentUser, updateFeedback } = this.props;
    if (isCurrentUser && currentUser?.auth_token) {
      const recordingMBID = _get(
        recommendation,
        "track_metadata.additional_info.recording_mbid"
      );
      try {
        const status = await APIService.deleteRecommendationFeedback(
          currentUser.auth_token,
          recordingMBID
        );
        if (status === 200) {
          updateFeedback(recordingMBID, null);
        }
      } catch (error) {
        this.handleError(
          `Error while deleting recommendation feedback - ${error.message}`
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
      currentFeedback,
      recommendation,
      className,
      isCurrentUser,
    } = this.props;
    const { isCurrentListen } = this.state;
    const { currentUser } = this.context;
    let icon: IconDefinition;
    let text: string;
    switch (currentFeedback) {
      case "hate":
        icon = faAngry;
        text = "Hate";
        break;
      case "dislike":
        icon = faFrown;
        text = "Dislike";
        break;
      case "like":
        icon = faSmileBeam;
        text = "Like";
        break;
      case "love":
        icon = faGrinStars;
        text = "Love";
        break;
      default:
        icon = faThumbsUpRegular;
        text = "Like";
        break;
    }

    return (
      <Card
        onDoubleClick={this.playRecommendation}
        className={`recommendation-card row ${
          isCurrentListen ? "current-recommendation" : ""
        } ${className || ""}`}
      >
        <div className="track-details">
          <div title={recommendation.track_metadata?.track_name}>
            {getTrackLink(recommendation)}
          </div>
          <small
            className="text-muted"
            title={recommendation.track_metadata?.artist_name}
          >
            {getArtistLink(recommendation)}
          </small>
        </div>
        {isCurrentUser && currentUser?.auth_token && (
          <div className="recommendation-controls">
            <button
              className={`btn ${currentFeedback}`}
              id="recommendationControlsDropdown"
              data-toggle="dropdown"
              aria-haspopup="true"
              aria-expanded="true"
              type="button"
            >
              <FontAwesomeIcon icon={icon as IconProp} /> {text}
            </button>
            <ul
              className="dropdown-menu dropdown-menu-right"
              aria-labelledby="recommendationControlsDropdown"
            >
              <RecommendationControl
                iconHover={faAngry}
                icon={faAngryRegular}
                title="I never want to hear this again!"
                action={() =>
                  currentFeedback === "hate"
                    ? this.deleteFeedback()
                    : this.submitFeedback("hate")
                }
                cssClass={`hate ${
                  currentFeedback === "hate" ? "selected" : ""
                }`}
              />
              <RecommendationControl
                iconHover={faFrown}
                icon={faFrownRegular}
                title="I don't like this!"
                action={() =>
                  currentFeedback === "dislike"
                    ? this.deleteFeedback()
                    : this.submitFeedback("dislike")
                }
                cssClass={`dislike ${
                  currentFeedback === "dislike" ? "selected" : ""
                }`}
              />
              <RecommendationControl
                iconHover={faSmileBeam}
                icon={faSmileBeamRegular}
                title="I like this!"
                action={() =>
                  currentFeedback === "like"
                    ? this.deleteFeedback()
                    : this.submitFeedback("like")
                }
                cssClass={`like ${
                  currentFeedback === "like" ? "selected" : ""
                }`}
              />
              <RecommendationControl
                iconHover={faGrinStars}
                icon={faGrinStarsRegular}
                title="I really love this!"
                action={() =>
                  currentFeedback === "love"
                    ? this.deleteFeedback()
                    : this.submitFeedback("love")
                }
                cssClass={`love ${
                  currentFeedback === "love" ? "selected" : ""
                }`}
              />
            </ul>
          </div>
        )}
      </Card>
    );
  }
}
