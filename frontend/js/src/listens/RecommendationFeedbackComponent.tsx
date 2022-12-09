import * as React from "react";
import {
  faAngry,
  faFrown,
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
import { IconDefinition } from "@fortawesome/fontawesome-common-types"; // eslint-disable-line import/no-unresolved
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

import { get } from "lodash";
import RecommendationControl from "../recommendations/RecommendationControl";
import GlobalAppContext from "../utils/GlobalAppContext";
import { getRecordingMBID } from "../utils/utils";

export type RecommendationFeedbackComponentProps = {
  newAlert: (
    type: AlertType,
    title: string,
    message: string | JSX.Element
  ) => void;
  listen: BaseListenFormat;
  currentFeedback: RecommendationFeedBack | null;
  updateFeedbackCallback?: (
    recordingMbid: string,
    score: RecommendationFeedBack
  ) => void;
};

export default class RecommendationFeedbackComponent extends React.Component<
  RecommendationFeedbackComponentProps
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  submitRecommendationFeedback = async (rating: RecommendationFeedBack) => {
    const {
      listen,
      updateFeedbackCallback,
      currentFeedback,
      newAlert,
    } = this.props;
    const { APIService, currentUser } = this.context;

    if (currentUser?.auth_token) {
      const recordingMBID = getRecordingMBID(listen);
      if (!recordingMBID) {
        return;
      }
      try {
        let status;
        if (currentFeedback === rating) {
          status = await APIService.deleteRecommendationFeedback(
            currentUser.auth_token,
            recordingMBID
          );
        } else {
          status = await APIService.submitRecommendationFeedback(
            currentUser.auth_token,
            recordingMBID,
            rating
          );
        }
        if (status === 200 && updateFeedbackCallback) {
          updateFeedbackCallback(recordingMBID, rating);
        }
      } catch (error) {
        newAlert(
          "danger",
          "Error while submitting recommendation feedback",
          error?.message ?? error.toString()
        );
      }
    }
  };

  render() {
    const { currentUser } = this.context;
    const { currentFeedback, listen } = this.props;
    const recordingMSID = get(
      listen,
      "track_metadata.additional_info.recording_msid"
    );
    if (!currentUser?.auth_token || !recordingMSID) {
      return null;
    }
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
            action={() => this.submitRecommendationFeedback("hate")}
            cssClass={`hate ${currentFeedback === "hate" ? "selected" : ""}`}
          />
          <RecommendationControl
            iconHover={faFrown}
            icon={faFrownRegular}
            title="I don't like this!"
            action={() => this.submitRecommendationFeedback("dislike")}
            cssClass={`dislike ${
              currentFeedback === "dislike" ? "selected" : ""
            }`}
          />
          <RecommendationControl
            iconHover={faSmileBeam}
            icon={faSmileBeamRegular}
            title="I like this!"
            action={() => this.submitRecommendationFeedback("like")}
            cssClass={`like ${currentFeedback === "like" ? "selected" : ""}`}
          />
          <RecommendationControl
            iconHover={faGrinStars}
            icon={faGrinStarsRegular}
            title="I really love this!"
            action={() => this.submitRecommendationFeedback("love")}
            cssClass={`love ${currentFeedback === "love" ? "selected" : ""}`}
          />
        </ul>
      </div>
    );
  }
}
