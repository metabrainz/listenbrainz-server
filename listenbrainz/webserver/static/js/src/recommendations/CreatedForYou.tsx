/* eslint-disable jsx-a11y/anchor-is-valid */
/* eslint-disable camelcase */

import * as React from "react";
import * as ReactDOM from "react-dom";

import { faCircle, faBullhorn } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";

import * as Sentry from "@sentry/react";
import { Integrations } from "@sentry/tracing";
import { Swiper, SwiperSlide } from "swiper/react";
import {
  withAlertNotifications,
  WithAlertNotificationsInjectedProps,
} from "../notifications/AlertNotificationsHOC";
import APIServiceClass from "../utils/APIService";
import GlobalAppContext, { GlobalAppContextT } from "../utils/GlobalAppContext";
import Card from "../components/Card";
import ErrorBoundary from "../utils/ErrorBoundary";
import { getPageProps } from "../utils/utils";

export type UserPlaylistsProps = {
  dailyJamsUrl?: string;
  top100ArtistsUrl?: string;
  similarArtistsUrl?: string;
  user: ListenBrainzUser;
} & WithAlertNotificationsInjectedProps;

export type UserPlaylistsState = {};

export default class UserPlaylists extends React.Component<
  UserPlaylistsProps,
  UserPlaylistsState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  private APIService!: APIServiceClass;

  isCurrentUserPage = () => {
    const { user } = this.props;
    const { currentUser } = this.context;
    return currentUser?.name === user.name;
  };

  render() {
    const {
      user,
      dailyJamsUrl,
      top100ArtistsUrl,
      similarArtistsUrl,
    } = this.props;
    return (
      <div id="created-for-you">
        <h1>Created for {this.isCurrentUserPage() ? "you" : user.name}</h1>
        <p>
          Boy, do we have goodies for you ! We have created these playlists of
          music recommendations just for you, based on you recent listening
          history.
          <br />
          Love it? Hate it? We would love your feedback to help us improve the
          quality of our recommendations:{" "}
          <a
            id="feedback-button"
            href="mailto:support@listenbrainz.org?subject=Recommendations%20feedback"
            type="button"
            className="btn btn-primary"
          >
            <span className="fa-layers icon">
              <FontAwesomeIcon
                icon={faCircle as IconProp}
                transform="grow-10"
              />
              <FontAwesomeIcon
                icon={faBullhorn as IconProp}
                transform="rotate--20"
              />
            </span>{" "}
            Feedback
          </a>
        </p>
        <hr />
        <div id="created-for-you-cards">
          {dailyJamsUrl && (
            <Card className="long-card daily-jams" href={dailyJamsUrl}>
              <h3>Daily Jams</h3>
              <p>
                A daily playlist of recommendations based on your recent
                listening history
              </p>
            </Card>
          )}
          <Card className="long-card fresh-releases" href="">
            <h3>Fresh Releases</h3>
            <p>
              Take a look at what new albums are coming out from your favorite
              artists
            </p>
          </Card>
          {top100ArtistsUrl && (
            <Card className="long-card top-100" href={top100ArtistsUrl}>
              <h3>Top 100 artists</h3>
              <p>A selection of tracks form your favorite artists</p>
            </Card>
          )}
          {similarArtistsUrl && (
            <Card
              className="long-card similar-artists"
              href={similarArtistsUrl}
            >
              <h3>Top 100 artists</h3>
              <p>
                A playlist of tracks from artists similar to what you listen to
              </p>
            </Card>
          )}
        </div>
        <hr />
        <h2>Other playlists</h2>
        <p>
          You have given permission for these bots to generate playlists for
          you. To review your permissions, please go to <a>this page</a>
        </p>
        <div>
          <h4 className="text-center">
            Created by <a>my-great-playlist-bot</a>
          </h4>
          <Swiper
            slidesPerView={4}
            // slidesPerColumn={2}
            spaceBetween={30}
            pagination={{ clickable: true }}
            navigation
          >
            <SwiperSlide>
              <Card className="playlist">
                <h4>My playlist 1</h4>
                <div className="description">A great description here</div>
                <div>
                  Created:{" "}
                  {new Date().toLocaleString(undefined, {
                    // @ts-ignore see https://github.com/microsoft/TypeScript/issues/40806
                    dateStyle: "short",
                  })}
                </div>
              </Card>
            </SwiperSlide>
            <SwiperSlide>
              <Card className="playlist">
                <h4>My playlist 2</h4>
                <div className="description">A great description here</div>
                <div>
                  Created:{" "}
                  {new Date().toLocaleString(undefined, {
                    // @ts-ignore see https://github.com/microsoft/TypeScript/issues/40806
                    dateStyle: "short",
                  })}
                </div>
              </Card>
            </SwiperSlide>
            <SwiperSlide>
              <Card className="playlist">
                <h4>My playlist 3</h4>
                <div className="description">A great description here</div>
                <div>
                  Created:{" "}
                  {new Date().toLocaleString(undefined, {
                    // @ts-ignore see https://github.com/microsoft/TypeScript/issues/40806
                    dateStyle: "short",
                  })}
                </div>
              </Card>
            </SwiperSlide>
            <SwiperSlide>
              <Card className="playlist">
                <h4>My playlist 4</h4>
                <div className="description">A great description here</div>
                <div>
                  Created:{" "}
                  {new Date().toLocaleString(undefined, {
                    // @ts-ignore see https://github.com/microsoft/TypeScript/issues/40806
                    dateStyle: "short",
                  })}
                </div>
              </Card>
            </SwiperSlide>
            <SwiperSlide>
              <Card className="playlist">
                <h4>My playlist 5</h4>
                <div className="description">A great description here</div>
                <div>
                  Created:{" "}
                  {new Date().toLocaleString(undefined, {
                    // @ts-ignore see https://github.com/microsoft/TypeScript/issues/40806
                    dateStyle: "short",
                  })}
                </div>
              </Card>
            </SwiperSlide>
            <SwiperSlide>
              <Card className="playlist">
                <h4>My playlist 6</h4>
                <div className="description">A great description here</div>
                <div>
                  Created:{" "}
                  {new Date().toLocaleString(undefined, {
                    // @ts-ignore see https://github.com/microsoft/TypeScript/issues/40806
                    dateStyle: "short",
                  })}
                </div>
              </Card>
            </SwiperSlide>
          </Swiper>
        </div>
      </div>
    );
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const {
    domContainer,
    reactProps,
    globalReactProps,
    optionalAlerts,
  } = getPageProps();
  const {
    api_url,
    sentry_dsn,
    current_user,
    spotify,
    youtube,
    sentry_traces_sample_rate,
  } = globalReactProps;
  const {
    user,
    daily_jams_url: dailyJamsUrl,
    top_100_artists_rl: top100ArtistsUrl,
    similar_artists_url: similarArtistsUrl,
  } = reactProps;

  if (sentry_dsn) {
    Sentry.init({
      dsn: sentry_dsn,
      integrations: [new Integrations.BrowserTracing()],
      tracesSampleRate: sentry_traces_sample_rate,
    });
  }

  const UserPlaylistsWithAlertNotifications = withAlertNotifications(
    UserPlaylists
  );

  const apiService = new APIServiceClass(
    api_url || `${window.location.origin}/1`
  );

  const globalProps: GlobalAppContextT = {
    APIService: apiService,
    currentUser: current_user,
    spotifyAuth: spotify,
    youtubeAuth: youtube,
  };

  ReactDOM.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalProps}>
        <UserPlaylistsWithAlertNotifications
          dailyJamsUrl={dailyJamsUrl}
          top100ArtistsUrl={top100ArtistsUrl}
          similarArtistsUrl={similarArtistsUrl}
          initialAlerts={optionalAlerts}
          user={user}
        />
      </GlobalAppContext.Provider>
    </ErrorBoundary>,
    domContainer
  );
});
