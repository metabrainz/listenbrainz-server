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
import ListenControl from "./ListenControl";

export const DEFAULT_COVER_ART_URL = "/static/img/default_cover_art.png";

export type ListenCardProps = {
  user: {
    id?: string;
    name: string;
    auth_token: string;
  };
  apiUrl: string;
  listen: Listen;
  mode: ListensListMode;
  className?: string;
  playListen: (listen: Listen) => void;
};

type ListenCardState = {
  feedback: ListenFeedBack;
};

export default class ListenCard extends React.Component<
  ListenCardProps,
  ListenCardState
> {
  APIService: APIService;
  playListen: (listen: Listen) => void;

  constructor(props: ListenCardProps) {
    super(props);

    this.state = {
      feedback: 0,
    };

    this.APIService = new APIService(
      props.apiUrl || `${window.location.origin}/1`
    );

    this.playListen = props.playListen.bind(this, props.listen);
  }

  handleClickLove = async () => {
    const { feedback } = this.state;
    await this.submitFeedback(feedback === 0 ? 1 : 0);
  };

  handleClickHate = async () => {
    const { feedback } = this.state;
    await this.submitFeedback(feedback === 0 ? -1 : 0);
  };

  submitFeedback = async (score: ListenFeedBack) => {
    const { listen, user } = this.props;
    const { feedback } = this.state;

    const recordingMSID = _get(
      listen,
      "track_metadata.additional_info.recording_msid"
    );

    const status = await this.APIService.submitFeedback(
      user.auth_token,
      recordingMSID,
      score
    );

    if (status === 200) {
      this.setState({ feedback: score });
    }
  };

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
            <div className="listen-controls">
              <ListenControl
                icon={faHeart}
                title="Love"
                action={this.handleClickLove}
              />
              <ListenControl
                icon={faHeartBroken}
                title="Hate"
                action={this.handleClickHate}
              />
            </div>
          )}
        </div>
      </Card>
    );
  }
}
