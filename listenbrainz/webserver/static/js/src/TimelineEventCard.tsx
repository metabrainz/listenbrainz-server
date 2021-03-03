import * as React from "react";
import { faQuestionCircle } from "@fortawesome/free-regular-svg-icons";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

import { getArtistLink, getTrackLink } from "./utils";
import Card from "./components/Card";

export const DEFAULT_COVER_ART_URL = "/static/img/default_cover_art.png";

export type TimelineEventCardProps = {
  className?: string;
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
    const { className, listen } = this.props;

    return (
      <Card
        onDoubleClick={this.playListen}
        className={`listen-card row ${className}`}
      >
        <div className="col-xs-9">
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
          </div>
        </div>
        <div className="col-xs-3">
          <div className="text-muted" title="Why am I seeing this?">
            <FontAwesomeIcon icon={faQuestionCircle as IconProp} />
          </div>
        </div>
      </Card>
    );
  }
}
