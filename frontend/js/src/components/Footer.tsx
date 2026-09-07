import * as React from "react";

import { faAnglesRight } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Link } from "react-router";

export default function Footer() {
  return (
    <section className="footer">
      <div className="container-fluid px-4">
        <div className="row align-items-baseline">
          <div className="col-12 col-sm-12 col-lg-6">
            <h3>
              <img
                src="/static/img/listenbrainz-logo.svg"
                width="180"
                alt="ListenBrainz"
              />
            </h3>
            <br />
            <p>
              ListenBrainz tracks what you listen to and turns it into insights
              about your music habits.
              <br />
              You can explore personalized recommendations, discover new
              artists, and share your taste with others through rich
              visualizations.
              <br />
              User listen data is made public under the{" "}
              <a href="https://creativecommons.org/public-domain/cc0/">
                Creative Commons Zero (CC0)
              </a>{" "}
              license.
            </p>
            <ul className="list-unstyled">
              <li className="color-a">
                <span>Chat with us: </span>{" "}
                <a
                  href="https://musicbrainz.org/doc/Communication/ChatBrainz"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Matrix, IRC, Discord
                </a>
              </li>
              <li className="color-a">
                <span>Email: </span>{" "}
                <a href="mailto:support@metabrainz.org">
                  support@metabrainz.org{" "}
                </a>
              </li>
            </ul>
          </div>
          <div className="col-6 col-lg-3">
            <h3 className="text-brand text-body">Useful Links</h3>
            <ul className="list-unstyled">
              <li>
                <FontAwesomeIcon icon={faAnglesRight} size="sm" />{" "}
                <Link to="/donate/">Donate</Link>
              </li>
              <li>
                <FontAwesomeIcon icon={faAnglesRight} size="sm" />{" "}
                <a
                  href="https://wiki.musicbrainz.org/Main_Page"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Wiki
                </a>
              </li>
              <li>
                <FontAwesomeIcon icon={faAnglesRight} size="sm" />{" "}
                <a
                  href="https://community.metabrainz.org/"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Community
                </a>
              </li>
              <li>
                <FontAwesomeIcon icon={faAnglesRight} size="sm" />{" "}
                <a
                  href="https://blog.metabrainz.org/"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Blog
                </a>
              </li>
              <li>
                <FontAwesomeIcon icon={faAnglesRight} size="sm" />{" "}
                <a
                  href="https://www.redbubble.com/people/metabrainz/shop"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Shop
                </a>
              </li>
              <li>
                <FontAwesomeIcon icon={faAnglesRight} size="sm" />{" "}
                <a
                  href="https://metabrainz.org/"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  MetaBrainz
                </a>
              </li>
              <li className="d-block d-md-none">
                <FontAwesomeIcon icon={faAnglesRight} size="sm" />{" "}
                <a
                  href="https://github.com/metabrainz/listenbrainz-server"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Contribute here
                </a>
              </li>
              <li className="d-block d-md-none">
                <FontAwesomeIcon icon={faAnglesRight} size="sm" />{" "}
                <a
                  href="https://tickets.metabrainz.org/"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Bug Tracker
                </a>
              </li>
            </ul>
          </div>
          <div className="col-6 col-lg-3">
            <h3 className="text-brand text-body">Fellow Projects</h3>
            <ul className="list-unstyled">
              <li>
                <FontAwesomeIcon icon={faAnglesRight} size="sm" />{" "}
                <img
                  src="/static/img/meb-icons/MusicBrainz.svg"
                  width="18"
                  height="18"
                  alt="MusicBrainz"
                />{" "}
                <a
                  href="https://musicbrainz.org/"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  MusicBrainz
                </a>
              </li>
              <li>
                <FontAwesomeIcon icon={faAnglesRight} size="sm" />{" "}
                <img
                  src="/static/img/meb-icons/CritiqueBrainz.svg"
                  width="18"
                  height="18"
                  alt="CritiqueBrainz"
                />{" "}
                <a
                  href="https://critiquebrainz.org/"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  CritiqueBrainz
                </a>
              </li>
              <li className="item-list-a">
                <FontAwesomeIcon icon={faAnglesRight} size="sm" />{" "}
                <img
                  src="/static/img/meb-icons/Picard.svg"
                  width="18"
                  height="18"
                  alt="Picard"
                />{" "}
                <a
                  href="https://picard.musicbrainz.org/"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Picard
                </a>
              </li>
              <li>
                <FontAwesomeIcon icon={faAnglesRight} size="sm" />{" "}
                <img
                  src="/static/img/meb-icons/BookBrainz.svg"
                  width="18"
                  height="18"
                  alt="BookBrainz"
                />{" "}
                <a
                  href="https://bookbrainz.org/"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  BookBrainz
                </a>
              </li>
              <li>
                <FontAwesomeIcon icon={faAnglesRight} size="sm" />{" "}
                <img
                  src="/static/img/meb-icons/AcousticBrainz.svg"
                  width="18"
                  height="18"
                  alt="AcousticBrainz"
                />{" "}
                <a
                  href="https://acousticbrainz.org/"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  AcousticBrainz
                </a>
              </li>
              <li>
                <FontAwesomeIcon icon={faAnglesRight} size="sm" />{" "}
                <img
                  src="/static/img/meb-icons/CoverArtArchive.svg"
                  width="18"
                  height="18"
                  alt="CoverArtArchive"
                />{" "}
                <a
                  href="https://coverartarchive.org"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Cover Art Archive
                </a>
              </li>
            </ul>
          </div>
        </div>
        <div className="row align-items-stretch mx-2 mx-xl-5 mt-3 border-top">
          <div className="col-lg-3 py-4 col-md-auto d-md-flex d-none flex-column gap-3 text-center ">
            <div className="mt-auto">
              OSS Geek?{" "}
              <a
                href="https://github.com/metabrainz/listenbrainz-server"
                target="_blank"
                rel="noopener noreferrer"
              >
                {" "}
                <span className="color-a"> Contribute here </span>{" "}
              </a>
            </div>
            <div className="mb-auto">
              Found an Issue?{" "}
              <a
                href="https://tickets.metabrainz.org/"
                target="_blank"
                rel="noopener noreferrer"
              >
                {" "}
                <span className="color-a"> Report here </span>
              </a>
            </div>
          </div>
          <div
            className="col-lg-6 py-4 col-md text-center my-auto"
            style={{ minHeight: 60 }}
          >
            <div className="d-inline-block">Brought to you by </div>
            <div className="d-inline-block">
              <img
                src="/static/img/meb-icons/MetaBrainz.svg"
                width="30"
                height="30"
                alt="MetaBrainz"
              />{" "}
              MetaBrainz Foundation
            </div>
          </div>
          <div className="py-4 col-lg-3 col-md-auto d-flex d-md-block justify-content-center order-first order-md-last">
            <a href="https://play.google.com/store/apps/details?id=org.listenbrainz.android&pcampaignid=pcampaignidMKT-Other-global-all-co-prtnr-py-PartBadge-Mar2515-1">
              <img
                alt="Get it on Google Play"
                src="https://play.google.com/intl/en_us/badges/static/images/badges/en_badge_web_generic.png"
                width="200"
              />
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
