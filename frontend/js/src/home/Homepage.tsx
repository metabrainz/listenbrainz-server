/*
 * listenbrainz-server - Server for the ListenBrainz project.
 *
 * Copyright (C) 2022 Akshat Tiwari <tiwariakshat03@gmail.com>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc.,
 * 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
 */

import * as React from "react";
import { createRoot } from "react-dom/client";
import * as Sentry from "@sentry/react";
import { Integrations } from "@sentry/tracing";
import { ToastContainer } from "react-toastify";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faSortDown, faSortUp } from "@fortawesome/free-solid-svg-icons";
import { getPageProps } from "../utils/utils";
import ErrorBoundary from "../utils/ErrorBoundary";
import GlobalAppContext from "../utils/GlobalAppContext";
import withAlertNotifications from "../notifications/AlertNotificationsHOC";
import NumberCounter from "./NumberCounter";

type HomePageProps = {
  listenCount: number;
  artistCount: number;
};

function HomePage({ listenCount, artistCount }: HomePageProps) {
  const homepageUpperRef = React.useRef<HTMLDivElement>(null);
  const homepageLowerRef = React.useRef<HTMLDivElement>(null);

  return (
    <div id="homepage-container" role="main">
      <div className="homepage-upper" ref={homepageUpperRef}>
        <img
          className="homepage-upper-vector-1"
          src="/static/img/homepage/Vector-1.svg"
          alt="ListenBrainz Logo"
        />
        <img
          className="homepage-upper-vector-2"
          src="/static/img/homepage/Vector-2.svg"
          alt="ListenBrainz Logo"
        />
        <img
          className="homepage-upper-vector-3"
          src="/static/img/homepage/Vector-3.svg"
          alt="ListenBrainz Logo"
        />
        <img
          className="homepage-upper-vector-4"
          src="/static/img/homepage/Vector-4.svg"
          alt="ListenBrainz Logo"
        />
        <img
          className="homepage-upper-headphone"
          src="/static/img/homepage/LB-Headphone.png"
          alt="ListenBrainz Logo"
        />

        <div className="listen-container">
          <NumberCounter count={listenCount} />
          <h1>global listens.</h1>
        </div>
        <div className="homepage-info">
          <h1>Listen together</h1>
          <h1>with ListenBrainz</h1>

          <button type="button">Create Account</button>
          <div className="homepage-info-text">
            <p>Track, explore, visualise and share the music you listen to.</p>
            <p>Follow your favourites and discover great new music.</p>
          </div>
          <div className="homepage-info-links">
            <a href="/login">Login</a>
            <span>|</span>
            <a href="/about">About ListenBrainz</a>
          </div>
        </div>
        <FontAwesomeIcon
          icon={faSortDown}
          className="homepage-arrow"
          size="3x"
          onClick={() => {
            homepageLowerRef.current?.scrollIntoView({
              behavior: "smooth",
              block: "start",
            });
          }}
        />
      </div>

      <div className="homepage-lower" ref={homepageLowerRef}>
        <FontAwesomeIcon
          icon={faSortUp}
          className="homepage-arrow"
          size="3x"
          onClick={() => {
            homepageUpperRef.current?.scrollIntoView({
              behavior: "smooth",
              block: "start",
            });
          }}
        />
        <img
          className="homepage-lower-vector-1"
          src="/static/img/homepage/Vector-1.svg"
          alt="ListenBrainz Logo"
        />
        <img
          className="homepage-lower-vector-2"
          src="/static/img/homepage/Vector-2.svg"
          alt="ListenBrainz Logo"
        />
        <img
          className="homepage-lower-vector-3"
          src="/static/img/homepage/Vector-3.svg"
          alt="ListenBrainz Logo"
        />
        <img
          className="homepage-lower-speaker"
          src="/static/img/homepage/LB-Speaker.png"
          alt="ListenBrainz Logo"
        />
        <div className="listen-container">
          <h1>Dig deeper with</h1>
          <div id="artist-count-container">
            <NumberCounter count={artistCount} /> <h1>artists.</h1>
          </div>
        </div>
        <div className="homepage-info">
          <h1>Connect your music</h1>
          <h1>with ListenBrainz</h1>

          <button type="button">Create Account</button>
          <div className="homepage-info-text">
            <p>
              Discover your music by linking to the largest open source music
              database.
            </p>
            <p>
              Unlock accurate and detailed metadata for millions of songs,
              albums and artists.
            </p>
          </div>
          <div className="homepage-info-links">
            <a href="/login">Login</a>
            <span>|</span>
            <a href="/about">About ListenBrainz</a>
          </div>
        </div>
      </div>
    </div>
  );
}

document.addEventListener("DOMContentLoaded", () => {
  const {
    domContainer,
    reactProps,
    globalAppContext,
    sentryProps,
  } = getPageProps();
  const { sentry_dsn, sentry_traces_sample_rate } = sentryProps;

  if (sentry_dsn) {
    Sentry.init({
      dsn: sentry_dsn,
      integrations: [new Integrations.BrowserTracing()],
      tracesSampleRate: sentry_traces_sample_rate,
    });
  }

  const { listen_count, artist_count } = reactProps;

  const HomePageWithAlertNotifications = withAlertNotifications(HomePage);

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <ErrorBoundary>
      <ToastContainer
        position="bottom-right"
        autoClose={8000}
        hideProgressBar
      />
      <GlobalAppContext.Provider value={globalAppContext}>
        <HomePageWithAlertNotifications
          listenCount={listen_count}
          artistCount={artist_count}
        />
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});

const container = document.querySelector(".container-fluid");
if (container instanceof HTMLElement) {
  container.style.paddingLeft = "0px";
  container.style.paddingRight = "0px";
}
