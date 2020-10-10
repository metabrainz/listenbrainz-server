import * as React from "react";
import { get as _get } from "lodash";
import MediaQuery from "react-responsive";
import {
  faAngry,
  faSadCry,
  faMeh,
  faSmileBeam,
  faLaughBeam,
} from "@fortawesome/free-solid-svg-icons";

import { getArtistLink, getTrackLink } from "../utils";
import Card from "../components/Card";
import ListenControl from "../listens/ListenControl";

export const DEFAULT_COVER_ART_URL = "/static/img/default_cover_art.png";

export type RecommendationCardProps = {
  recommendation: Recommendation;
  playRecommendation: (recommendation: Recommendation) => void;
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
  playRecommendation: (recommendation: Recommendation) => void;

  constructor(props: RecommendationCardProps) {
    super(props);

    this.playRecommendation = props.playRecommendation.bind(this, props.recommendation);
  }


  render() {
    const { recommendation } = this.props;

    return (
      <Card
        onDoubleClick={this.playRecommendation}
        className="listen-card row current-listen"
      >
        <div className="col-xs-9">
          <MediaQuery minWidth={768}>
            <div className="col-xs-9">
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
          </MediaQuery>
          <MediaQuery maxWidth={767}>
            <div className="col-xs-12">
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
          </MediaQuery>
        </div>
        <div
          className="col-xs-3 text-center"
        >
            <div className="listen-controls">
                <>
                <ListenControl
                    icon={faAngry}
                    title="I never want to hear this again!"
                />
                <ListenControl
                    icon={faSadCry}
                    title="I don't like this!"
                />
                <ListenControl
                    icon={faMeh}
                    title="This is a bad recommendation!"
                />
                <ListenControl
                    icon={faSmileBeam}
                    title="I like this!"
                />
                <ListenControl
                    icon={faLaughBeam}
                    title="I really love this!"
                />
                </>
            </div>
        </div>
      </Card>
    );
  }
}
