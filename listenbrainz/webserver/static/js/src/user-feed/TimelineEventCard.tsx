import * as React from "react";
import { faQuestionCircle } from "@fortawesome/free-regular-svg-icons";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

import { getArtistLink, getTrackLink } from "../utils";
import Card from "../components/Card";

type TimelineEventCardProps = {
  className?: string;
  additionalDetails: string;
  listen: Listen;
  playListen: (listen: Listen) => void;
  newAlert: (
    alertType: AlertType,
    title: string,
    message: string | JSX.Element
  ) => void;
};

export default class TimelineEventCard extends React.Component<
  TimelineEventCardProps
> {
  playListen: (listen: Listen) => void;

  constructor(props: TimelineEventCardProps) {
    super(props);
    this.playListen = props.playListen.bind(this, props.listen);
  }

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
    const { className, listen, additionalDetails } = this.props;

    return (
      <Card
        onDoubleClick={this.playListen}
        className={`listen-card row ${className} ${
          additionalDetails ? "has-additional-details" : ""
        }`}
      >
        <div className="col-xs-11">
          <div className="track-details">
            <p title={listen.track_metadata?.track_name}>
              {getTrackLink(listen)}
            </p>
            <p>
              <small
                className="text-muted"
                title={listen.track_metadata?.artist_name}
              >
                {getArtistLink(listen)}
              </small>
            </p>
            {additionalDetails && (
              <p
                className="additional-details"
                title={listen.track_metadata?.track_name}
              >
                {additionalDetails}
              </p>
            )}
          </div>
        </div>
        <div className="col-xs-1">
          {/* <div className="text-muted" title="Why am I seeing this?">
            <FontAwesomeIcon icon={faQuestionCircle as IconProp} />
          </div> */}
        </div>
      </Card>
    );
  }
}
