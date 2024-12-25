import { faCheck, faQuestionCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as React from "react";
import { Link } from "react-router-dom";
import ReactTooltip from "react-tooltip";
import { COLOR_LB_GREEN } from "../../utils/constants";
import Blob from "../../home/Blob";
import GlobalAppContext from "../../utils/GlobalAppContext";

export default function Donate() {
  const { currentUser } = React.useContext(GlobalAppContext);
  const flairQuestionMarkIcon = (
    <FontAwesomeIcon
      icon={faQuestionCircle}
      data-tip
      data-for="flair-tooltip"
      size="sm"
    />
  );
  return (
    <div id="donations-page">
      <Blob width={250} height={250} randomness={1.5} className="blob" />
      <Blob
        width={250}
        height={250}
        randomness={1.1}
        className="blob"
        style={{ top: "45%", right: "15%" }}
      />
      <div>
        <div className="donations-page-header">
          Money can&apos;t buy happiness, but it can buy
          <br />
          <span style={{ fontWeight: 600 }}>LISTENBRAINZ HOSTING</span>
        </div>
        <div id="donations-tiers">
          <div className="tier card text-center">
            <div>
              <h2 style={{ marginTop: 0 }}>
                <b>Free for everyone</b>
              </h2>
              <FontAwesomeIcon icon={faCheck} color={COLOR_LB_GREEN} />
              <b style={{ marginLeft: "0.5em" }}>
                All website features, for free, forever
              </b>
            </div>
          </div>
          <ReactTooltip id="flair-tooltip" place="bottom" multiline>
            Every $5 donation unlocks flairs for 1 month,
            <br />
            with larger donations extending the duration.
            <br />
            Donations stack up, adding more months
            <br />
            of unlocked flairs with each contribution.
          </ReactTooltip>
          <div className="tier card">
            <div className="tier-heading">
              <h2>
                <a
                  className="btn btn-success btn-lg btn-rounded"
                  href={`https://metabrainz.org/donate?amount=5&editor=${
                    currentUser?.name ?? ""
                  }`}
                  target="_blank"
                  rel="noreferrer"
                >
                  Donate $5
                </a>
              </h2>
            </div>
            <ul className="fa-ul">
              <li className="perk">
                <FontAwesomeIcon
                  listItem
                  icon={faCheck}
                  color={COLOR_LB_GREEN}
                />
                <b>User flair {flairQuestionMarkIcon}</b>
                <br />
                <small>
                  Add a special effect to your username on the website
                </small>
              </li>
              <li className="perk">
                <FontAwesomeIcon
                  listItem
                  icon={faCheck}
                  color={COLOR_LB_GREEN}
                />
                <b>Our eternal gratitude</b>
              </li>
            </ul>
          </div>
          <div className="tier card">
            <div className="tier-heading">
              <h2>
                <a
                  className="btn btn-success btn-lg btn-rounded"
                  href={`https://metabrainz.org/donate?amount=20&editor=${
                    currentUser?.name ?? ""
                  }`}
                  target="_blank"
                  rel="noreferrer"
                >
                  Donate $20
                </a>
              </h2>
            </div>
            <ul className="fa-ul">
              <li className="perk">
                <FontAwesomeIcon
                  listItem
                  icon={faCheck}
                  color={COLOR_LB_GREEN}
                />
                <b>User flair {flairQuestionMarkIcon}</b>
                <br />
                <small>
                  Add a special effect to your username on the website
                </small>
              </li>
              <li className="perk">
                <FontAwesomeIcon
                  listItem
                  icon={faCheck}
                  color={COLOR_LB_GREEN}
                />
                <b>Our eternal gratitude</b>
              </li>
              <li className="perk">
                <FontAwesomeIcon
                  listItem
                  icon={faCheck}
                  color={COLOR_LB_GREEN}
                />
                <b>Inner sense of peace and accomplishment</b>
              </li>
            </ul>
          </div>
          <div className="tier card">
            <div className="tier-heading">
              <h2>
                <a
                  className="btn btn-success btn-lg btn-rounded"
                  href={`https://metabrainz.org/donate?amount=50&editor=${
                    currentUser?.name ?? ""
                  }`}
                  target="_blank"
                  rel="noreferrer"
                >
                  Donate $50
                </a>
              </h2>
            </div>
            <ul className="fa-ul">
              <li className="perk">
                <FontAwesomeIcon
                  listItem
                  icon={faCheck}
                  color={COLOR_LB_GREEN}
                />
                <b>User flair {flairQuestionMarkIcon}</b>
                <br />
                <small>
                  Add a special effect to your username on the website
                </small>
              </li>
              <li className="perk">
                <FontAwesomeIcon
                  listItem
                  icon={faCheck}
                  color={COLOR_LB_GREEN}
                />
                <b>Our eternal gratitude</b>
              </li>
              <li className="perk">
                <FontAwesomeIcon
                  listItem
                  icon={faCheck}
                  color={COLOR_LB_GREEN}
                />
                <b>Inner sense of peace and accomplishment</b>
              </li>
              <li className="perk">
                <FontAwesomeIcon
                  listItem
                  icon={faCheck}
                  color={COLOR_LB_GREEN}
                />
                <b>Make your family proud</b>
              </li>
              <li className="perk">
                <FontAwesomeIcon
                  listItem
                  icon={faCheck}
                  color={COLOR_LB_GREEN}
                />
                <b>Instant street cred</b>
              </li>
              <li className="perk">
                <FontAwesomeIcon
                  listItem
                  icon={faCheck}
                  color={COLOR_LB_GREEN}
                />
                <b>De-shittify the internet</b>
              </li>
            </ul>
          </div>
        </div>
        <div className="donations-page-footer row">
          <h3 className="col-xs-12">Jokes aside</h3>
          <div className="col-sm-6">
            <p>
              We are a{" "}
              <a
                href="https://metabrainz.org/projects"
                target="_blank"
                rel="noreferrer"
              >
                non-profit foundation
              </a>{" "}
              and we are free to build the music website of our dreams, unbiased
              by financial deals.
              <br />
              One where <b>you aren&apos;t the product</b> and your personal
              data isn&apos;t the price you pay.
            </p>
            <p>
              <b>All features are free for everyone</b> —no paywalls, no “Pro++”
              features.
            </p>
          </div>
          <div className="col-sm-6">
            <p>
              By donating —either once or regularly— you&apos;ll join thousands
              of music lovers in helping us build an honest, unbiased and
              community-driven space for music discovery.
            </p>
            <p>
              <b>At our scale, every contribution matters.</b>
            </p>
            <p>
              <Link to="/donors/">See all our donors</Link>
            </p>
          </div>
        </div>
      </div>
      <div className="grey-wedge" />
    </div>
  );
}
