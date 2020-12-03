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
  faMeh as faMehRegular,
  faSmileBeam as faSmileBeamRegular,
  faGrinStars as faGrinStarsRegular,
} from "@fortawesome/free-regular-svg-icons";

import { get as _get } from "lodash";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { IconDefinition } from "@fortawesome/fontawesome-common-types"; // eslint-disable-line import/no-unresolved
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import RecommendationControl from "./RecommendationControl";

import { getArtistLink, getTrackLink } from "../utils";
import Card from "../components/Card";
import APIService from "../APIService";

export type RecommendationCardProps = {
  apiUrl: string;
  recommendation: Recommendation;
  playRecommendation: (recommendation: Recommendation) => void;
  currentFeedback: RecommendationFeedBack | null;
  updateFeedback: (
    recordingMbid: string,
    rating: RecommendationFeedBack | null
  ) => void;
  className?: string;
  isCurrentUser: Boolean;
  currentUser?: ListenBrainzUser;
  newAlert: (
    alertType: AlertType,
    title: string,
    message: string | JSX.Element
  ) => void;
};

export default class RecommendationCard extends React.Component<
  RecommendationCardProps
> {
  APIService: APIService;
  playRecommendation: (recommendation: Recommendation) => void;

  constructor(props: RecommendationCardProps) {
    super(props);

    this.APIService = new APIService(
      props.apiUrl || `${window.location.origin}/1`
    );

    this.playRecommendation = props.playRecommendation.bind(
      this,
      props.recommendation
    );
  }

  submitFeedback = async (rating: RecommendationFeedBack) => {
    const {
      recommendation,
      currentUser,
      isCurrentUser,
      updateFeedback,
    } = this.props;
    if (isCurrentUser && currentUser?.auth_token) {
      const recordingMBID = _get(
        recommendation,
        "track_metadata.additional_info.recording_mbid"
      );
      try {
        const status = await this.APIService.submitRecommendationFeedback(
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
    const {
      recommendation,
      currentUser,
      isCurrentUser,
      updateFeedback,
    } = this.props;
    if (isCurrentUser && currentUser?.auth_token) {
      const recordingMBID = _get(
        recommendation,
        "track_metadata.additional_info.recording_mbid"
      );
      try {
        const status = await this.APIService.deleteRecommendationFeedback(
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
      currentUser,
    } = this.props;
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
      case "bad_recommendation":
        icon = faMeh;
        text = "Bad";
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
        className={`recommendation-card row ${className}`}
      >
        <div className="track-details">
          <div title={recommendation.track_metadata.track_name}>
            {getTrackLink(recommendation)}
          </div>
          <small
            className="text-muted"
            title={recommendation.track_metadata.artist_name}
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
                iconHover={faMeh}
                icon={faMehRegular}
                title="This is a bad recommendation!"
                action={() =>
                  currentFeedback === "bad_recommendation"
                    ? this.deleteFeedback()
                    : this.submitFeedback("bad_recommendation")
                }
                cssClass={`bad_recommendation ${
                  currentFeedback === "bad_recommendation" ? "selected" : ""
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
