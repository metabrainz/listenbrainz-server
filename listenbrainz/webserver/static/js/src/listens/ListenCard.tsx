import * as timeago from "time-ago";

import * as React from "react";
import { get as _get } from "lodash";
import MediaQuery from "react-responsive";
import {
  faMusic,
  faHeart,
  faHeartBroken,
} from "@fortawesome/free-solid-svg-icons";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

import { getArtistLink, getTrackLink } from "../utils";
import Card from "../components/Card";
import APIService from "../APIService";

export const DEFAULT_COVER_ART_URL = "/static/img/default_cover_art.png";

export type ListenCardProps = {
  listen: Listen;
  mode: ListensListMode;
  className?: string;
  playListen: (listen: Listen) => void;
};

export default class ListenCard extends React.Component<ListenCardProps> {
  playListen: (listen: Listen) => void;

  constructor(props: ListenCardProps) {
    super(props);

    this.playListen = props.playListen.bind(this, props.listen);
  }

  render() {
    const { listen, mode, className } = this.props;

    return (
      <Card
        onDoubleClick={this.playListen}
        className={`listen-card row ${className}`}
      >
        <div className="col-xs-9">
          <MediaQuery minWidth={768}>
            <div className="col-xs-9">
              <div className="track-details">
                <p title={listen.track_metadata.track_name}>
                  {getTrackLink(listen)}
                </p>
                <p>
                  <small
                    className="text-muted"
                    title={listen.track_metadata.artist_name}
                  >
                    {getArtistLink(listen)}
                  </small>
                </p>
              </div>
            </div>
            <div className="col-xs-3">
              {listen.playing_now ? (
                <span className="listen-time text-center text-muted">
                  <FontAwesomeIcon icon={faMusic as IconProp} /> Playing now
                </span>
              ) : (
                <span
                  className="listen-time text-center text-muted"
                  title={
                    listen.listened_at_iso?.toString() ||
                    new Date(listen.listened_at * 1000).toISOString()
                  }
                >
                  {listen.listened_at_iso
                    ? timeago.ago(listen.listened_at_iso)
                    : timeago.ago(listen.listened_at * 1000)}
                </span>
              )}
            </div>
          </MediaQuery>
          <MediaQuery maxWidth={767}>
            <div className="col-xs-12">
              <div className="track-details">
                <p title={listen.track_metadata.track_name}>
                  {getTrackLink(listen)}
                </p>
                <p>
                  <small
                    className="text-muted"
                    title={listen.track_metadata.artist_name}
                  >
                    {listen.playing_now ? (
                      <span className="listen-time text-muted">
                        <FontAwesomeIcon icon={faMusic as IconProp} /> Playing
                        now
                      </span>
                    ) : (
                      <span
                        className="listen-time text-muted"
                        title={
                          listen.listened_at_iso?.toString() ||
                          new Date(listen.listened_at * 1000).toISOString()
                        }
                      >
                        {`
                      ${
                        listen.listened_at_iso
                          ? timeago.ago(listen.listened_at_iso, true)
                          : timeago.ago(listen.listened_at * 1000, true)
                      }
                      `}
                        ago &#8212;
                      </span>
                    )}

                    {` ${getArtistLink(listen)}`}
                  </small>
                </p>
              </div>
            </div>
          </MediaQuery>
        </div>
        <div className="col-xs-3 text-center">
          {mode === "follow" || mode === "recent" ? (
            <a
              href={`/user/${listen.user_name}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              {listen.user_name}
            </a>
          ) : (
            <div />
          )}
        </div>
      </Card>
    );
  }
}
