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
import { throttle } from "lodash";
import { getPageProps } from "../utils/utils";
import ErrorBoundary from "../utils/ErrorBoundary";
import GlobalAppContext from "../utils/GlobalAppContext";
import withAlertNotifications from "../notifications/AlertNotificationsHOC";
import NumberCounter from "./NumberCounter";
import Blob from "./Blob";

type HomePageProps = {
  listenCount: number;
  artistCount: number;
};

function HomePage({ listenCount, artistCount }: HomePageProps) {
  const homepageUpperRef = React.useRef<HTMLDivElement>(null);
  const homepageLowerRef = React.useRef<HTMLDivElement>(null);

  const [windowHeight, setWindowHeight] = React.useState(window.innerHeight);

  React.useEffect(() => {
    const handleResize = throttle(
      () => {
        setWindowHeight(window.innerHeight);
      },
      300,
      { leading: true }
    );

    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  const createAccountButton = (
    <a
      className="create-account-button"
      href={`https://musicbrainz.org/register?returnto=${window.document.location.href}`}
    >
      Create Account
    </a>
  );
  // Calculate available screen real estate
  // This allows us to ensure that each page takes full height taking mobile browser toolbars into account
  const styles = {
    "--vh": windowHeight * 0.01,
  } as React.CSSProperties;
  return (
    <div id="homepage-container" style={styles}>
      <div className="homepage-upper" ref={homepageUpperRef}>
        <Blob
          width={200}
          height={200}
          randomness={1.5}
          className="homepage-upper-vector-1"
          style={{ animationDelay: "-10s" }}
        />
        <Blob
          width={300}
          height={300}
          randomness={2.5}
          className="homepage-upper-vector-2"
          style={{ animationDelay: "-7s" }}
        />
        <Blob
          width={100}
          height={100}
          randomness={2}
          className="homepage-upper-vector-3"
          style={{
            animationDelay: "-3s",
            animationDuration: "10s",
          }}
        />
        <Blob
          width={350}
          height={350}
          randomness={2}
          className="homepage-upper-vector-4"
          style={{
            animationDuration: "30s",
            width: "350px",
            height: "200px",
          }}
        />
        <img
          className="homepage-upper-headphone"
          src="/static/img/homepage/LB-Headphone.png"
          alt="ListenBrainz Logo"
        />
        <div className="homepage-upper-grey-box" />

        <h1 className="listen-container">
          <NumberCounter count={listenCount} />
          global listens.
        </h1>
        <div className="homepage-info">
          <h1>
            Listen together
            <br />
            with ListenBrainz
          </h1>

          {createAccountButton}

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

        <Blob
          width={250}
          height={250}
          randomness={1.5}
          className="homepage-lower-vector-1"
        />
        <Blob
          width={300}
          height={300}
          randomness={2}
          className="homepage-lower-vector-2"
          style={{ animationDelay: "-7s" }}
        />
        <Blob
          width={100}
          height={100}
          randomness={1.6}
          className="homepage-lower-vector-3"
          style={{
            animationDelay: "-3s",
            animationDuration: "10s",
          }}
        />
        <Blob
          width={250}
          height={250}
          randomness={1.5}
          className="homepage-lower-vector-4"
        />
        <img
          className="homepage-lower-speaker"
          src="/static/img/homepage/LB-Speaker.png"
          alt="ListenBrainz Logo"
        />
        <div className="homepage-lower-grey-box" />

        <h1 className="listen-container">
          Dig deeper with
          <div id="artist-count-container">
            <NumberCounter count={artistCount} /> artists.
          </div>
        </h1>
        <div className="homepage-info">
          <h1>
            Connect your music
            <br />
            with ListenBrainz
          </h1>

          {createAccountButton}

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

document.addEventListener("DOMContentLoaded", async () => {
  const {
    domContainer,
    reactProps,
    globalAppContext,
    sentryProps,
  } = await getPageProps();
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
