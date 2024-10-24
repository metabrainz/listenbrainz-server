import * as React from "react";

import { faAnglesRight } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Link } from "react-router-dom";

export default function Footer() {
  return (
    <section className="footer">
      <div className="container-fluid">
        <div className="row">
          <div className="col-sm-12 col-md-6">
            <h3>
              <img
                src="/static/img/listenbrainz-logo.svg"
                width="180"
                alt="ListenBrainz"
              />
            </h3>
            <br />
            <p className="color-gray">
              ListenBrainz keeps track of music you listen to and provides you
              with insights into your listening habits.
              <br />
              You can use ListenBrainz to track your listening habits, discover
              new music with personalized recommendations, and share your
              musical taste with others using our visualizations.
            </p>
            <ul className="list-unstyled">
              <li className="color-a">
                <span className="color-gray">Chat with us: </span>{" "}
                <a
                  href="https://musicbrainz.org/doc/Communication/ChatBrainz"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Matrix, IRC, Discord
                </a>
              </li>
              <li className="color-a">
                <span className="color-gray">Email: </span>{" "}
                <a href="mailto:support@metabrainz.org">
                  support@metabrainz.org{" "}
                </a>
              </li>
            </ul>
          </div>
          <br />
          <div className="col-xs-12 col-sm-6 col-md-3">
            <h3 className="w-title-a text-brand">Useful Links</h3>
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
              <li className="visible-xs">
                <FontAwesomeIcon icon={faAnglesRight} size="sm" />{" "}
                <a
                  href="https://github.com/metabrainz/listenbrainz-server"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Contribute Here
                </a>
              </li>
              <li className="visible-xs">
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
          <div className="col-xs-12 col-sm-6 col-md-3">
            <h3 className="w-title-a text-brand">Fellow Projects</h3>
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
        <div className="row center-p">
          <div className="col-md-3 d-none d-md-block hidden-xs">
            <p className="color-gray section-line">
              OSS Geek?{" "}
              <a
                href="https://github.com/metabrainz/listenbrainz-server"
                target="_blank"
                rel="noopener noreferrer"
              >
                {" "}
                <span className="color-a"> Contribute Here </span>{" "}
              </a>
            </p>
          </div>
          <div className="col-md-6">
            <p className="section-line">
              Brought to you by{" "}
              <img
                src="/static/img/meb-icons/MetaBrainz.svg"
                width="30"
                height="30"
                alt="MetaBrainz"
              />{" "}
              <span className="color-a"> MetaBrainz Foundation </span>
            </p>
          </div>
          <div className="col-md-3 d-none d-md-block hidden-xs">
            <p className="color-gray section-line">
              Found an Issue?{" "}
              <a
                href="https://tickets.metabrainz.org/"
                target="_blank"
                rel="noopener noreferrer"
              >
                {" "}
                <span className="color-a"> Report Here </span>
              </a>
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
