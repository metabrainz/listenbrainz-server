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
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faAnglesRight,
  faSortDown,
  faSortUp,
} from "@fortawesome/free-solid-svg-icons";
import { isNumber, throttle } from "lodash";
import { Link, Navigate, useLocation, useSearchParams } from "react-router-dom";
import { Helmet } from "react-helmet";
import { useQuery } from "@tanstack/react-query";
import NumberCounter from "./NumberCounter";
import Blob from "./Blob";
import GlobalAppContext from "../utils/GlobalAppContext";
import { RouteQuery } from "../utils/Loader";

type HomePageProps = {
  listenCount: number;
  artistCount: number;
};

function HomePage() {
  const location = useLocation();
  const { data } = useQuery<HomePageProps>(
    RouteQuery(["home"], location.pathname)
  );
  const { listenCount, artistCount } = data || {};
  const homepageUpperRef = React.useRef<HTMLDivElement>(null);
  const homepageLowerRef = React.useRef<HTMLDivElement>(null);
  const homepageLowerInfoRef = React.useRef<HTMLDivElement>(null);

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
  const loginButton = (
    <Link className="login-button" to="/login/">
      Login
    </Link>
  );
  // Calculate available screen real estate
  // This allows us to ensure that each page takes full height taking mobile browser toolbars into account
  const styles = {
    "--vh": windowHeight * 0.01,
  } as React.CSSProperties;
  return (
    <div id="homepage-container" style={styles}>
      <Helmet>
        <style type="text/css">
          {`.container-react {
            padding-bottom: 0 !important;
          }
          .container-react-main, [role="main"] {
            padding: 0;
            max-width: none !important;
          }
          .footer {
            display: none;
          }`}
        </style>
      </Helmet>
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
        <div
          className="homepage-upper-logo-info"
          onClick={() => {
            homepageLowerInfoRef.current?.scrollIntoView({
              behavior: "smooth",
              block: "start",
            });
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              homepageLowerInfoRef.current?.scrollIntoView({
                behavior: "smooth",
                block: "start",
              });
            }
          }}
          role="button"
          tabIndex={0}
        >
          <img
            className="homepage-upper-logo-info-image"
            src="/static/img/homepage/LB-Open-Source.png"
            alt="ListenBrainz Open Source Logo"
          />
          <img
            className="homepage-upper-logo-info-image"
            src="/static/img/homepage/LB-Data-Provider.png"
            alt="ListenBrainz Data Provider Logo"
          />
          <img
            className="homepage-upper-logo-info-image"
            src="/static/img/homepage/LB-Ethical.png"
            alt="ListenBrainz Ethical Source Logo"
          />
        </div>
        <img
          className="homepage-upper-headphone"
          src="/static/img/homepage/LB-Headphone.png"
          alt="ListenBrainz Logo"
        />
        <div className="homepage-upper-grey-box" />

        {isNumber(listenCount) && listenCount > 0 && (
          <h1 className="listen-container">
            <NumberCounter count={listenCount} />
            global listens.
          </h1>
        )}
        <div className="homepage-info">
          <h1>
            Listen together
            <br />
            with ListenBrainz
          </h1>

          {createAccountButton}
          {loginButton}

          <div className="homepage-info-text">
            <p>Track, explore, visualise and share the music you listen to.</p>
            <p>Follow your favourites and discover great new music.</p>
          </div>
          <div className="homepage-info-links">
            <Link to="/about/">About ListenBrainz</Link>
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

        {isNumber(artistCount) && artistCount > 0 && (
          <h1 className="listen-container">
            Dig deeper with
            <div id="artist-count-container">
              <NumberCounter count={artistCount} /> artists.
            </div>
          </h1>
        )}
        <div className="homepage-info">
          <h1>
            Connect your music
            <br />
            with ListenBrainz
          </h1>

          {createAccountButton}
          {loginButton}

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
            <Link to="/about/">About ListenBrainz</Link>
          </div>
        </div>
        <FontAwesomeIcon
          icon={faSortDown}
          className="homepage-arrow"
          size="3x"
          onClick={() => {
            homepageLowerInfoRef.current?.scrollIntoView({
              behavior: "smooth",
              block: "start",
            });
          }}
        />
      </div>

      <div className="homepage-information" ref={homepageLowerInfoRef}>
        <FontAwesomeIcon
          icon={faSortUp}
          className="homepage-arrow"
          size="3x"
          onClick={() => {
            homepageLowerRef.current?.scrollIntoView({
              behavior: "smooth",
              block: "start",
            });
          }}
        />

        <Blob
          width={200}
          height={200}
          randomness={1.5}
          className="homepage-information-vector-1"
          style={{ animationDelay: "-10s" }}
        />

        <div className="homepage-information-grey-box" />

        <div className="homepage-information-content">
          <div className="info-column">
            <div className="info-icon">
              <img
                src="/static/img/homepage/LB-Open-Source-Info.png"
                alt="Open source"
              />
            </div>
            <h2>Open source</h2>
            <p>
              &quot;Open source is source code that is made freely available for
              possible modification and redistribution... A main principle of
              open source software development is peer production, with products
              such as source code, blueprints, and documentation freely
              available to the public.&quot; -{" "}
              <Link
                to="https://en.wikipedia.org/wiki/Open_source"
                target="_blank"
                rel="noopener noreferrer"
              >
                Wikipedia
              </Link>
            </p>
            <p>
              The ListenBrainz website, the MusicBrainz database, and the music
              and listen data that our users contribute is all open source. This
              means that anyone can view the code, contribute improvements and
              new features, and copy and modify it for their own use.
            </p>
            <p>
              Thousands of people contribute code or data to ListenBrainz and
              its sister projects for no monetary return. Contributors do this
              to further humanity&apos;s global store of knowledge, and to
              safeguard and share data about the artists and music that we love.
            </p>
            <p>
              Data wants to be free, and we believe that by sharing what we
              have, rather than jealously guarding it for the benefit of a few,
              everyone can benefit.
            </p>
            <Link
              to="https://github.com/orgs/metabrainz"
              className="info-link"
              target="_blank"
              rel="noopener noreferrer"
            >
              <FontAwesomeIcon icon={faAnglesRight} size="sm" /> GitHub
              repositories
            </Link>
          </div>

          <div className="info-column">
            <div className="info-icon">
              <img
                src="/static/img/homepage/LB-Data-Provider-Info.png"
                alt="Data provider"
              />
            </div>
            <h2>Data provider</h2>
            <p>
              The MetaBrainz core mission is to curate and maintain public
              datasets that anyone can download and use. Some of the world’s
              biggest platforms, such as Google and Amazon, use our data, as
              well as small-scale developers and simply curious individuals.
            </p>
            <p>
              ListenBrainz and its sister sites are part of this mission - the
              music data that our users submit to ListenBrainz, and the
              MusicBrainz database that powers it, is available for download. We
              want to help <strong>you</strong> build products and tools.
            </p>
            <p>
              These datasets include the ListenBrainz PostgreSQL Data Dumps,
              which contains detailed data about ~1 billion listens, and can be
              used to create and study music consumption patterns. Our datasets
              are AI Ready, perfect for training large language models for
              music-based tasks.
            </p>
            <p>
              We ask{" "}
              <Link
                to="https://metabrainz.org/supporters"
                target="_blank"
                rel="noopener noreferrer"
              >
                commercial supporters
              </Link>{" "}
              to support us in order to help fund the creation and maintenance
              of these datasets. Personal use of our datasets will always be
              free.
            </p>
            <Link
              to="https://metabrainz.org/datasets"
              className="info-link"
              target="_blank"
              rel="noopener noreferrer"
            >
              <FontAwesomeIcon icon={faAnglesRight} size="sm" /> MetaBrainz
              Datasets
            </Link>
          </div>

          <div className="info-column">
            <div className="info-icon">
              <img
                src="/static/img/homepage/LB-Ethical-Info.png"
                alt="Ethical forever"
              />
            </div>
            <h2>Ethical forever</h2>
            <p>
              In today&apos;s world your personal data is owned, bought, sold
              and traded. Your personal and global listening history powers
              multi-billion dollar corporations and is used to tie you to their
              services and platforms. Sometimes it seems that the only person
              without access to your data, is you.
            </p>
            <p>
              Not any more! ListenBrainz was created because we believe in your
              right to your data. It is free, has no advertising, and you can
              migrate your data out at any time.
            </p>
            <p>
              The MetaBrainz Foundation is a registered non-profit, making it
              impossible for us to be bought or traded. Our team and volunteer
              contributers from across the globe are proud to consider
              ListenBrainz and it&apos;s sister sites enshittification-proof
              projects, immune to the the crapifying that takes place when
              business interests inevitably subsume and monetize projects that
              initially focussed on high-quality offerings to attract users. In
              fact Cory Doctorow, the coiner of the term &quot;
              <Link
                to="https://en.wikipedia.org/wiki/Enshittification"
                target="_blank"
                rel="noopener noreferrer"
              >
                enshittification
              </Link>
              &quot;, is on the MetaBrainz board of directors.
            </p>
            <Link
              to="https://metabrainz.org/"
              className="info-link"
              target="_blank"
              rel="noopener noreferrer"
            >
              <FontAwesomeIcon icon={faAnglesRight} size="sm" /> MetaBrainz
              Foundation
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

export function HomePageWrapper() {
  const { currentUser } = React.useContext(GlobalAppContext);
  const [searchParams, setSearchParams] = useSearchParams();

  const redirectParam = searchParams.get("redirect");

  if (
    currentUser?.name &&
    (redirectParam === "true" || redirectParam === null)
  ) {
    return <Navigate to={`/user/${currentUser.name}/`} replace />;
  }
  return <HomePage />;
}

export default HomePage;
