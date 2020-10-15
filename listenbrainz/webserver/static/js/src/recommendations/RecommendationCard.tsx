import * as React from "react";
import { get as _get } from "lodash";
import { faEllipsisV } from "@fortawesome/free-solid-svg-icons";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

import { getArtistLink, getTrackLink } from "../utils";
import Card from "../components/Card";

export type RecommendationCardProps = {
  recommendation: Recommendation;
  playRecommendation: (recommendation: Recommendation) => void;
  className?: string;
  isCurrentUser: Boolean;
  currentUser?: ListenBrainzUser;
};

export default class RecommendationCard extends React.Component<
  RecommendationCardProps
> {
  playRecommendation: (recommendation: Recommendation) => void;

  constructor(props: RecommendationCardProps) {
    super(props);

    this.playRecommendation = props.playRecommendation.bind(
      this,
      props.recommendation
    );
  }

  render() {
    const { recommendation, className } = this.props;

    return (
      <Card
        onDoubleClick={this.playRecommendation}
        className={`recommendation-card row ${className}`}
      >
        <div className="col-xs-9">
          <div className="col-xs-11">
            <div className="track-details">
              <p title={recommendation.track_metadata.track_name}>
                {getTrackLink(recommendation)}
              </p>
              <p>
                <small
                  className="text-muted"
                  title={recommendation.track_metadata.artist_name}
                >
                  {getArtistLink(recommendation)}
                </small>
              </p>
            </div>
          </div>
        </div>
        <div className="col-xs-1 text-center">
          <div className="recommendation-controls">
            <>
              <FontAwesomeIcon
                icon={faEllipsisV as IconProp}
                className="dropdown-toggle"
                id="recommendationControlsDropdown"
                data-toggle="dropdown"
                aria-haspopup="true"
                aria-expanded="true"
              />
              <ul
                className="dropdown-menu dropdown-menu-right"
                aria-labelledby="recommendationControlsDropdown"
              >
                <span
                  className="angry"
                  title="I never want to hear this again!"
                >
                  &#128544;
                </span>
                <span className="disappoint" title="I don't like this!">
                  &#128542;
                </span>
                <span className="meh" title="This is a bad recommendation!">
                  &#128529;
                </span>
                <span className="smile" title="I like this!">
                  &#128578;
                </span>
                <span className="laugh" title="I really love this!">
                  &#128516;
                </span>
              </ul>
            </>
          </div>
        </div>
      </Card>
    );
  }
}
